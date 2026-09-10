import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

from backend.agents.business_agent import business_analyst_node

state = {
    "idea": "An app that helps students find study partners near them using AI matching",
    "api_key": os.getenv("GEMINI_API_KEY"),
}

result = business_analyst_node(state)

print("\n=== BUSINESS ANALYSIS RESULT ===")
print("Status:", result.get("business_analysis_status"))
print("Verdict:", result.get("business_verdict"))
print("Scores:", result.get("business_score"))
print("Concerns:", result.get("business_concerns"))