from typing import TypedDict, Dict, Any, List, Optional

class SpecForgeState(TypedDict, total=False):

    # Input
    idea: str
    api_key: Optional[str]

    # Business Agent
    business_analysis: Optional[Dict[str, Any]]
    business_analysis_status: Optional[str]
    business_verdict: Optional[str]
    business_score: Optional[Dict[str, int]]
    business_key_questions: Optional[List[str]]
    business_concerns: Optional[List[str]]
    business_missing_requirements: Optional[List[str]]
    business_assumptions: Optional[List[str]]

    # Developer Agent
    dev_concerns: Optional[Dict[str, Any]]
    developer_status: Optional[str]
    developer_verdict: Optional[str]
    developer_scores: Optional[Dict[str, int]]
    developer_architecture_concerns: Optional[List[str]]
    developer_scalability_risks: Optional[List[str]]
    developer_blockers: Optional[List[str]]

    # QA Agent
    qa_concerns: Optional[Dict[str, Any]]
    qa_status: Optional[str]
    qa_verdict: Optional[str]
    qa_scores: Optional[Dict[str, int]]
    critical_test_areas: Optional[List[str]]
    edge_cases: Optional[List[str]]
    failure_scenarios: Optional[List[str]]
    testing_strategy: Optional[List[str]]
    qa_blockers: Optional[List[str]]

    # Security Agent
    security_concerns: Optional[Dict[str, Any]]
    security_status: Optional[str]
    security_verdict: Optional[str]
    security_scores: Optional[Dict[str, int]]
    critical_vulnerabilities: Optional[List[str]]
    compliance_risks: Optional[List[str]]
    mitigation_strategies: Optional[List[str]]
    security_blockers: Optional[List[str]]

    # UX Agent
    ux_concerns: Optional[Dict[str, Any]]
    ux_status: Optional[str]
    ux_verdict: Optional[str]
    ux_scores: Optional[Dict[str, int]]
    onboarding_issues: Optional[List[str]]
    accessibility_concerns: Optional[List[str]]
    retention_risks: Optional[List[str]]
    ux_blockers: Optional[List[str]]

    # Orchestrator Agent
    final_spec: Optional[Dict[str, Any]]
    orchestrator_status: Optional[str]
    project_viability: Optional[str]
    functional_requirements: Optional[List[str]]
    non_functional_requirements: Optional[List[str]]
    mvp_scope: Optional[List[str]]
    launch_risks: Optional[List[str]]
    final_recommendation: Optional[str]