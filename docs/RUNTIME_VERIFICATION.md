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

## 2026-10-07 — Fundamental Analyst live smoke under pre-clarification contract

Status: EXECUTED; technically successful under the contract active at run time.

Observed live result:
- the real `FundamentalAnalystEngine` returned a valid
  `FundamentalResearchDraft`;
- run identity, company, ticker, as-of, and report period remained stable;
- the result contained three claims;
- the observed-fact claim cited supplied evidence `E1`;
- two `ANALYST_INFERENCE` claims also carried direct `evidence_refs = ["E1"]`;
- outlook was `UNDETERMINED`;
- confidence was `LOW`;
- repository state remained unchanged.

Subsequent contract clarification:
- Evidence Service `target_claim_id` and Analyst `claim_id` are separate
  namespaces, so an EvidenceItem target ID differing from an Analyst claim ID
  is not itself a defect;
- strict v0 now requires `ANALYST_INFERENCE` and `FORWARD_VIEW` to leave
  `evidence_refs` empty and trace through `supporting_claim_ids`;
- therefore the two live inference claims would not comply with the newly
  adopted strict-v0 claim-link rule.

This is not a retroactive failure of the earlier schema or validator.

The original live execution fact remains preserved as observed.

DeepSeek provider verification remains based on the earlier dedicated live
provider smoke test. This contract clarification did not independently rerun or
reverify provider connectivity.
