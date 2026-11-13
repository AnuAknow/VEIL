# Offline login assessment and recovery

Run from the repository root, with Python 3.10+ and no API key, credits, or third-party dependencies:

```bash
python prototype/login_flow.py
python -m unittest discover -s prototype -p 'test_login_flow.py' -v
```

The demonstration records unknown authorization (ask), a new verified fixture approval (proceed), one mock attempt, expiration before a subsequent attempt (hold), and explicit denial (hold). Earlier records remain in history and reevaluation links to its predecessor.

The only permitted operation is one synthetic negative-login attempt against `mock://staging/login`. There is no HTTP client, credential input, real login, or live model call. A proceed result authorizes only this mock operation; it makes no claim about general ethical appropriateness or whether a real login rejected invalid credentials correctly.

## Boundaries tested

- Missing permission asks; explicit denial holds even when time evidence is missing.
- Time windows require timezone-aware instants and use start-inclusive/end-exclusive boundaries.
- Each grant binds the exact principal, target, method, attempt count, approval record, and baseline digest.
- The execution boundary rechecks the trusted fixture source and current time.
- Changed requests, changed policy, revoked/revised authority, expired windows, and unavailable evidence cannot produce mock execution.
- Grants are single-use. All grants under the same principal/approval revision share a one-attempt budget; reevaluation does not reset that budget.
- Mutating a returned decision cannot create a grant. An ask/hold identifier cannot execute.
- Every result has `execution_performed: false`; only `mock_execution_performed` can become true.

## Deliberate limits

Approval fixtures are supplied by trusted Python code, not authenticated external records. The digest detects a baseline change between assessment and execution; it does not authenticate the baseline's origin. Mandatory login restrictions are explicit code, not inferred from policy prose. No signed policies, durable audit, distributed locking, production credentials, real containment, or full core-spec compliance is claimed. The mock is single-threaded; a production executor must reserve budgets atomically and coordinate authorization with the action boundary.

This feature is independent of the live comparison PR. Model funding is unnecessary for its tests.
