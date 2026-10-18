# Financial Evidence Service Adapter — S6

Status: VERIFIED DEVELOPMENT BOUNDARY
Production acceptance: NOT ACHIEVED

## Purpose

FRW-S6 introduces a small EvidenceProvider implementation
that delegates packet acquisition to an injected
FinancialEvidenceServiceClient.

It does not create an Evidence Service, implement
retrieval, or modify the existing LangGraph.

Source baseline:
FRW main 8bc2932388494407826baedf47e44de33ed05f3d

Retrieval Lab reference:
lab/retrieval-v1 dadd16e646cddd654be6fa0e024a9189e36bbd7f

## Files

Adapter:
financial_research/workflow/evidence_service_adapter.py

Tests:
tests/test_evidence_service_adapter.py

The existing WorkflowServices.evidence_provider injection
point remains unchanged.

## Verified boundary behavior

The adapter accepts a typed ResearchRequest,
ResolvedExecutionScope and research_run_id.

It delegates to FinancialEvidenceServiceClient.fetch_packets.

It revalidates returned EvidencePacket objects.

It checks:
- Research run identity
- Exact research as_of
- Execution scope equality
- Requested question membership
- Duplicate question packets
- One packet per requested question
- Evidence document IDs when document_scope is nonempty
- Existing EvidencePacket model invariants

Explicit question-level UNAVAILABLE packets can pass.

Backend errors are propagated rather than silently
converted into evidence insufficiency.

S6B verification:
13 focused tests passed.
87 total FRW tests passed.

## Explicit authorization limitation

The adapter checks document membership only when
execution_scope.document_scope is nonempty.

When document_scope is empty, the adapter currently
performs no document-level allowlist enforcement.

The authorized meaning of an empty document_scope
has not been ruled or implemented.

Do not interpret an empty document_scope as universal
document access without an explicit authorization
contract and additional tests.

This limitation must be resolved before production
Evidence Service acceptance.

## Responsibilities not implemented

The adapter does not independently perform:
- Authorized source retrieval
- Canonical PDF and source verification
- Automatic table boundary identification
- Runtime PIT admission and acquisition enforcement
- Historical source revision verification
- Independent question evidence sufficiency adjudication
- Source-backed execution through LangGraph
- Production research delivery

No real Financial Evidence Service client was used
in the S6B tests.

S6B exercised an injected fake client only.

Previous S5 real-report source validation was an
independent bounded development experiment.

## Next engineering stage

Specify and implement one real Evidence Service
delivery slice. Resolve empty document_scope
authorization semantics before activating the adapter.

Maintain distinct states for:
- Technical failure
- Source or table evidence unavailable
- Valid contextual evidence
- Proposition-level support
- Question-level sufficiency

Do not equate P2 EXPANDED_VERIFIED with SUFFICIENT.
Do not duplicate Retrieval Lab's experiment graph.
Do not treat a successful transport test as
production evidence certification.
