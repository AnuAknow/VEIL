"""Advisory review service. Never grants permission or executes actions."""
import hashlib
import json
import os
from pathlib import Path
from core import load_policy, validate_assessment, evaluate
from langchain_adapter import LangChainAssessor
ROOT = Path(__file__).parent

def live_assessor():
    model = os.environ.get("VEIL_MODEL", "").strip()
    if not model or not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("Configure VEIL_MODEL and OPENAI_API_KEY")
    from langchain_openai import ChatOpenAI
    return LangChainAssessor(ChatOpenAI(model=model, timeout=30, max_retries=0))

def review(action, context, assessor_factory=live_assessor):
    policy = load_policy()
    base = {"mode":"live", "advisory_only":True, "authorization_verified":False,
            "eligible_to_execute":False, "execution_performed":False,
            "policy_id":policy["policy_id"], "policy_version":policy["version"],
            "policy_sha256":hashlib.sha256(json.dumps(policy,sort_keys=True).encode()).hexdigest()}
    if any(not isinstance(v,str) or not v.strip() or len(v)>20000 for v in (action,context)):
        return {**base, "status":"error", "decision":"hold", "reason":"Provide action and context, each 1–20,000 characters.", "rule_ids":["VEIL-005"], "question":None}
    request={"request_id":"advisory-review","action":action,"context":context}
    try:
        assessment=validate_assessment(assessor_factory()(request,policy),policy)
        return {**base, **assessment, "status":"evaluated"}
    except Exception:
        return {**base, "status":"error", "decision":"hold",
                "reason":"Live assessment unavailable or invalid. Check model configuration and provider access.",
                "rule_ids":["VEIL-005","VEIL-007"], "question":None}

def scenarios():
    return json.loads((ROOT/"scenarios.json").read_text())

def demo(case_id):
    case=next((c for c in scenarios() if c["id"]==case_id),None)
    if case is None: raise ValueError("Unknown scenario ID")
    result=evaluate(case["request"],case["trusted_context"],lambda *_:case["fixture_assessment"])
    return {**result, "eligible_to_execute":False, "mode":"fixture_demo",
            "advisory_only":True, "authorization_verified":False, "status":"fixture",
            "note":"Predefined fixture response, not live model judgment.", "scenario_id":case_id}
