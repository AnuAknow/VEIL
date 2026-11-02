"""Framework-independent evaluation; never executes external actions."""
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).parent

def load_policy():
    policy = json.loads((ROOT / "baseline.json").read_text())
    ids = [r["id"] for r in policy["rules"]]
    if len(ids) != len(set(ids)) or not ids:
        raise ValueError("Invalid policy")
    return policy

def validate_assessment(value, policy):
    # Explicit validation keeps the offline core dependency-free.
    if not isinstance(value, dict) or set(value) != {"decision", "reason", "rule_ids", "question"}:
        raise ValueError("Unexpected assessment shape")
    if value["decision"] not in ("proceed", "ask", "hold"):
        raise ValueError("Unknown decision")
    if not isinstance(value["reason"], str) or not value["reason"].strip():
        raise ValueError("Missing reason")
    ids = value["rule_ids"]
    known = {r["id"] for r in policy["rules"]}
    if not isinstance(ids, list) or not ids or any(not isinstance(i, str) or i not in known for i in ids):
        raise ValueError("Unknown rule")
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate rules")
    q = value["question"]
    if q is not None and (not isinstance(q, str) or not q.strip()):
        raise ValueError("Invalid question")
    if value["decision"] == "ask" and q is None:
        raise ValueError("Ask requires targeted question")
    if value["decision"] != "ask" and q is not None:
        raise ValueError("Only ask may have question")
    return value

def evaluate(request, trusted_context, assessor):
    """trusted_context must come from application auth, never user/model claims.
    assessor(request, policy) returns an assessment dictionary.
    """
    policy = load_policy()
    def result(decision, reason, rules, question=None):
        return {"policy_id":policy["policy_id"], "policy_version":policy["version"],
                "policy_sha256":hashlib.sha256(json.dumps(policy, sort_keys=True).encode()).hexdigest(),
                "decision":decision, "reason":reason, "rule_ids":rules, "question":question,
                "eligible_to_execute":decision == "proceed", "execution_performed":False}
    if not isinstance(request, dict) or set(request) != {"request_id", "action", "context"} or any(
        not isinstance(request[k], str) or not request[k].strip() for k in request):
        return result("hold", "Invalid request.", ["VEIL-005"])
    if not isinstance(trusted_context, dict) or set(trusted_context) != {"authorization", "scope"}:
        return result("hold", "Invalid trusted context.", ["VEIL-002"])
    if trusted_context["authorization"] not in ("granted", "denied", "unknown") or trusted_context["scope"] not in ("within", "outside", "unknown"):
        return result("hold", "Invalid permission or scope value.", ["VEIL-002"])
    if trusted_context["authorization"] == "denied" or trusted_context["scope"] == "outside":
        return result("hold", "Verified permission or scope boundary prevents this action.", ["VEIL-002"])
    if "unknown" in trusted_context.values():
        return result("ask", "Permission or scope needs verification.", ["VEIL-002"],
                      "Can an authorized source verify permission and scope for this action?")
    try:
        a = validate_assessment(assessor(request.copy(), json.loads(json.dumps(policy))), policy)
    except Exception:
        return result("hold", "Assessment unavailable or invalid; review before retry.", ["VEIL-005", "VEIL-007"])
    return result(a["decision"], a["reason"], a["rule_ids"], a["question"])
