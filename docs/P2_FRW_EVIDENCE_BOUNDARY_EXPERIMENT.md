# P2 / Financial Research Workflow Evidence Boundary Experiment

Status: VERIFIED DEVELOPMENT EXPERIMENT — NOT PRODUCTION ACCEPTANCE

## 1. Scope and architecture

The Financial Research Workflow (FRW) is an independent
research application with its own LangGraph orchestration.

The existing workflow is:

Validate Request
→ Resolve Scope
→ Collect Evidence
→ Fundamental Analyst
→ Claim Review
→ Publish / Publish Partial / Preserve Failure

The workflow uses the EvidenceProvider Protocol to
receive EvidencePacket objects.

Retrieval Lab remains an independent development and
evaluation laboratory. Its experimental RAG Graph is
not the FRW product graph.

No production retrieval implementation should be
duplicated inside FRW.

## 2. Verified research baselines

FRW baseline:
6ade7948b3dd7faa4500c957cc20600f821e2c90

Retrieval Lab P2 code baseline:
aac3811897ddb713f1295c9190e73c9ae68022f7

Retrieval Lab real-report findings:
dadd16e646cddd654be6fa0e024a9189e36bbd7f

Relevant P2 semantic ruling:
quant-desk ruling seq 567

The source laboratory baseline and diagnostic findings
were already committed separately.

## 3. Jason-approved EvidencePacket consistency rule

When an EvidencePacket has no evidence_items and its
QuestionEvidenceState.technical_state.status is OK,
question-level EvidenceAvailability must not be
AVAILABLE or PARTIAL.

Such a packet must not claim available evidence
without traceable EvidenceItem records.

This is a packet-consistency condition, not an
automatic evidence-sufficiency conclusion.

The implemented rule is scoped specifically to the
empty-evidence / technical-OK combination.

Technical failures and evidence insufficiency
remain separate states.

No additional rule for technical-FAILED packets
was decided or implemented by this experiment.

## 4. Distinct evidence semantics

P1:
Authorizes retrieval of in-scope documents and
returns candidate source context.

P2:
Verifies structural association with a source table
and, when possible, exact same-table context.

P2 statuses:
- ALREADY_COMPLETE
- EXPANDED_VERIFIED
- UNAVAILABLE

FRW question availability:
- AVAILABLE
- PARTIAL
- UNAVAILABLE

FRW answer sufficiency:
- SUFFICIENT
- PARTIALLY_SUFFICIENT
- INSUFFICIENT

These classifications operate at different levels.

EXPANDED_VERIFIED does not imply SUFFICIENT.

P2 UNAVAILABLE does not prove that the research
question has no available evidence.

EvidenceRelationship.SUPPORTS requires independent
proposition-specific support assessment.

EvidenceItem.target_claim_id refers to the evidence
target proposition, not necessarily the Analyst's
FundamentalClaim.claim_id.

## 5. E2 test-only adapter

The experiment created:
tests/test_p2_boundary_experiment.py

It used two archived development case identifiers
with synthetic evidence payloads and dates.

Shenfei 600760 2026H1, chunk 215:
P2 observation EXPANDED_VERIFIED.

The synthetic context was carried as a CONTEXT_ONLY
EvidenceItem with test-only provenance.

Hengrui 600276 2026H1, chunk 234:
P2 observation UNAVAILABLE.

No EvidenceItem was manufactured for the failed
table association.

Question-level availability and sufficiency were
supplied independently as test assessments.

They were not inferred from the P2 statuses.

E2 was not a live P1/P2 execution or a real
source/PIT validation.

## 6. E3-A contract verification

The empty-evidence consistency rule was implemented
in financial_research/contracts/models.py.

The test-only adapter was updated to avoid claiming
PARTIAL availability with an empty evidence list.

Two negative parametrized cases verify that empty
technical-OK packets cannot claim AVAILABLE or PARTIAL.

Focused test result: 4 passed.

Full FRW test result at E3-A: 60 passed.

The original E3-A final Git-status comparison initially
failed because a diagnostic helper stripped the leading
space from Git porcelain output. A separate read-only
verification confirmed that file hashes, HEAD, staging
and protected sources matched expectations.

No code or test failure was established by that
Git-status display error.

## 7. E3-B actual LangGraph boundary experiment

The experiment created:
tests/test_p2_graph_boundary_experiment.py

Both synthetic scenarios traversed the real FRW graph:

Resolve Scope
→ Collect Evidence
→ Fundamental Analyst
→ Claim Review

Both the fake Analyst and fake Reviewer received the
expected EvidencePacket.

The Reviewer FAIL result was deliberately injected
by the test. It was not an AI evidence judgment.

Shenfei:
The synthetic CONTEXT_ONLY item and its P2 status
reached the downstream components.

Hengrui:
The empty EvidencePacket reached the downstream
components, with an independent question assessment.

The P2 UNAVAILABLE diagnostic remained in the
test adapter's separate diagnostics, not in the
EvidencePacket delivered downstream.

Focused Graph tests: 2 passed.

Full FRW suite after E3-B: 62 passed.

These results establish interface and Graph routing
behavior under synthetic conditions.

## 8. Unresolved evidence delivery boundary

The formal EvidencePacket does not currently carry
the P2 table-recovery status directly when no
EvidenceItem was created.

Therefore, a downstream Analyst cannot distinguish
P2 table-format limitations from other evidence
unavailability causes using only the packet.

This is an unresolved delivery/interface question,
not authorization to equate P2 UNAVAILABLE with
question-level EvidenceAvailability.UNAVAILABLE.

Any future mapping must preserve provenance,
technical failures, source validation, PIT availability,
question availability and answer sufficiency as
distinct responsibilities.

## 9. Explicit limitations

Not demonstrated:

- Production Financial Evidence Service implementation
- Real FRW EvidenceProvider using authorized P1/P2
- Live canonical-source verification
- Real financial-report point-in-time validation
- Actual Fundamental Analyst answer quality
- Real Claim Reviewer correctness
- Independent GT, OOS or holdout performance
- Trading decisions or production delivery

The E2/E3 work is a bounded development experiment,
not a production service acceptance test.

## 10. Next stage

First review how the P2 diagnostic can be delivered
through a stable evidence-service interface without
changing its meaning or inventing evidence.

Then design a bounded source-backed integration
experiment using the existing FRW LangGraph.

Do not copy the experimental Retrieval Lab Graph,
silently expand the scope, or claim that a synthetic
test represents real evidence availability.
