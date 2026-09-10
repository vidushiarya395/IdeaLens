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


class DeveloperAnalysisSchema(BaseModel):
    role: str
    architecture_concerns: List[str]
    scalability_risks: List[str]
    tech_stack_recommendations: List[str]
    integration_challenges: List[str]
    development_blockers: List[str]
    complexity_score: int = Field(..., ge=1, le=10)
    scalability_score: int = Field(..., ge=1, le=10)
    recommendation: str
    verdict: str


SYSTEM_PROMPT = """
You are an elite Senior Software Architect and Developer.
You are part of a multi-agent AI product evaluation system.

Your job:
- identify architecture risks
- identify scalability concerns
- recommend tech stack
- identify integration challenges
- identify development blockers

CRITICAL RESPONSE RULES:
- Return ONLY raw valid JSON
- Do NOT use markdown or code fences
- Keep arrays concise (maximum 5 items)

Required JSON structure:
{
  "role": "Senior Developer",
  "architecture_concerns": [],
  "scalability_risks": [],
  "tech_stack_recommendations": [],
  "integration_challenges": [],
  "development_blockers": [],
  "complexity_score": 1,
  "scalability_score": 1,
  "recommendation": "",
  "verdict": "feasible"
}
"""


def validate_response(raw_text: str) -> Dict[str, Any]:
    parsed = extract_json(raw_text)
    if "complexity_score" in parsed:
        parsed["complexity_score"] = round(float(parsed["complexity_score"]) * 10) if float(parsed["complexity_score"]) <= 1 else int(parsed["complexity_score"])
    if "scalability_score" in parsed:
        parsed["scalability_score"] = round(float(parsed["scalability_score"]) * 10) if float(parsed["scalability_score"]) <= 1 else int(parsed["scalability_score"])
    if "tech_stack_recommendations" in parsed:
        fixed = []
        for item in parsed["tech_stack_recommendations"]:
            if isinstance(item, dict):
                fixed.append(f"{item.get('component', '')}: {item.get('technology', '')} - {item.get('reason', '')}")
            else:
                fixed.append(str(item))
        parsed["tech_stack_recommendations"] = fixed
    validated = DeveloperAnalysisSchema(**parsed)
    validated.verdict = validated.verdict.lower().strip()
    allowed = {"feasible", "complex", "needs_clarification", "not_viable", "risky", "unclear"}
    if validated.verdict not in allowed:
        validated.verdict = "needs_clarification"
    return validated.model_dump()


def generate_analysis(client: genai.Client, user_message: str) -> Dict[str, Any]:
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"Developer Analysis Attempt {attempt}")
            start_time = time.time()

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0,
                    max_output_tokens=6000,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                )
            )

            latency = round(time.time() - start_time, 2)
            raw_text = (response.text or "").strip()
            if not raw_text:
                raise ValueError("Empty model response (truncated or safety-blocked)")
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


def developer_node(state: SpecForgeState) -> SpecForgeState:
    logger.info("Developer Node Started")
    state["developer_status"] = "failed"
    state["dev_concerns"] = None

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
            f"software architecture scalability tech stack SaaS patterns for: {idea}"
        )

        user_message = f"""
Analyse this product idea from a software architecture and development perspective.

PRODUCT IDEA:
{idea}

REFERENCE CONTEXT:
{rag_context}

Focus on:
- architecture risks
- scalability concerns
- recommended tech stack
- integration challenges
- development blockers

Return ONLY valid JSON.
"""

        analysis = generate_analysis(client, user_message)
        state["dev_concerns"] = analysis
        state["developer_status"] = "success"
        state["developer_verdict"] = analysis["verdict"]
        state["developer_scores"] = {
            "complexity": analysis["complexity_score"],
            "scalability": analysis["scalability_score"]
        }
        state["developer_architecture_concerns"] = analysis["architecture_concerns"]
        state["developer_scalability_risks"] = analysis["scalability_risks"]
        state["developer_blockers"] = analysis["development_blockers"]
        logger.info("Developer Node Completed Successfully")

    except Exception as e:
        logger.exception(f"Developer Node Failed: {e}")
        state["developer_status"] = "failed"

    return state