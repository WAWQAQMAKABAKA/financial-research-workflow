"""Isolated P2/FRW LangGraph interface tests.

All observations and evidence text are synthetic.
No real P1/P2, PIT, Analyst or Reviewer validation is performed.
"""
from financial_research.contracts import (
    AnswerSufficiency,
    EvidenceAvailability,
    EvidenceRelationship,
    ReviewStatus,
)
from financial_research.workflow.graph import build_research_graph
from financial_research.workflow.interfaces import WorkflowServices

from tests.test_p2_boundary_experiment import (
    P2Observation,
    P2TestAdapter,
    make_inputs,
)
from tests.test_workflow_graph import (
    FakeFundamentalAnalyst,
    FakeClaimReviewer,
)


class RecordingScopeResolver:
    def __init__(self, scope, log):
        self.scope = scope
        self.log = log

    def resolve(self, request, research_run_id):
        self.log.append("resolve_scope")
        return self.scope


class RecordingProvider:
    def __init__(self, delegate, log):
        self.delegate = delegate
        self.log = log

    def collect(self, request, execution_scope, research_run_id):
        self.log.append("collect_evidence")
        return self.delegate.collect(
            request, execution_scope, research_run_id
        )


class RecordingAnalyst:
    def __init__(self, delegate):
        self.delegate = delegate
        self.received_packets = None

    def analyze(self, request, evidence_packets, research_run_id):
        self.received_packets = evidence_packets
        return self.delegate.analyze(
            request, evidence_packets, research_run_id
        )


class RecordingReviewer:
    def __init__(self, delegate):
        self.delegate = delegate
        self.received_packets = None

    def review(self, draft, evidence_packets, research_run_id):
        self.received_packets = evidence_packets
        return self.delegate.review(
            draft, evidence_packets, research_run_id
        )


def execute_test_case(observation, assessment):
    request, scope = make_inputs(observation.document_id)
    log = []
    run_id = "RUN1"

    adapter = P2TestAdapter(observation, assessment)

    analyst = RecordingAnalyst(
        FakeFundamentalAnalyst(log, draft_run_id=run_id)
    )
    reviewer = RecordingReviewer(
        FakeClaimReviewer(
            log,
            status=ReviewStatus.FAIL,
            review_run_id=run_id,
        )
    )

    services = WorkflowServices(
        scope_resolver=RecordingScopeResolver(scope, log),
        evidence_provider=RecordingProvider(adapter, log),
        fundamental_analyst=analyst,
        claim_reviewer=reviewer,
    )

    graph = build_research_graph(services)

    result = graph.invoke({
        "research_run_id": run_id,
        "request": request,
    })

    assert log == [
        "resolve_scope",
        "collect_evidence",
        "fundamental_analyst",
        "claim_review",
    ]

    assert len(result["evidence_packets"]) == 1
    packet = result["evidence_packets"][0]

    assert packet.research_run_id == run_id
    assert packet.question_id == "Q1"
    assert analyst.received_packets == [packet]
    assert reviewer.received_packets == [packet]

    # Reviewer FAIL is independently injected by this test.
    # It is not a conclusion inferred from the P2 status.
    assert "final_output" not in result

    return packet, adapter


def test_shenfei_p2_context_reaches_actual_graph():
    observation = P2Observation(
        document_id="600760-2026H1-cninfo-1225517994",
        chunk_index=215,
        status="EXPANDED_VERIFIED",
        context_text="SYNTHETIC_TABLE_CONTEXT_NOT_SOURCE_TEXT",
    )

    packet, adapter = execute_test_case(
        observation,
        (
            EvidenceAvailability.PARTIAL,
            AnswerSufficiency.INSUFFICIENT,
        ),
    )

    assert len(packet.evidence_items) == 1
    item = packet.evidence_items[0]

    assert item.relationship == EvidenceRelationship.CONTEXT_ONLY
    assert item.provenance["p2_status"] == "EXPANDED_VERIFIED"
    assert packet.question_state.sufficiency == (
        AnswerSufficiency.INSUFFICIENT
    )
    assert adapter.diagnostics[0]["chunk_index"] == 215


def test_hengrui_p2_unavailable_reaches_actual_graph():
    observation = P2Observation(
        document_id="600276-2026H1-cninfo-1225483600",
        chunk_index=234,
        status="UNAVAILABLE",
        context_text=None,
    )

    packet, adapter = execute_test_case(
        observation,
        (
            EvidenceAvailability.UNAVAILABLE,
            AnswerSufficiency.INSUFFICIENT,
        ),
    )

    assert packet.evidence_items == []
    assert packet.question_state.availability == (
        EvidenceAvailability.UNAVAILABLE
    )
    assert packet.question_state.sufficiency == (
        AnswerSufficiency.INSUFFICIENT
    )

    # The P2 diagnostic remains outside the EvidencePacket.
    # This unresolved delivery boundary is intentional.
    assert adapter.diagnostics[0]["p2_status"] == "UNAVAILABLE"
    assert "p2_status" not in packet.model_dump()
