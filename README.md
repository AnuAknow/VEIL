# VEIL — working advisory prototype

The runnable prototype is in **prototype/**. The earlier vector experiments in this repository remain historical material and are not used by the new evaluator.

## Start in GitHub Codespaces
Select this branch under Code → Codespaces → Create codespace. Setup installs the pinned Python dependencies automatically.

From the repository terminal:
    python prototype/cli.py list
    python prototype/cli.py demo P01
    python prototype/cli.py demo A01
    python prototype/cli.py demo H01

These return proceed, ask and hold using **labeled fixtures**, without an API key. They do not demonstrate live ethical reasoning.

Run checks:
    python -m unittest discover -s prototype -v
    python prototype/validate_pairs.py
    python prototype/mcp_smoke.py

## Review your own request using LangChain
Add OPENAI_API_KEY as a Codespaces secret for this repository; rebuild/restart the Codespace if required for the secret to become available. Never commit or paste a key into source files.
Set VEIL_MODEL to a model ID available to your provider account:
    export VEIL_MODEL='your-model-id'
    python prototype/cli.py review --action "Correct this invoice total" --context "The receipt supports the correction and the original will remain available."

This path makes a paid provider call and sends the action, context and policy to the provider. Use synthetic information first. Missing configuration, timeout or invalid output returns status=error and hold; it must not be counted as a successful ethical decision.
Only the OpenAI provider is configured in this initial adapter. No live provider call has been validated in the build environment.

## MCP server
    python prototype/mcp_server.py

The server waits for an MCP client over stdio; an idle terminal is expected. Configure your client's command as the absolute Python executable path and its args as the absolute path to prototype/mcp_server.py. Configure model credentials in the server environment for veil_review.
Tools:
- veil_scenarios: list synthetic examples.
- veil_demo: predefined fixture output.
- veil_review: advisory assessment of an arbitrary request using the configured model.

## Boundaries
Policy 0.0.2 remains independent of LangChain. No actions are executed. The public service never grants execution eligibility or verifies user authority; proceed is advice only. Existing core permission-gate tests simulate trusted authorization inputs. Production enforcement requires authenticated, action-bound authority and a non-bypassable executor.
This is a local single-user research prototype, not a production safety or compliance service.
The test suite checks routing, validation and integration. The 20 paired semantic cases remain unrun against a live model; see prototype/PAIR-EVALUATION.md.
