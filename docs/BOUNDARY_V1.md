# Financial Research Workflow Boundary v1

Status: Jason-confirmed business boundary; engineering implementation begins from
this repository.

## Mission

Financial Research Workflow is an independent AI research system operating
before trading action is decided.

It may form conditional, traceable, falsifiable research views.

It has no trading decision authority.

## Responsibility boundary

### Financial Evidence Service

Owns:
- authorized research scope
- PIT enforcement
- retrieval
- evidence sufficiency
- bounded repair
- citations and canonical source locations
- limitations and conflicts
- deterministic calculations
- provenance and run identity

Does not own:
- investment stance
- analyst interpretation
- portfolio decisions
- trading actions

### Financial Research Workflow

Owns:
- research requests and questions
- research state
- analyst output
- claim/evidence chains
- assumptions
- disconfirming conditions
- research stance
- review result
- run provenance

Does not own Quant Desk production state.

### Quant Desk

Remains the deterministic execution system for Jason-approved trading
discipline.

Research views must never automatically become trading state.

## Fundamental Analyst v0

The first analyst is position-blind and studies company fundamentals.

It may cover:
- revenue/profit/margins/expenses/cash flow
- business/product/geographic contribution
- company-disclosed operating drivers
- product/pipeline/commercialization progress
- management guidance
- balance sheet and liquidity
- earnings quality
- major fundamental risks
- assumptions and disconfirming conditions
- outlook for explicitly resolved future reporting periods

It does not cover:
- security buy/sell views
- valuation or target price
- market structure
- positions/cost/P&L
- full industry/peer research
- real-time news monitoring

Allowed fundamental outlook states:

- IMPROVING
- STABLE
- DETERIORATING
- MIXED
- UNDETERMINED

MIXED and UNDETERMINED are distinct.

## Request boundary

One request contains 1–5 tightly related questions sharing:
- company
- as_of
- research scope
- baseline report period

The analyst may decompose questions but may not autonomously launch new research.

Follow-up questions may be suggested but are not automatically executed.

Authorized corpus is resolved by trusted configuration, not trusted caller input.

Benchmark GT, expected outcomes and protected evaluation answers are forbidden
runtime inputs.

## Evidence semantics

Evidence relationships bind to concrete claims.

Relationship:
- SUPPORTS
- CONTRADICTS
- CONTEXT_ONLY

Coverage is separate from relationship.

Per-question evidence state separately records:

Availability:
- AVAILABLE
- PARTIAL
- UNAVAILABLE

Answer sufficiency:
- SUFFICIENT
- PARTIALLY_SUFFICIENT
- INSUFFICIENT

Conflicts are stored separately.

Technical failures are not evidence insufficiency.

Original relevant spans, qualifiers, page/canonical locations, PIT timing,
searched scope and provenance remain available to the analyst.

## Claim chain

Substantive conclusions follow:

Evidence
-> Observed fact / management explanation
-> Analyst inference
-> Explicit assumptions
-> Forward view

Claim types:
- OBSERVED_FACT
- MANAGEMENT_EXPLANATION
- ANALYST_INFERENCE
- FORWARD_VIEW

Facts link to evidence.

Inferences and forward views link to supporting claims and assumptions.

Drivers, risks, outlook and executive summary may not introduce orphan
conclusions.

## Claim Review

Publication results:

PASS
- approved claims may be shown as formal research.

PARTIAL
- valid claims remain;
- weak/unsupported claims are identified;
- the overall result is marked partially complete.

FAIL
- a critical conclusion fails evidence or scope review;
- the run is preserved;
- it is not published as a completed research view.

v0 does not require autonomous rewrite loops.

## Test boundary

Pure research execution does not trigger Quant Desk tests.

Internal workflow changes use this repository's own tests.

Cross-system validation is required only when a future explicit integration
contract is modified.

## Retrieval Lab boundary

Retrieval Lab remains the B1/benchmark/evaluation laboratory.

This repository must not build a second production retrieval implementation
before B1 closure.

After runtime selection, stable capabilities may be naturalized into the
Financial Evidence Service.

Benchmark GT, evaluator-only code and protected evaluation artifacts remain
outside production runtime.
