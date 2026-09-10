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


class OrchestratorSchema(BaseModel):
    role: str
    product_summary: str
    target_users: List[str]
    core_problem_statement: str
    functional_requirements: List[str]
    non_functional_requirements: List[str]
    technical_constraints: List[str]
    business_requirements: List[str]
    security_requirements: List[str]
    qa_requirements: List[str]
    ux_requirements: List[str]
    recurring_cross_agent_risks: List[str]
    implementation_priorities: List[str]
    mvp_scope: List[str]
    future_scope: List[str]
    launch_risks: List[str]
    final_recommendation: str
    project_viability: str


SYSTEM_PROMPT = """
You are an elite Principal Product Architect and Technical Specification Strategist.
You are the FINAL synthesis agent in a multi-agent AI evaluation system.

Your job:
- synthesize all agent inputs into a final specification
- identify recurring risks across all agents
- define MVP scope
- define launch blockers
- create a production-ready specification

CRITICAL RESPONSE RULES:
- Return ONLY raw valid JSON
- Do NOT use markdown or code fences
- Keep arrays concise (maximum 5 items)

Required JSON structure:
{
  "role": "Orchestrator",
  "product_summary": "",
  "target_users": [],
  "core_problem_statement": "",
  "functional_requirements": [],
  "non_functional_requirements": [],
  "technical_constraints": [],
  "business_requirements": [],
  "security_requirements": [],
  "qa_requirements": [],
  "ux_requirements": [],
  "recurring_cross_agent_risks": [],
  "implementation_priorities": [],
  "mvp_scope": [],
  "future_scope": [],
  "launch_risks": [],
  "final_recommendation": "",
  "project_viability": "medium"
}
"""


def validate_response(raw_text: str) -> Dict[str, Any]:
    parsed = extract_json(raw_text)
    
    # Fix functional_requirements if returned as objects
    if "functional_requirements" in parsed:
        fixed = []
        for item in parsed["functional_requirements"]:
            if isinstance(item, dict):
                fixed.append(item.get("description", str(item)))
            else:
                fixed.append(str(item))
        parsed["functional_requirements"] = fixed

    # Fix non_functional_requirements if returned as objects
    if "non_functional_requirements" in parsed:
        fixed = []
        for item in parsed["non_functional_requirements"]:
            if isinstance(item, dict):
                fixed.append(item.get("description", str(item)))
            else:
                fixed.append(str(item))
        parsed["non_functional_requirements"] = fixed

    # Fix mvp_scope if returned as object instead of list
    if "mvp_scope" in parsed and isinstance(parsed["mvp_scope"], dict):
        core = parsed["mvp_scope"].get("core_features", [])
        parsed["mvp_scope"] = core

    validated = OrchestratorSchema(**parsed)
    validated.project_viability = validated.project_viability.lower().strip()
    allowed = {"high", "medium", "low", "very_low"}
    if validated.project_viability not in allowed:
        validated.project_viability = "medium"
    return validated.model_dump()


def generate_analysis(client: genai.Client, user_message: str) -> Dict[str, Any]:
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"Orchestrator Analysis Attempt {attempt}")
            start_time = time.time()

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0,
                    max_output_tokens=8000,
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


def orchestrator_node(state: SpecForgeState) -> SpecForgeState:
    logger.info("Orchestrator Node Started")
    state["orchestrator_status"] = "failed"
    state["final_spec"] = None

    try:
        api_key = state.get("api_key") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError("No API key available. Please provide your own Gemini API key or contact the site owner.")

        client = genai.Client(api_key=api_key)

        idea = state.get("idea")
        if not idea:
            raise ValueError("No product idea provided")

        from backend.rag.setup import get_relevant_context
        rag_context = get_relevant_context(
            f"software requirements specification SRS template product specification for: {idea}"
        )

        user_message = f"""
You are the final synthesis agent. Based on all agent analyses below, create a complete product specification.

PRODUCT IDEA:
{idea}

REFERENCE CONTEXT:
{rag_context}

BUSINESS ANALYSIS:
{json.dumps(state.get("business_analysis"), indent=2)}

DEVELOPER ANALYSIS:
{json.dumps(state.get("dev_concerns"), indent=2)}

QA ANALYSIS:
{json.dumps(state.get("qa_concerns"), indent=2)}

SECURITY ANALYSIS:
{json.dumps(state.get("security_concerns"), indent=2)}

UX ANALYSIS:
{json.dumps(state.get("ux_concerns"), indent=2)}

Synthesize all of the above into a final product specification.
Return ONLY valid JSON.
"""
        analysis = generate_analysis(client, user_message)
        state["final_spec"] = analysis
        state["orchestrator_status"] = "success"
        state["project_viability"] = analysis["project_viability"]
        state["functional_requirements"] = analysis["functional_requirements"]
        state["non_functional_requirements"] = analysis["non_functional_requirements"]
        state["mvp_scope"] = analysis["mvp_scope"]
        state["launch_risks"] = analysis["launch_risks"]
        state["final_recommendation"] = analysis["final_recommendation"]
        logger.info("Orchestrator Node Completed Successfully")

    except Exception as e:
        logger.exception(f"Orchestrator Node Failed: {e}")
        state["orchestrator_status"] = "failed"

    return state