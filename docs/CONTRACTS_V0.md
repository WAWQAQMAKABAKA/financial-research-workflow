# Financial Research Workflow Contracts v0

Status: Jason-confirmed business specification.

These contracts define the v0 boundary between the caller, Financial Evidence
Service, Fundamental Analyst, and Claim Review.

They do not define Quant Desk integration.

---

## 1. ResearchRequest v0

A request contains 1–5 tightly related questions sharing:

- the same company;
- the same `as_of`;
- the same research scope;
- the same baseline report period.

Minimum logical fields:

    ResearchRequest
    - company
    - ticker
    - as_of
    - report_period
    - research_questions[1..5]
    - research_scope = FUNDAMENTAL
    - horizon
    - requested_output = FUNDAMENTAL_RESEARCH

### as_of

`as_of` is the timezone-aware research information cutoff.

Information published after this instant is excluded from the run.

### report_period

`report_period` is the baseline reporting period.

It does not restrict the Evidence Service to reading only that report.

### horizon

The business default is the next 1–2 reporting periods.

Every run must resolve this into explicit target reporting periods relative to
the selected baseline period.

### research questions

The Fundamental Analyst may decompose the original questions for analysis.

It may not autonomously launch additional research.

Possible new questions may be returned only as:

    suggested_followup_questions[]

They are not automatically executed in v0.

---

## 2. Trusted execution scope

Authorized corpus is not trusted caller input.

The system resolves from trusted configuration:

- authorized corpus;
- document scope;
- corpus/index version;
- source permissions.

The actual resolved scope and version are persisted in the run record.

Runtime must not accept or use:

- benchmark expected answers;
- GT;
- GT spans or routes;
- evaluator-only answer requirements;
- protected validation/final answers;
- benchmark case identity as a shortcut;
- desired trading action;
- portfolio state for the Fundamental Analyst.

---

## 3. Position blindness

Position blindness applies to both structured and natural-language inputs.

The Fundamental Analyst must not receive:

- current position;
- average cost;
- unrealized P&L;
- statements such as “I am heavily invested” when they are merely portfolio context;
- prior desired trade outcome.

If portfolio information is embedded in natural-language input:

1. remove or redact it before analyst execution when the underlying research
   question remains intact; or
2. require reformulation when removal would materially change the research
   question.

The transformation is recorded in run metadata.

The original request remains preserved for audit.

A future Portfolio Impact layer may consume a frozen research conclusion plus
portfolio context, but may not rewrite the underlying fundamental research.

---

## 4. EvidencePacket v0

EvidencePacket provides source-grounded evidence.

It is not an investment opinion and must not reduce the source record to only a
model-written summary.

### Claim binding

Evidence relationships bind to a concrete proposition.

A research question itself is not necessarily a supportable proposition.

Example question:

    Did product X improve profitability?

Example target proposition:

    Product X contributed identifiable incremental profit in the baseline period.

Every evidence relationship therefore binds to a stable `claim_id` and/or an
explicit target proposition.

### Evidence item

Minimum logical form:

    EvidenceItem
    - evidence_id
    - claim_id
    - source_id
    - document_id
    - source_type
    - published_at
    - pit_available_at
    - page
    - canonical_location
    - relevant_span
    - qualifiers
    - relationship
    - provenance

Original relevant text, qualifiers and canonical location remain available to
the analyst.

---

## 5. Evidence relationship and coverage

Relationship and coverage are separate dimensions.

Allowed relationship values:

    SUPPORTS
    CONTRADICTS
    CONTEXT_ONLY

`PARTIAL` is not a relationship type.

Coverage records separately:

- which parts of a proposition are supported;
- which parts remain unsupported;
- which required dimensions remain missing.

---

## 6. Question-level evidence state

Each research question independently records:

### Availability

    AVAILABLE
    PARTIAL
    UNAVAILABLE

### Answer sufficiency

    SUFFICIENT
    PARTIALLY_SUFFICIENT
    INSUFFICIENT

### Conflicts

Conflicts are stored in:

    conflicts[]

Each conflict records:

- the conflicting proposition or interpretation;
- relevant evidence;
- whether the conflict is resolved;
- when resolved, the basis for resolution.

Evidence may be sufficient to establish that a conflict exists while remaining
insufficient to determine which competing interpretation is correct.

---

## 7. Technical state

Technical/runtime failures are separate from evidence states.

Examples:

- retrieval failure;
- parser failure;
- unavailable index;
- model/API failure;
- corrupted document.

A technical failure must never be represented as:

- insufficient evidence;
- neutral outlook;
- undetermined fundamental outlook.

A failure on one question must not erase valid results for the other questions
in the same request.

---

## 8. Source-validation terminology

v0 distinguishes:

### GROUNDED

A claim has explicit source support.

### DISCLOSURE_CONSISTENT

Multiple disclosures express consistent information, but they may derive from
the same original source.

### INDEPENDENTLY_CORROBORATED

Genuinely independent sources support the same material claim.

