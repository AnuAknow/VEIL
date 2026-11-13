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
from request_control import RequestController


class Judgment(BaseModel):
    decision: Literal["proceed", "ask", "hold"]
    reason: str
    question: str | None = Field(description="One targeted question for ask, otherwise null.")


class TerminalStream(BaseCallbackHandler):
    """Display provisional output on stderr; stdout stays machine-readable JSON."""

    def on_llm_new_token(self, token, **kwargs):
        print(token, end="", file=sys.stderr, flush=True)


def compare(runner, model, stream=False, controller=None):
    controller = controller or RequestController(interval=0, retries=0)
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
    request_metrics = {}
    for arm, system in (("control", common), ("veil", common + "\nPolicy: " + encoded)):
        try:
            messages = [("system", system), ("human", payload)]
            def invoke(attempt):
                if stream:
                    print(f"\n[{arm}: attempt {attempt}; streaming preview — not yet validated]", file=sys.stderr, flush=True)
                    return runner.invoke(messages, config={"callbacks": [TerminalStream()]})
                return runner.invoke(messages)
            answer, metrics = controller.call(invoke)
            request_metrics[arm] = metrics
            if metrics.get("skipped"):
                results[arm] = {"status": "skipped", "reason": metrics["stop_reason"]}
                continue
            if "error_type" in metrics:
                results[arm] = {"status": "error", "error_type": metrics["error_type"]}
                continue
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
            "results": results, "request_metrics": request_metrics}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stream", action="store_true", help="Show provisional response text on stderr as it arrives.")
    parser.add_argument("--max-tokens", type=int, default=1024, help="Maximum completion tokens per request (default: 1024).")
    parser.add_argument("--min-interval", type=float, default=2, help="Minimum seconds between request starts (0–60; default: 2).")
    parser.add_argument("--max-retries", type=int, default=2, help="Retries per arm for classified temporary rate limits (0–5; default: 2).")
    parser.add_argument("--max-retry-wait", type=float, default=30, help="Stop if provider/backoff delay exceeds this many seconds (0–60; default: 30).")
    args = parser.parse_args()
    if args.max_tokens < 1:
        parser.error("--max-tokens must be a positive integer")
    try:
        controller = RequestController(args.min_interval, args.max_retries, args.max_retry_wait)
    except ValueError as exc:
        parser.error(str(exc))
    model = os.getenv("VEIL_MODEL", "").strip()
    if not model or not os.getenv("OPENAI_API_KEY"):
        sys.exit("Set VEIL_MODEL and OPENAI_API_KEY in the environment.")
    from langchain_openai import ChatOpenAI
    runner = ChatOpenAI(model=model, timeout=30, max_retries=0, streaming=args.stream, max_tokens=args.max_tokens).with_structured_output(Judgment, method="json_schema")
    report = compare(runner, model, stream=args.stream, controller=controller)
    report["max_tokens"] = args.max_tokens
    report["request_settings"] = {"min_interval_seconds": args.min_interval,
                                  "max_retries": args.max_retries, "max_retry_wait_seconds": args.max_retry_wait}
    print(json.dumps(report, indent=2))
    return int(any(row["status"] != "evaluated" for row in report["results"].values()))


if __name__ == "__main__":
    sys.exit(main())
