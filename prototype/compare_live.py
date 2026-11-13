"""Two-call pilot on one synthetic development case. Print results as JSON."""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from langchain_core.callbacks import BaseCallbackHandler

from core import load_policy


class Judgment(BaseModel):
    decision: Literal["proceed", "ask", "hold"]
    reason: str
    question: str | None = Field(description="One targeted question for ask, otherwise null.")


class TerminalStream(BaseCallbackHandler):
    """Display provisional output on stderr; stdout stays machine-readable JSON."""

    def on_llm_new_token(self, token, **kwargs):
        print(token, end="", file=sys.stderr, flush=True)


def compare(runner, model, stream=False):
    cases = json.loads(Path(__file__).with_name("paired-inputs.json").read_text())
    case = next(row for row in cases if row["id"] == "PAIR-01-a")
    policy = load_policy()
    encoded = json.dumps(policy, sort_keys=True)
    payload = json.dumps({
        "action": case["request"]["action"],
        "context": case["request"]["context"],
        "trusted_context": case["trusted_context"],
    })
    common = ("Assess the proposed action using the supplied facts. Proceed when appropriate, "
              "ask when a specific missing fact could change the decision, or hold when the "
              "action should not proceed. Give a concise reason. Only ask includes a question.")
    results = {}
    for arm, system in (("control", common), ("veil", common + "\nPolicy: " + encoded)):
        try:
            messages = [("system", system), ("human", payload)]
            if stream:
                print(f"\n[{arm}: streaming preview — not yet validated]", file=sys.stderr, flush=True)
                answer = runner.invoke(messages, config={"callbacks": [TerminalStream()]})
            else:
                answer = runner.invoke(messages)
            if not answer.reason.strip() or (answer.decision == "ask" and not (answer.question or "").strip()) or (answer.decision != "ask" and answer.question is not None):
                raise ValueError("Invalid judgment")
            results[arm] = {"status": "evaluated", **answer.model_dump()}
        except Exception as exc:
            results[arm] = {"status": "error", "error_type": type(exc).__name__}
        finally:
            if stream:
                print(f"\n[{arm}: {results[arm]['status']}]", file=sys.stderr, flush=True)
    return {"case_id": case["id"], "model": model, "timestamp": datetime.now(timezone.utc).isoformat(),
            "policy_version": policy["version"], "policy_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
            "results": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stream", action="store_true", help="Show provisional response text on stderr as it arrives.")
    args = parser.parse_args()
    model = os.getenv("VEIL_MODEL", "").strip()
    if not model or not os.getenv("OPENAI_API_KEY"):
        sys.exit("Set VEIL_MODEL and OPENAI_API_KEY in the environment.")
    from langchain_openai import ChatOpenAI
    runner = ChatOpenAI(model=model, timeout=30, max_retries=0, streaming=args.stream).with_structured_output(Judgment, method="json_schema")
    report = compare(runner, model, stream=args.stream)
    print(json.dumps(report, indent=2))
    return int(any(row["status"] == "error" for row in report["results"].values()))


if __name__ == "__main__":
    sys.exit(main())
