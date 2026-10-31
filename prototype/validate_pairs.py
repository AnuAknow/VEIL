import json
from collections import Counter
from pathlib import Path
p=Path(__file__).parent
inputs=json.loads((p/'paired-inputs.json').read_text())
key=json.loads((p/'paired-answer-key.json').read_text())
manifest=json.loads((p/'paired-manifest.json').read_text())
ids=[x['id'] for x in inputs]
assert len(ids)==len(set(ids))==20
assert set(ids)=={x['id'] for x in key}
assert len(manifest)==10
assert {i for pair in manifest for i in pair['case_ids']}==set(ids)
by_id={x['id']:x for x in inputs}
answers={x['id']:x for x in key}
for case in inputs:
    assert set(case)=={'id','request','trusted_context'}
    assert set(case['request'])=={'request_id','action','context'}
    assert case['id']==case['request']['request_id']
for pair in manifest:
    a,b=pair['case_ids']
    assert by_id[a]['request']['action']==by_id[b]['request']['action']
    assert answers[a]['expected_decision']!=answers[b]['expected_decision']
print('Validated 10 pairs / 20 cases; inputs contain no expected outcomes.')
print(dict(Counter(x['expected_decision'] for x in key)))
