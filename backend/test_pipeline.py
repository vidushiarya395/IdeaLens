import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

from backend.agents.pipeline import spec_pipeline

state = {
    "idea": "An app that helps students find study partners near them using AI matching",
    "api_key": os.getenv("GEMINI_API_KEY"),
    "business_analysis": None,
    "dev_concerns": None,
    "qa_concerns": None,
    "security_concerns": None,
    "ux_concerns": None,
    "final_spec": None
}

print("Running full pipeline...")
result = spec_pipeline.invoke(state)

print("\n=== PIPELINE RESULTS ===")
print("Business Status:", result.get("business_analysis_status"))
print("Developer Status:", result.get("developer_status"))
print("QA Status:", result.get("qa_status"))
print("Security Status:", result.get("security_status"))
print("UX Status:", result.get("ux_status"))
print("Orchestrator Status:", result.get("orchestrator_status"))
print("\nProject Viability:", result.get("project_viability"))
print("Final Recommendation:", result.get("final_recommendation"))