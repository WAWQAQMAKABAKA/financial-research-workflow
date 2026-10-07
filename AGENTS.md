# financial-research-workflow agent instructions

This repository is an independent Financial Research Workflow.

## Authority split

Jason owns:
- research/business meaning
- analyst mandate
- evidence semantics
- research stance semantics
- permission boundaries
- final adoption of research conclusions

Mich owns:
- engineering execution
- tests
- files
- packaging
- wiring
- provenance
- already-defined contracts

Do not ask Mich to infer investment meaning.

## Product boundary

This repository owns research workflow state and research outputs.

It must not:
- import Quant Desk production internals
- read Quant Desk cards/rulings/trades as an implicit data API
- write any Quant Desk production decision-chain input
- duplicate the Retrieval Lab RAG while B1 remains open
- import benchmark GT into runtime
- convert research views into trading actions

## v0

Build only:
- ResearchRequest
- EvidencePacket
- FundamentalResearchOutput
- Evidence Service interface
- Fundamental Analyst
- Claim Review
- independent state/tests/UI

Do not add:
- extra analysts
- Bull/Bear debate
- Research Manager
- autonomous planner
- HTTP service
- Quant Desk adapter
- valuation or market-structure logic
unless Jason explicitly expands scope.

## Evidence rule

Evidence answers what sources support.

Analysts interpret evidence.

Jason decides action.

Evidence sufficiency, conflict, technical failure, and analyst claim support are
separate states.

## Test boundary

Pure research runs do not run Quant Desk tests.

Internal changes run this repository's component/workflow/contract tests.

Quant Desk full gates are relevant only after a future explicit integration
boundary is changed.

## Retrieval Lab

The Retrieval Lab remains the experiment/benchmark/evaluation environment.

Do not move or copy its implementation wholesale.

Promote only stable product capability after runtime selection and explicit
verification.

## Engineering protocol

Before writes:
- confirm branch / HEAD when available
- inspect git status
- pull --ff-only when a remote exists
- re-read current project docs relevant to the change

If actual output differs from expectation:
- stop
- preserve evidence
- do not fix while here
- diagnose before continuing

Use independently verifiable checkpoints.

A change is not complete merely because code exists.


## Orchestration and observability

LangGraph is the product orchestration layer.

Keep the graph bounded and explicit. Do not add autonomous planners, unlimited
loops, or new analyst roles without Jason's scope decision.

LangGraph Studio is for engineering visualization/debugging, not the product UI.

LangSmith is optional observability/evaluation infrastructure. The workflow must
remain runnable without LangSmith.

ResearchRun artifacts owned by this repository are authoritative. External
traces are diagnostic copies only.

Do not enable tracing of raw documents, private research material, portfolio
context, credentials, or proprietary payloads without an explicit data policy.
