# VEIL v001: one evaluation flow
Draft prototype, policy 0.0.2, updated 2026-10-31. Python 3.10+. Offline demo requires no API key or third-party packages.

## Run
From this extracted directory, run:
    python -m unittest -v
    python demo.py

## Flow
Validate request -> verify trusted authorization and scope -> assess against policy -> validate assessment -> return proceed / ask / hold.
A denial takes priority over missing context. Unknown permission produces ask; an invalid evaluation produces hold.
No action is executed. All 30 scenarios are synthetic.

## Files
- baseline.json: seven portable principles, decision meanings and precedence.
- assessment.schema.json: portable model-response contract. core.py additionally enforces question/decision consistency.
- core.py: framework-independent evaluation and code-derived execution eligibility.
- scenarios.json: 10 proceed, 10 ask, 10 hold cases with expected outcomes and offline fixtures.
- langchain_adapter.py: optional structured-output adapter.
- test_veil.py: scenario harness, negative tests and clarification transitions.
- demo.py: outputs the example evaluations.

## What the tests establish
Offline fixtures supply the model assessment. Passing tests validates routing, validation, denial precedence and adapter wiring. It DOES NOT establish that an LLM understands ethics or classifies these scenarios correctly. Never pass expected_decision or fixture_assessment to a real model.

## Optional LangChain integration
Install LangChain and your selected provider package in a separate environment. Configure credentials through environment variables and supply a chat model:

    from langchain.chat_models import init_chat_model
    from langchain_adapter import LangChainAssessor
    from core import evaluate
    model = init_chat_model("PROVIDER:MODEL", timeout=30, max_retries=1)
    assessor = LangChainAssessor(model)
    result = evaluate(request, trusted_context, assessor)

Replace PROVIDER:MODEL with a supported model identifier. Provider parameters and structured output support must be verified for that model.
Reference: https://reference.langchain.com/python/langchain-core/language_models/chat_models/BaseChatModel/with_structured_output
Live LangChain/provider calls have not been run; adapter is tested with a fake model. The root requirements.txt pins the locally installed and integration-tested dependencies.

## Trust and execution
trusted_context must come from application authentication/authorization code, not user or model assertions. This local demo cannot authenticate callers and exposes no public endpoint.
eligible_to_execute is informational, not a reusable authorization token. A future executor must enforce the gate, bind the result to exact action arguments, recheck current authorization and prevent alternate paths.
After clarification rerun the entire evaluation. A reply does not automatically clear a hold.
Keep policy files server-controlled and version changes reviewed. Editing policy prose does not update deterministic enforcement logic.
Prompt instructions do not prevent all prompt injections or judgment errors.

## Scope and next milestone
The baseline derives from seven principles drafted in the conversation; the Covenant and ethics book are not incorporated yet. This is not a compliance certification or validated hiring system.
An MCP stdio server and configurable live-model entry point are now included; see the repository root README. No retrieval pipeline, production executor, durable audit log or validated live-model results are included.
Next: select a provider/model, run the same cases without fixture answers, measure false permits and false blocks, and add paraphrases/adversarial inputs before exposing MCP.
Future logs should retain only necessary evaluation metadata, not raw private prompts by default.


## Baseline revision 0.0.2
Preserves all seven rule IDs. Adds refinements under authorization/scope (entrusted resources), context/consequences (physical harm), evidence/truthfulness (deceptive representations), and proportionality (restraint).
These interpretations arose from our discussion of selected commandments. They require no religious agreement. No full-book research or new compliance claim is implied.
Fifteen additional cases cover transparent corrections versus fraud, synthetic test records versus false consent, proportionate access, repurposing, and physical safety. All new cases have technically granted permission so the semantic assessor must distinguish permission from ethical appropriateness.
Offline results remain fixture-based. The adapter test verifies that all four refinements reach the model prompt; it does not verify that a live model obeys them.

## Paired evaluation addition
Ten new paired situations (20 cases) are in paired-inputs.json; expected outcomes and reviewer metadata are separate. Read PAIR-EVALUATION.md before model testing. Run python validate_pairs.py for offline data validation. Policy remains 0.0.2. No live comparison has run.
