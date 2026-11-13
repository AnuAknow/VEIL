# VEIL — Values-Encoded Integration Layer

**Version 0.1.0 · Research prototype · Policy 0.0.2**

VEIL explores a practical question: should an AI-assisted action proceed, require clarification, or be held? It combines a portable ethical baseline, deterministic permission checks, an advisory MCP interface, and an offline login simulator.

**Start without API credits.** The offline examples use synthetic evidence and predefined assessments. They demonstrate control behavior, not a model's ethical understanding.

## Five-minute offline start

Requires Python 3.10 or newer. From the repository root:

```bash
python prototype/login_flow.py
python prototype/cli.py demo P01
python prototype/cli.py demo A01
python prototype/cli.py demo H01
python -m unittest discover -s prototype -p test_login_flow.py -v
python -m unittest discover -s prototype -p test_veil.py -v
python prototype/validate_pairs.py
```

The login demo moves from missing permission to verified fixture approval, records one mock attempt, and holds expired or denied activity. It performs no real login. The other examples demonstrate proceed, ask, and hold with labeled fixtures.

## What is implemented

| Component | Behavior | Boundary |
| --- | --- | --- |
| Portable baseline | Seven principles in `prototype/baseline.json` | Framework-independent; not signed or immutable storage |
| Core evaluator | Permission/scope checks, response validation, three decisions | Trusted authority is supplied by caller code |
| Offline login gate | Revalidation, exact request binding, expiry, single-use grants, shared approval budget | Synthetic authority, single-threaded, in-memory state |
| Advisory CLI/MCP | Reviews requests and exposes fixture examples | Never grants execution permission or executes real actions |
| Comparison runner | Same synthetic case with/without policy, optional streaming, completion cap | Fixed order; one development case, not an effectiveness benchmark |
| Request control | Pacing, bounded 429 retries, quota stop, safe diagnostics | Comparison runner only; not a system-wide spending limit |

## Optional integration setup

Create an isolated environment and install dependencies only for MCP, live evaluation, or the full test suite:

```bash
python -m venv .venv
# Linux/macOS/Codespaces:
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s prototype -v
python prototype/mcp_smoke.py
```

Codespaces installs the pinned dependencies during setup. The offline quickstart above can also run locally without installation.

## Optional paid model comparison

Configure `OPENAI_API_KEY` through your environment or Codespaces secrets, and `VEIL_MODEL` to an available OpenAI model supporting structured output. Do not put keys in source, terminal screenshots, or Git commits.

```bash
export VEIL_MODEL='your-model-id'
python prototype/compare_live.py --stream --max-tokens 1024 --min-interval 2 --max-retries 2 --max-retry-wait 30
```

This sends the synthetic case and policy to the provider and may incur charges. Streaming previews go to stderr; final JSON goes to stdout. Invalid/incomplete outputs remain errors. Confirmed quota failures stop further calls. Pacing and retries are documented in [prototype/README.md](prototype/README.md).

**Live validation is pending.** Previous attempts returned rate-limit errors with a reported zero API balance. No successful live comparison or ethical-accuracy score is claimed. A larger paired evaluation plan is in [PAIR-EVALUATION.md](prototype/PAIR-EVALUATION.md).

## MCP interface

```bash
python prototype/mcp_server.py
```

This is a local stdio server; waiting silently for a client is expected. Configure your MCP client's command with an absolute Python executable and the absolute script path as its argument. Tools: `veil_scenarios`, `veil_demo`, and `veil_review`. Only `veil_review` uses a configured paid model. It is advisory and does not verify user authority. The comparison runner's throttle does not apply to this tool.

## Evidence and limitations

The 0.1.0 preparation passed **41 offline tests**, validated 10 pairs / 20 inputs, and passed an actual local MCP round trip. Streaming tests simulate provider responses. See [release notes](RELEASE_NOTES.md) and [login flow](prototype/LOGIN-FLOW.md).

This is not a production security boundary, compliance certification, autonomous incident-response service, or validated hiring system. There are no real enforcement connectors, signed baseline releases, durable audit storage, distributed budget reservations, or guarantees against prompt injection. A policy digest identifies content; it does not authenticate its author. Production deployment would require independent security review and trusted enforcement outside the model.

Earlier `data/` vector experiments and `load_the_veil.py` are historical research and are not used by this evaluator. Development was led by Everett Aknowledge with AI-assisted implementation and review. This repository currently has no open-source license; public visibility should not be represented as an unrestricted license grant.
