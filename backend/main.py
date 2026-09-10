import os
import json
import asyncio
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded

from backend.agents.business_agent import business_analyst_node
from backend.agents.developer_agent import developer_node
from backend.agents.qa_agent import qa_node
from backend.agents.security_agent import security_node
from backend.agents.ux_agent import ux_node
from backend.agents.orchestrator_agent import orchestrator_node
from backend.agents.pipeline import spec_pipeline
from backend.database.db import save_project, save_specification
from backend.rag.setup import setup_vector_store

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

# Seconds to wait between agents so a single run stays under Gemini's free-tier
# per-minute request cap (as low as 5 RPM). Set to 0 on a paid key.
AGENT_DELAY_SECONDS = float(os.getenv("AGENT_DELAY_SECONDS", "13"))

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="SpecForge API", version="1.0.0")


@app.on_event("startup")
def bootstrap_vector_store():
    setup_vector_store()

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

allowed_origins = ["http://localhost:3000"]
extra_origins = os.getenv("ALLOWED_ORIGINS", "")
if extra_origins:
    allowed_origins += [origin.strip() for origin in extra_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"error": "Rate limit exceeded. You can generate 3 specs per hour. Please try again later."}
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    msg = errors[0].get("msg", "Invalid request.") if errors else "Invalid request."
    return JSONResponse(status_code=422, content={"error": msg.replace("Value error, ", "")})


MISSING_KEY_HINT = (
    "A Gemini API key is required. Paste yours in the field above — "
    "get one free at https://aistudio.google.com/apikey"
)
GEMINI_KEY_HINT = (
    "That doesn't look like a Google Gemini API key. AI Studio keys start with "
    "'AQ.' (older ones start with 'AIza') — get one free at "
    "https://aistudio.google.com/apikey"
)


class IdeaRequest(BaseModel):
    idea: str
    # Bring-your-own-key: every request must carry the caller's own Google
    # Gemini (AI Studio) key. There is no shared server key for public traffic —
    # each analysis makes 6 Gemini calls that run entirely on the caller's quota.
    # It has to be a Gemini key because every agent talks to Google via
    # google-genai; another provider's key passes Pydantic but fails at call time.
    # Google AI Studio now issues "auth keys" prefixed "AQ." — older "standard"
    # keys are prefixed "AIza" and are being retired through 2026.
    api_key: str | None = Field(default=None, validate_default=True)

    @field_validator("api_key", mode="before")
    @classmethod
    def _require_gemini_key(cls, v):
        v = str(v or "").strip()
        if not v:
            raise ValueError(MISSING_KEY_HINT)
        if not (v.startswith("AQ.") or v.startswith("AIza")) or len(v) < 20:
            raise ValueError(GEMINI_KEY_HINT)
        return v




@app.api_route("/", methods=["GET", "HEAD"])
def root():
    return {"message": "SpecForge backend is running"}


@app.post("/generate-spec")
@limiter.limit("3/hour")
async def generate_spec(request: Request, body: IdeaRequest):
    result = spec_pipeline.invoke({
        "idea": body.idea,
        "api_key": body.api_key,
        "business_analysis": None,
        "dev_concerns": None,
        "qa_concerns": None,
        "security_concerns": None,
        "ux_concerns": None,
        "final_spec": None
    })
    project_id = save_project(
        user_id="anonymous",
        title=body.idea[:80],
        idea=body.idea
    )

    save_specification(project_id, result)

    return {
        "project_id": project_id,
        "business_analysis": result.get("business_analysis"),
        "dev_concerns": result.get("dev_concerns"),
        "qa_concerns": result.get("qa_concerns"),
        "security_concerns": result.get("security_concerns"),
        "ux_concerns": result.get("ux_concerns"),
        "final_spec": result.get("final_spec")
    }


@app.post("/generate-spec-stream")
@limiter.limit("3/hour")
async def generate_spec_stream(request: Request, body: IdeaRequest):

    async def event_generator():
        state = {
            "idea": body.idea,
            "api_key": body.api_key,
            "business_analysis": None,
            "dev_concerns": None,
            "qa_concerns": None,
            "security_concerns": None,
            "ux_concerns": None,
            "final_spec": None
        }
        agents = [
            ("business",     business_analyst_node, "business_analysis"),
            ("developer",    developer_node,        "dev_concerns"),
            ("qa",           qa_node,               "qa_concerns"),
            ("security",     security_node,         "security_concerns"),
            ("ux",           ux_node,               "ux_concerns"),
            ("orchestrator", orchestrator_node,     "final_spec"),
        ]

        for i, (agent_name, agent_fn, output_key) in enumerate(agents):
            if i > 0 and AGENT_DELAY_SECONDS > 0:
                await asyncio.sleep(AGENT_DELAY_SECONDS)
            yield f"data: {json.dumps({'type': 'status', 'agent': agent_name, 'status': 'running'})}\n\n"
            state = await asyncio.to_thread(agent_fn, state)
            output = state.get(output_key)
            yield f"data: {json.dumps({'type': 'result', 'agent': agent_name, 'data': output})}\n\n"

        try:
            project_id = save_project(
                user_id="anonymous",
                title=body.idea[:80],
                idea=body.idea
            )
            save_specification(project_id, state)
            yield f"data: {json.dumps({'type': 'done', 'project_id': project_id})}\n\n"
        except Exception:
            yield f"data: {json.dumps({'type': 'done', 'project_id': None})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )