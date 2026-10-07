# Financial Research Workflow

Independent AI research workflow for financial research before trading decisions.

## Mission

This system may produce evidence-grounded research findings, analyst interpretation,
conditional research views, disagreements, limitations, and follow-up questions.

It does not own trading decisions or Quant Desk production state.

Responsibility boundary:

1. Evidence — what authorized sources support.
2. Research — how analysts interpret supported evidence.
3. Action — Jason decides whether trading discipline changes.

## v0 scope

v0 contains:

- Financial Evidence Service contract
- Fundamental Analyst
- Claim Review
- Research state
- Independent tests
- Research UI

v0 excludes:

- Quant Desk production data
- positions, cost, P&L
- valuation
- price structure
- Bull/Bear debate
- Research Manager
- HTTP service
- long-term memory
- autonomous planning
- production RAG duplication

## Retrieval Lab relationship

The existing quant-desk Retrieval Lab remains the RAG/B1 laboratory.

Until B1 closure and runtime selection, this repository must not create a second
retrieval engine. It may define and test an Evidence Service interface using
fixtures or fake providers.

Stable retrieval capability may later be naturalized here through explicit
contracts. Benchmark GT, evaluator artifacts, validation fixtures, and
protected-final material remain outside production runtime.

## Quant Desk relationship

This repository must not import Quant Desk internals or read/write its working
directory as an implicit API.

Future integration must use explicit read-only contracts.

Research output never automatically changes trading state.


## Orchestration and observability

- LangGraph is the bounded research-workflow orchestration runtime.
- LangGraph Studio is a developer visualization/debugging surface.
- LangSmith is a future optional tracing/evaluation layer.
- The repository's own ResearchRun artifacts remain authoritative.
- Tracing must never become a runtime dependency or silently expand the
  research-data boundary.

See `docs/ORCHESTRATION_OBSERVABILITY.md`.
