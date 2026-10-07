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

## 2026-10-07 — Fundamental Analyst live strict-v0 verification

Status: VERIFIED for live contract compliance.

Runtime:
- model: `deepseek-chat`;
- adapter: `DeepSeekStructuredResearchModel`;
- engine: `FundamentalAnalystEngine`;
- LangSmith tracing: disabled;
- evidence source: controlled test fixture;
- repository writes during live run: none.

Observed result:
- returned `FundamentalResearchDraft`;
- research run identity remained `RUN1`;
- company, ticker, as-of, and report period remained unchanged;
- Evidence Service target identity was `EVIDENCE-C1`;
- Analyst claim identity used its own namespace beginning with `C1`;
- one `OBSERVED_FACT` used direct `evidence_refs = ["E1"]` and no
  `supporting_claim_ids`;
- two `ANALYST_INFERENCE` claims used no direct `evidence_refs`, used
  `supporting_claim_ids`, and contained explicit assumptions;
- one `FORWARD_VIEW` used no direct `evidence_refs`, used supporting claims,
  and contained explicit assumptions;
- outlook was `UNDETERMINED`;
- confidence was `LOW`;
- the complete draft passed the archived strict-v0 structural contract.

This verification establishes that the live DeepSeek-backed Fundamental
Analyst can produce an output accepted by the strict-v0 claim-chain contract.

It does not establish:
- substantive investment-research quality;
- semantic correctness of every Analyst claim;
- Claim Reviewer live behavior;
- PASS/PARTIAL/FAIL publication behavior under a real model;
- full workflow correctness;
- real Financial Evidence Service / Retrieval Lab integration;
- Quant Desk integration.

The earlier pre-clarification live run remains preserved separately and is not
rewritten or retroactively reclassified.
