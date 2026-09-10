from google import genai
from google.genai import types
import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from .state import SpecForgeState
from .utils import extract_json, logger

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

MODEL_NAME = "gemini-2.5-flash"
MAX_RETRIES = 3
RETRY_DELAY = 5


class BusinessAnalysisSchema(BaseModel):
    role: str
    key_questions: List[str]
    business_concerns: List[str]
    assumptions_detected: List[str]
    missing_requirements: List[str]
    feasibility_score: int = Field(..., ge=1, le=10)
    market_clarity_score: int = Field(..., ge=1, le=10)
    recommendation: str
    verdict: str


SYSTEM_PROMPT = """
You are an elite Senior Business Analyst and Product Strategist.
You are part of a multi-agent AI product evaluation system.

Your job:
- identify business risks
- identify weak assumptions
- identify missing requirements
- evaluate monetization feasibility
- evaluate scalability realism

CRITICAL RESPONSE RULES:
- Return ONLY raw valid JSON
- Do NOT use markdown or code fences
- Keep arrays concise (maximum 5 items)

Required JSON structure:
{
  "role": "Business Analyst",
  "key_questions": [],
  "business_concerns": [],
  "assumptions_detected": [],
  "missing_requirements": [],
  "feasibility_score": 1,
  "market_clarity_score": 1,
  "recommendation": "",
  "verdict": "promising"
}
"""


def validate_response(raw_text: str) -> Dict[str, Any]:
    parsed = extract_json(raw_text)
    if "feasibility_score" in parsed:
        parsed["feasibility_score"] = round(float(parsed["feasibility_score"]) * 10) if float(parsed["feasibility_score"]) <= 1 else int(parsed["feasibility_score"])
    if "market_clarity_score" in parsed:
        parsed["market_clarity_score"] = round(float(parsed["market_clarity_score"]) * 10) if float(parsed["market_clarity_score"]) <= 1 else int(parsed["market_clarity_score"])
    validated = BusinessAnalysisSchema(**parsed)
    validated.verdict = validated.verdict.lower().strip()
    allowed = {"promising", "needs_clarification", "not_viable", "needs_work", "risky", "unclear"}
    if validated.verdict not in allowed:
        validated.verdict = "needs_clarification"
    return validated.model_dump()


def generate_analysis(client: genai.Client, user_message: str) -> Dict[str, Any]:
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"Business Analysis Attempt {attempt}")
            start_time = time.time()

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0,
                    max_output_tokens=6000,
                )
            )

            latency = round(time.time() - start_time, 2)
            raw_text = response.text.strip()

            logger.info(f"RAW RESPONSE:\n{raw_text}")

            validated = validate_response(raw_text)
            validated["_meta"] = {
                "latency_seconds": latency,
                "model": MODEL_NAME
            }
            return validated

        except (ValidationError, ValueError, json.JSONDecodeError) as e:
            last_error = str(e)
            logger.warning(f"Attempt {attempt} failed: {last_error}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)

    raise RuntimeError(f"All retry attempts failed: {last_error}")


def business_analyst_node(state: SpecForgeState) -> SpecForgeState:
    logger.info("Business Analyst Node Started")
    state["business_analysis_status"] = "failed"
    state["business_analysis"] = None

    try:
        api_key = state.get("api_key")
        if not api_key:
            raise EnvironmentError("No Gemini API key provided for this request")

        client = genai.Client(api_key=api_key)

        idea = state.get("idea")
        if not idea:
            raise ValueError("No product idea provided")

        from backend.rag.setup import get_relevant_context

        rag_context = get_relevant_context(
            f"business scalability SaaS monetization market feasibility for: {idea}"
        )

        user_message = f"""
Analyse this product idea from a business strategy perspective.

PRODUCT IDEA:
{idea}

REFERENCE CONTEXT:
{rag_context}

Focus on:
- market viability
- monetization risks
- execution blockers
- scalability realism
- missing business requirements

Return ONLY valid JSON.
"""

        analysis = generate_analysis(client, user_message)
        state["business_analysis"] = analysis
        state["business_analysis_status"] = "success"
        state["business_verdict"] = analysis["verdict"]
        state["business_score"] = {
            "feasibility": analysis["feasibility_score"],
            "market_clarity": analysis["market_clarity_score"]
        }
        state["business_key_questions"] = analysis["key_questions"]
        state["business_concerns"] = analysis["business_concerns"]
        state["business_missing_requirements"] = analysis["missing_requirements"]
        state["business_assumptions"] = analysis["assumptions_detected"]
        logger.info("Business Analyst Node Completed Successfully")

    except Exception as e:
        logger.exception(f"Business Analyst Node Failed: {e}")
        state["business_analysis_status"] = "failed"

    return state