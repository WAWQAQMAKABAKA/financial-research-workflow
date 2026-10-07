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

## 2026-10-07 — Claim Reviewer live semantic-gate verification

Status: VERIFIED for live claim-level semantic review in English and Chinese.

Runtime:
- model: `deepseek-chat`;
- adapter: `DeepSeekStructuredResearchModel`;
- engine: `ClaimReviewerEngine`;
- LangSmith tracing: disabled;
- evidence source: controlled test fixtures;
- repository writes during live model calls: none.

### Initial English semantic test

A directly supported observed fact stated:

`Revenue increased during the reporting period.`

The live Reviewer returned:
- status: `PASS`;
- approved claim: `C1`;
- rejected claims: none;
- `publication_allowed=true`.

A mixed draft then contained:
- `C1`: `Revenue increased during the reporting period.`;
- `C2`: `Revenue doubled during the reporting period.`

The supplied evidence supported only an increase and supplied no magnitude.

The Reviewer semantically classified the mixed draft correctly:
- approved `C1`;
- rejected `C2`;
- selected `PARTIAL`.

However, the first live mixed-case response returned
`publication_allowed=false`.

The structured `ClaimReviewResult` contract rejected that response because
the archived workflow contract requires:
- `PASS -> publication_allowed=true`;
- `PARTIAL -> publication_allowed=true`;
- `FAIL -> publication_allowed=false`.

### Raw diagnostic

A read-only `include_raw=True` diagnostic confirmed that the model had
correctly understood the evidence problem.

The raw tool-call arguments contained:
- status: `PARTIAL`;
- approved claims: `["C1"]`;
- rejected claims: `["C2"]`;
- `publication_allowed=false`.

The model's reasons explicitly stated that the evidence supported only an
increase and did not support the claim that revenue doubled.

Therefore the failure was not attributed to inability to perform semantic
evidence review. It was attributed to ambiguity in the meaning of the
`publication_allowed` field: the model interpreted it as permission to
publish the original draft as written rather than as a workflow-routing flag.

The Pydantic contract was not weakened.

### Repair and English live regression

The Reviewer system prompt was clarified so that
`publication_allowed` is explicitly defined as a workflow-routing flag.

For `PARTIAL`, `publication_allowed=true` means that the workflow may emit a
`PartialResearchResult` preserving the original draft, complete claim
classification, and review reasons. It does not mean that rejected claims or
the original draft may be silently published as approved.

After this clarification, the same English mixed case returned:
- status: `PARTIAL`;
- approved claims: `["C1"]`;
- rejected claims: `["C2"]`;
- `publication_allowed=true`.

The live regression therefore satisfied both the semantic review requirement
and the publication-routing contract.

### Chinese financial-report semantic verification

A separate live Chinese test used filing-style evidence:

`报告期内，公司营业收入同比增长12.5%。`

For a clean draft containing the same observed fact, the Reviewer returned:
- status: `PASS`;
- approved claim: `C-CN-1`;
- rejected claims: none;
- `publication_allowed=true`.

A mixed Chinese draft additionally claimed:

`报告期内，公司营业收入同比增长125%。`

The Reviewer returned:
- status: `PARTIAL`;
- approved claim: `C-CN-1`;
- rejected claim: `C-CN-2`;
- `publication_allowed=true`.

The Reviewer explicitly recognized that the supplied evidence stated 12.5%
rather than 125% and rejected the stronger quantitative claim as unsupported
and overstated.

This verifies that the live Reviewer can perform claim-level semantic review
against Chinese financial-report evidence for this controlled case.

### Scope of verification

This verification establishes:
- live Claim Reviewer structured execution for supported claims;
- live semantic rejection of unsupported quantitative overreach;
- correct `PARTIAL` publication routing after prompt clarification;
- controlled English semantic-gate behavior;
- controlled Chinese financial-report semantic-gate behavior.

It does not establish:
- broad Chinese-language research quality across real issuers and filings;
- calibrated Reviewer accuracy across diverse claim types;
- production retry or failure-recovery policy;
- real Financial Evidence Service / Retrieval Lab integration;
- complete live Analyst -> Reviewer -> publication workflow behavior;
- Quant Desk integration.

Reviewer `reasons` in the Chinese test were primarily English. Output-language
policy is not part of this verification and remains a separate contract
decision.

## 2026-10-07 — Controlled Chinese live end-to-end PASS route

Status: VERIFIED for one controlled live end-to-end PASS route.

The run used the actual compiled LangGraph workflow with:
- a controlled in-memory ScopeResolver;
- a controlled in-memory EvidenceProvider;
- Chinese financial-report-style evidence;
- the real `FundamentalAnalystEngine`;
- the real `ClaimReviewerEngine`;
- `DeepSeekStructuredResearchModel` backed by `deepseek-chat`;
- LangSmith tracing disabled.

No production Retrieval Lab / RAG component was connected.

The controlled evidence stated:

`报告期内，公司营业收入同比增长12.5%。`

The graph executed:

`validate_request -> resolve_scope -> collect_evidence ->
fundamental_analyst -> claim_review -> publish`

Observed Analyst draft:
- `C1` — `OBSERVED_FACT`, directly referencing `E-CN-1`;
- `C2` — `ANALYST_INFERENCE`, no direct evidence reference, supported by `C1`,
  with explicit assumptions;
- `C3` — `FORWARD_VIEW`, no direct evidence reference, supported by prior
  Analyst claims, with explicit assumptions;
- fundamental outlook: `UNDETERMINED`;
- confidence: `LOW`.

Observed Reviewer result:
- status: `PASS`;
- approved claims: `C1`, `C2`, `C3`;
- rejected claims: none;
- `publication_allowed=true`.

Observed graph terminal result:
- `ResearchRunStatus.PUBLISHED`;
- terminal artifact: `final_output`;
- final output review status: `PASS`.

Run identity remained consistent across the workflow request, EvidencePacket,
FundamentalResearchDraft, ClaimReviewResult, and final publication artifact.

The run remained read-only with respect to repository state.

This verifies that a controlled Chinese evidence packet can pass through the
real live Analyst and Reviewer inside the actual LangGraph workflow and reach
the correct PASS publication artifact while preserving the strict-v0 claim
chain and run identity.

A Reviewer `PASS` is a publication-quality judgment, not an investment stance.
In this verified run the research outlook remained `UNDETERMINED` and
confidence remained `LOW`.

Scope limitation:
- the live end-to-end PASS route is verified;
- live end-to-end PARTIAL and FAIL routes have not yet been exercised with
  real model calls;
- deterministic graph unit tests cover PASS, PARTIAL, and FAIL routing;
- no real Financial Evidence Service / Retrieval Lab runtime was used;
- no persistent ResearchRun storage was used;
- no Quant Desk integration was used.
