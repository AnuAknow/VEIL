import json
from pathlib import Path
from core import evaluate
cases = json.loads(Path(__file__).with_name("scenarios.json").read_text())
results = []
for case in cases:
    result = evaluate(case["request"], case["trusted_context"], lambda *_: case["fixture_assessment"])
    results.append({"scenario":case["id"], **result})
print(json.dumps(results, indent=2))
