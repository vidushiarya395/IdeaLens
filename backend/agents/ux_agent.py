from google import genai
from google.genai import types
from google.genai import errors as genai_errors
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


class UXAnalysisSchema(BaseModel):
    role: str
    onboarding_issues: List[str]
    accessibility_concerns: List[str]
    usability_breakpoints: List[str]
    retention_risks: List[str]
    ux_blockers: List[str]
    usability_score: int = Field(..., ge=1, le=10)
    retention_score: int = Field(..., ge=1, le=10)
    recommendation: str
    verdict: str


SYSTEM_PROMPT = """
You are an elite Senior UX Researcher and Product Designer.
You are part of a multi-agent AI product evaluation system.

Your job:
- identify onboarding issues
- identify accessibility concerns
- identify usability breakpoints
- identify retention risks
- identify UX blockers

CRITICAL RESPONSE RULES:
- Return ONLY raw valid JSON
- Do NOT use markdown or code fences
- Keep arrays concise (maximum 5 items)

Required JSON structure:
{
  "role": "UX Researcher",
  "onboarding_issues": [],
  "accessibility_concerns": [],
  "usability_breakpoints": [],
  "retention_risks": [],
  "ux_blockers": [],
  "usability_score": 1,
  "retention_score": 1,
  "recommendation": "",
  "verdict": "needs_work"
}
"""


def validate_response(raw_text: str) -> Dict[str, Any]:
    parsed = extract_json(raw_text)
    if "usability_score" in parsed:
        parsed["usability_score"] = round(float(parsed["usability_score"]) * 10) if float(parsed["usability_score"]) <= 1 else int(parsed["usability_score"])
    if "retention_score" in parsed:
        parsed["retention_score"] = round(float(parsed["retention_score"]) * 10) if float(parsed["retention_score"]) <= 1 else int(parsed["retention_score"])
    validated = UXAnalysisSchema(**parsed)
    validated.verdict = validated.verdict.lower().strip()
    allowed = {"good", "needs_work", "risky", "needs_clarification", "not_viable", "unclear"}
    if validated.verdict not in allowed:
        validated.verdict = "needs_work"
    return validated.model_dump()


def generate_analysis(client: genai.Client, user_message: str) -> Dict[str, Any]:
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"UX Analysis Attempt {attempt}")
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

        except genai_errors.APIError as e:
            code = getattr(e, "code", None)
            last_error = f"Gemini API error {code}: {e}"
            logger.warning(f"Attempt {attempt} hit API error: {last_error}")
            if attempt < MAX_RETRIES:
                time.sleep(30 * attempt if code == 429 else RETRY_DELAY * attempt)
        except (ValidationError, ValueError, json.JSONDecodeError) as e:
            last_error = str(e)
            logger.warning(f"Attempt {attempt} failed: {last_error}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)

    raise RuntimeError(f"All retry attempts failed: {last_error}")


def ux_node(state: SpecForgeState) -> SpecForgeState:
    logger.info("UX Node Started")
    state["ux_status"] = "failed"
    state["ux_concerns"] = None

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
            f"UX design usability onboarding accessibility retention for: {idea}"
        )

        user_message = f"""
Analyse this product idea from a UX and user experience perspective.

PRODUCT IDEA:
{idea}

REFERENCE CONTEXT:
{rag_context}

Focus on:
- onboarding issues
- accessibility concerns
- usability breakpoints
- retention risks
- UX blockers

Return ONLY valid JSON.
"""
        analysis = generate_analysis(client, user_message)
        state["ux_concerns"] = analysis
        state["ux_status"] = "success"
        state["ux_verdict"] = analysis["verdict"]
        state["ux_scores"] = {
            "usability": analysis["usability_score"],
            "retention": analysis["retention_score"]
        }
        state["onboarding_issues"] = analysis["onboarding_issues"]
        state["accessibility_concerns"] = analysis["accessibility_concerns"]
        state["retention_risks"] = analysis["retention_risks"]
        state["ux_blockers"] = analysis["ux_blockers"]
        logger.info("UX Node Completed Successfully")

    except Exception as e:
        logger.exception(f"UX Node Failed: {e}")
        state["ux_status"] = "failed"

    return state

