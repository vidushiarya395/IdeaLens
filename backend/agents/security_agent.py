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


class SecurityAnalysisSchema(BaseModel):
    role: str
    critical_vulnerabilities: List[str]
    authentication_risks: List[str]
    data_privacy_risks: List[str]
    compliance_risks: List[str]
    mitigation_strategies: List[str]
    security_score: int = Field(..., ge=1, le=10)
    compliance_score: int = Field(..., ge=1, le=10)
    recommendation: str
    verdict: str


SYSTEM_PROMPT = """
You are an elite Senior Security Engineer and Compliance Specialist.
You are part of a multi-agent AI product evaluation system.

Your job:
- identify critical vulnerabilities
- identify authentication risks
- identify data privacy risks
- identify compliance risks
- recommend mitigation strategies

CRITICAL RESPONSE RULES:
- Return ONLY raw valid JSON
- Do NOT use markdown or code fences
- Keep arrays concise (maximum 5 items)

Required JSON structure:
{
  "role": "Security Engineer",
  "critical_vulnerabilities": [],
  "authentication_risks": [],
  "data_privacy_risks": [],
  "compliance_risks": [],
  "mitigation_strategies": [],
  "security_score": 1,
  "compliance_score": 1,
  "recommendation": "",
  "verdict": "needs_review"
}
"""


def validate_response(raw_text: str) -> Dict[str, Any]:
    parsed = extract_json(raw_text)
    if "security_score" in parsed:
        parsed["security_score"] = round(float(parsed["security_score"]) * 10) if float(parsed["security_score"]) <= 1 else int(parsed["security_score"])
    if "compliance_score" in parsed:
        parsed["compliance_score"] = round(float(parsed["compliance_score"]) * 10) if float(parsed["compliance_score"]) <= 1 else int(parsed["compliance_score"])
    validated = SecurityAnalysisSchema(**parsed)
    validated.verdict = validated.verdict.lower().strip()
    allowed = {"secure", "needs_review", "risky", "needs_clarification", "not_viable", "unclear"}
    if validated.verdict not in allowed:
        validated.verdict = "needs_review"
    return validated.model_dump()


def generate_analysis(client: genai.Client, user_message: str) -> Dict[str, Any]:
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"Security Analysis Attempt {attempt}")
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


def security_node(state: SpecForgeState) -> SpecForgeState:
    logger.info("Security Node Started")
    state["security_status"] = "failed"
    state["security_concerns"] = None

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
            f"security vulnerabilities OWASP GDPR compliance data privacy for: {idea}"
        )

        user_message = f"""
Analyse this product idea from a security and compliance perspective.

PRODUCT IDEA:
{idea}

REFERENCE CONTEXT:
{rag_context}

Focus on:
- critical vulnerabilities
- authentication risks
- data privacy risks
- compliance risks
- mitigation strategies

Return ONLY valid JSON.
"""
        analysis = generate_analysis(client, user_message)
        state["security_concerns"] = analysis
        state["security_status"] = "success"
        state["security_verdict"] = analysis["verdict"]
        state["security_scores"] = {
            "security": analysis["security_score"],
            "compliance": analysis["compliance_score"]
        }
        state["critical_vulnerabilities"] = analysis["critical_vulnerabilities"]
        state["compliance_risks"] = analysis["compliance_risks"]
        state["mitigation_strategies"] = analysis["mitigation_strategies"]
        logger.info("Security Node Completed Successfully")

    except Exception as e:
        logger.exception(f"Security Node Failed: {e}")
        state["security_status"] = "failed"

    return state