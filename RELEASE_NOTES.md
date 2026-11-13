# VEIL 0.1.0 — research prototype

Prepared November 13, 2026. Policy version remains 0.0.2; release and policy versions describe different artifacts.

## Included

- Advisory CLI and stdio MCP server with labeled offline fixtures.
- Portable seven-principle policy and validated proceed/ask/hold contract.
- Streaming two-arm comparison with a configurable completion cap.
- Sequential request pacing, bounded temporary-429 retries, provider-delay handling, quota stops, and safe attempt diagnostics.
- Offline login assessment and recovery, action binding, expiry/revocation checks, single-use grants and one-attempt approval budgets.
- Hardened malformed-provider-code handling and login identity validation.

## Verification

Python 3.12, pinned integration environment:

- `python -m unittest discover -s prototype -v`: 41 passed.
- `python prototype/validate_pairs.py`: 10 pairs / 20 cases validated; no expected answers in model inputs.
- `python prototype/mcp_smoke.py`: discovery, proceed/ask/hold fixtures and invalid-input hold passed.
- `python prototype/login_flow.py`: one mock execution; zero real executions.

Test totals combine overlapping prior branches; they must not be added together as separate coverage totals. Tests establish implemented routing and safety checks under synthetic conditions, not ethical effectiveness or production security.

## Pending

Successful live provider comparison, independent review, broader semantic evaluation, authenticated connectors, signed policy distribution, durable audit, concurrency controls and release licensing decisions. API funding is not required to use the offline demonstrations.

This publication supersedes the earlier requirement to wait for a live result before merging the experimental runner: live results remain an explicit validation gap rather than a claim attached to this offline-first release.
