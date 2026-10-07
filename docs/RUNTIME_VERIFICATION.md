# Runtime Verification

This document records actual execution facts separately from planned
architecture and mocked test coverage.

## 2026-10-07 — DeepSeek structured-output runtime

Status: VERIFIED

Environment:
- provider adapter: `DeepSeekStructuredResearchModel`
- model: `deepseek-chat`
- provider package: `langchain-deepseek`
- API credential source: process environment only
- repository credential storage: none
- LangSmith tracing during smoke call: disabled

Verified facts:
- the archived DeepSeek adapter imported successfully;
- a real DeepSeek API request completed successfully;
- the provider accepted the requested Pydantic structured-output schema;
- the result was returned through the shared structured-model adapter;
- the returned object validated as the requested Pydantic model;
- the smoke result contained `status = ok` and `number = 1`;
- the live call did not modify repository state.

This verification proves provider connectivity and structured-output
compatibility only.

It does not prove:
- real Fundamental Analyst research quality;
- real Claim Reviewer behavior;
- PASS/PARTIAL/FAIL behavior under live model output;
- end-to-end Financial Research Workflow correctness;
- Evidence Service / Retrieval Lab integration;
- Quant Desk integration;
- LangSmith production tracing.

Secrets:
- `DEEPSEEK_API_KEY` must never be committed or written into project artifacts.
