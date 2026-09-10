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


class QAAnalysisSchema(BaseModel):
    role: str
    critical_test_areas: List[str]
    edge_cases: List[str]
    failure_scenarios: List[str]
    testing_strategy: List[str]
    qa_blockers: List[str]
    testability_score: int = Field(..., ge=1, le=10)
    risk_score: int = Field(..., ge=1, le=10)
    recommendation: str
    verdict: str


SYSTEM_PROMPT = """
You are an elite Senior QA Engineer and Test Strategist.
You are part of a multi-agent AI product evaluation system.

Your job:
- identify critical test areas
- identify edge cases
- identify failure scenarios
- recommend testing strategy
- identify QA blockers

CRITICAL RESPONSE RULES:
- Return ONLY raw valid JSON
- Do NOT use markdown or code fences
- Keep arrays concise (maximum 5 items)

Required JSON structure:
{
  "role": "QA Engineer",
  "critical_test_areas": [],
  "edge_cases": [],
  "failure_scenarios": [],
  "testing_strategy": [],
  "qa_blockers": [],
  "testability_score": 1,
  "risk_score": 1,
  "recommendation": "",
  "verdict": "testable"
}
"""


def validate_response(raw_text: str) -> Dict[str, Any]:
    parsed = extract_json(raw_text)
    if "testability_score" in parsed:
        parsed["testability_score"] = round(float(parsed["testability_score"]) * 10) if float(parsed["testability_score"]) <= 1 else int(parsed["testability_score"])
    if "risk_score" in parsed:
        parsed["risk_score"] = round(float(parsed["risk_score"]) * 10) if float(parsed["risk_score"]) <= 1 else int(parsed["risk_score"])
    validated = QAAnalysisSchema(**parsed)
    validated.verdict = validated.verdict.lower().strip()
    allowed = {"testable", "risky", "needs_clarification", "not_viable", "complex", "unclear"}
    if validated.verdict not in allowed:
        validated.verdict = "needs_clarification"
    return validated.model_dump()


def generate_analysis(client: genai.Client, user_message: str) -> Dict[str, Any]:
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"QA Analysis Attempt {attempt}")
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
            validated["_meta"] = {"latency_seconds": latency, "model": MODEL_NAME}
            return validated

        except (ValidationError, ValueError, json.JSONDecodeError) as e:
            last_error = str(e)
            logger.warning(f"Attempt {attempt} failed: {last_error}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)

    raise RuntimeError(f"All retry attempts failed: {last_error}")


def qa_node(state: SpecForgeState) -> SpecForgeState:
    logger.info("QA Node Started")
    state["qa_status"] = "failed"
    state["qa_concerns"] = None

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
            f"software testing QA strategy edge cases failure scenarios for: {idea}"
        )

        user_message = f"""
Analyse this product idea from a QA and testing perspective.

PRODUCT IDEA:
{idea}

REFERENCE CONTEXT:
{rag_context}

Focus on:
- critical test areas
- edge cases
- failure scenarios
- testing strategy
- QA blockers

Return ONLY valid JSON.
"""
        analysis = generate_analysis(client, user_message)
        state["qa_concerns"] = analysis
        state["qa_status"] = "success"
        state["qa_verdict"] = analysis["verdict"]
        state["qa_scores"] = {
            "testability": analysis["testability_score"],
            "risk": analysis["risk_score"]
        }
        state["critical_test_areas"] = analysis["critical_test_areas"]
        state["edge_cases"] = analysis["edge_cases"]
        state["failure_scenarios"] = analysis["failure_scenarios"]
        state["testing_strategy"] = analysis["testing_strategy"]
        state["qa_blockers"] = analysis["qa_blockers"]
        logger.info("QA Node Completed Successfully")

    except Exception as e:
        logger.exception(f"QA Node Failed: {e}")
        state["qa_status"] = "failed"

    return state