v0 guarantees only grounded evidence and authorized-disclosure consistency
checking unless independent-source provenance has actually been established.

---

## 9. Fundamental research lifecycle

The Fundamental Analyst produces a pre-review artifact:

    FundamentalResearchDraft

The analyst does not assign its own review result.

The lifecycle is:

    FundamentalResearchDraft
      ->
    ClaimReviewResult
      ->
    FundamentalResearchOutput

`FundamentalResearchOutput` is the reviewed/final publication-facing research
artifact.

Claim Review remains an independent publication gate.

A draft must not contain `review_status`.

The final output contains the accepted research body plus the resulting
`review_status`.

The executive summary is also subject to the publication gate. It must not be
treated as automatically publishable merely because the analyst produced it.

## 9A. FundamentalResearchDraft v0

Every substantive conclusion participates in one traceable claim chain.

Minimum logical form:

    FundamentalResearchDraft
    - research_scope
    - company
    - ticker
    - as_of
    - report_period
    - resolved_horizon
    - executive_summary
    - claims[]
    - drivers[]
    - risks[]
    - fundamental_outlook
    - key_assumptions[]
    - disconfirming_conditions[]
    - evidence_gaps[]
    - source_conflicts[]
    - limitations[]
    - suggested_followup_questions[]
    - confidence
    - provenance
    - research_run_id

## 9B. FundamentalResearchOutput v0

The final output contains the reviewed research body and additionally:

    - review_status

It is created only after Claim Review.

## 10. Claim types

Allowed claim types:

    OBSERVED_FACT
    MANAGEMENT_EXPLANATION
    ANALYST_INFERENCE
    FORWARD_VIEW

The intended direction is:

    Evidence
      ->
    Observed fact / management explanation
      ->
    Analyst inference
      ->
    Explicit assumptions
      ->
    Forward view

Historical facts do not automatically establish a forward view.

Every substantive claim receives a stable `claim_id`.

Facts and management explanations link directly to `evidence_refs`.

Analyst inferences and forward views link to:

- supporting `claim_ids`;
- explicit assumptions;
- disconfirming conditions when relevant.

---

## 11. No orphan conclusions

`drivers`, `risks`, and `fundamental_outlook` must reference checked claims.

They must not introduce new substantive conclusions.

`executive_summary` may only summarize content admitted by Claim Review.

---

## 12. Fundamental outlook

Allowed values:

    IMPROVING
    STABLE
    DETERIORATING
    MIXED
    UNDETERMINED

`MIXED` means evidence is sufficient but material operating dimensions point in
different directions.

`UNDETERMINED` means available evidence is insufficient to form a justified
overall fundamental view.

The two states are not interchangeable.

---

## 13. Confidence

Allowed values:

    HIGH
    MEDIUM
    LOW
    UNDETERMINED

Confidence means confidence in the evidence support for that analytical
judgment.

It is not a probability that a future event will occur.

Until explicit calibration rules exist, confidence:

- is descriptive only;
- must not rank opportunities;
- must not trigger automated decisions.

---

## 14. Claim Review

Claim Review checks whether:

    evidence
      -> fact / management explanation
      -> inference
      -> assumptions
      -> forward view

is supported and remains within Fundamental Analyst scope.

The reviewer does not need to rewrite the report.

### PASS

- approved claims may be published as formal research output.

### PARTIAL

- supported claims remain;
- weak or unsupported claims are explicitly identified;
- the result is marked partially complete.

### FAIL

- a critical conclusion fails evidence or scope review;
- the actual run remains preserved;
- failure reason is visible;
- the result is not published as a completed research view.

v0 does not require autonomous iterative rewriting.

---

## 15. Persisted run record

Persist the observable execution record:

- original request;
- sanitized/execution request when different;
- resolved corpus/document scope;
- `as_of`;
- evidence packet(s);
- model output;
- claim links;
- assumptions;
- review result;
- calculation inputs/outputs;
- technical diagnostics;
- runtime/model/config identity;
- provenance and run ID.

Do not request or persist model hidden chain-of-thought.

---

## 16. Minimum v0 acceptance cases

### A — Sufficient evidence

The workflow forms a justified fundamental view with traceable material claims.

### B — Insufficient evidence

The workflow identifies missing evidence and uses `UNDETERMINED` or a properly
bounded partial conclusion rather than inventing completeness.

### C — Conflicting evidence

The workflow preserves the conflict and distinguishes:

- evidence that conflict exists;
- evidence sufficient to decide which interpretation is correct.

### D — Boundary pressure

A request asks for:

- a trade action;
- security-level bullish/bearish view;
- position-aware interpretation;
- another out-of-scope task.

The Fundamental Analyst preserves its scope and does not convert the request
into trading advice.

Additional requirements:

- information after `as_of` is excluded;
- technical failures remain distinct from evidence insufficiency;
- one failed question does not erase successful questions;
- the research run can complete without Quant Desk production state;
- no Quant Desk decision-chain input is written;
- results remain recoverable through run/provenance identity.
