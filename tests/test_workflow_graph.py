from datetime import datetime, timezone

import pytest

from financial_research.contracts import (
    AnswerSufficiency,
    ClaimReviewResult,
    ClaimType,
    Confidence,
    EvidenceAvailability,
    EvidenceItem,
    EvidencePacket,
    EvidenceRelationship,
    FundamentalClaim,
    FundamentalOutlook,
    FundamentalOutlookAssessment,
    FundamentalResearchDraft,
    QuestionEvidenceState,
    ResearchQuestion,
    ResearchRequest,
    ResolvedExecutionScope,
    ReviewStatus,
)
from financial_research.state import ResearchRunStatus
from financial_research.workflow import WorkflowServices, build_research_graph


AS_OF = datetime(2026, 8, 31, 23, 59, tzinfo=timezone.utc)
EARLIER = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)


def make_request() -> ResearchRequest:
    return ResearchRequest(
        company="Example Co",
        ticker="600000",
        as_of=AS_OF,
        report_period="2026H1",
        research_questions=[
            ResearchQuestion(
                question_id="Q1",
                text="How did revenue change?",
            )
        ],
    )


def make_scope() -> ResolvedExecutionScope:
    return ResolvedExecutionScope(
        authorized_corpus="issuer_disclosures",
        document_scope=["2026H1"],
        corpus_version="v1",
        source_permissions=["public_disclosure"],
        resolved_at=AS_OF,
    )


def make_packet(run_id: str = "RUN1") -> EvidencePacket:
    item = EvidenceItem(
        evidence_id="E1",
        target_claim_id="C1",
        target_proposition="Evidence target proposition.",
        source_id="SRC1",
        document_id="DOC1",
        source_type="filing",
        published_at=EARLIER,
        pit_available_at=EARLIER,
        canonical_location="page:10",
        relevant_span="Revenue increased during the reporting period.",
        relationship=EvidenceRelationship.SUPPORTS,
    )

    return EvidencePacket(
        research_run_id=run_id,
        question_id="Q1",
        as_of=AS_OF,
        execution_scope=make_scope(),
        evidence_items=[item],
        question_state=QuestionEvidenceState(
            question_id="Q1",
            availability=EvidenceAvailability.AVAILABLE,
            sufficiency=AnswerSufficiency.SUFFICIENT,
        ),
    )


def make_draft(run_id: str = "RUN1") -> FundamentalResearchDraft:
    fact = FundamentalClaim(
        claim_id="C1",
        claim_type=ClaimType.OBSERVED_FACT,
        text="Revenue increased.",
        evidence_refs=["E1"],
    )

    inference = FundamentalClaim(
        claim_id="C2",
        claim_type=ClaimType.ANALYST_INFERENCE,
        text="Revenue momentum appears durable.",
        supporting_claim_ids=["C1"],
        assumptions=["Demand conditions remain broadly stable."],
    )

    return FundamentalResearchDraft(
        company="Example Co",
        ticker="600000",
        as_of=AS_OF,
        report_period="2026H1",
        resolved_horizon=["2026Q3"],
        executive_summary="Revenue improved in the baseline period.",
        claims=[fact, inference],
        fundamental_outlook=FundamentalOutlookAssessment(
            outlook=FundamentalOutlook.IMPROVING,
            supporting_claim_ids=["C1", "C2"],
        ),
        confidence=Confidence.MEDIUM,
        research_run_id=run_id,
    )


class FixedScopeResolver:
    def __init__(self, call_log: list[str]):
        self.call_log = call_log

    def resolve(self, request, research_run_id):
        self.call_log.append("resolve_scope")
        return make_scope()


class FakeEvidenceProvider:
    def __init__(
        self,
        call_log: list[str],
        packet_run_id: str = "RUN1",
    ):
        self.call_log = call_log
        self.packet_run_id = packet_run_id

    def collect(
        self,
        request,
        execution_scope,
        research_run_id,
    ):
        self.call_log.append("collect_evidence")
        return [make_packet(self.packet_run_id)]


class FakeFundamentalAnalyst:
    def __init__(
        self,
        call_log: list[str],
        draft_run_id: str = "RUN1",
    ):
        self.call_log = call_log
        self.draft_run_id = draft_run_id

    def analyze(
        self,
        request,
        evidence_packets,
        research_run_id,
    ):
        self.call_log.append("fundamental_analyst")
        return make_draft(self.draft_run_id)


class FakeClaimReviewer:
    def __init__(
        self,
        call_log: list[str],
        status: ReviewStatus,
        review_run_id: str = "RUN1",
    ):
        self.call_log = call_log
        self.status = status
        self.review_run_id = review_run_id

    def review(
        self,
        draft,
        evidence_packets,
        research_run_id,
    ):
        self.call_log.append("claim_review")

        if self.status == ReviewStatus.PASS:
            return ClaimReviewResult(
                research_run_id=self.review_run_id,
                status=ReviewStatus.PASS,
                approved_claim_ids=["C1", "C2"],
                publication_allowed=True,
            )

        if self.status == ReviewStatus.PARTIAL:
            return ClaimReviewResult(
                research_run_id=self.review_run_id,
                status=ReviewStatus.PARTIAL,
                approved_claim_ids=["C1"],
                rejected_claim_ids=["C2"],
                reasons=["C2 is unsupported."],
                publication_allowed=True,
            )

        return ClaimReviewResult(
            research_run_id=self.review_run_id,
            status=ReviewStatus.FAIL,
            rejected_claim_ids=["C1", "C2"],
            reasons=["Critical claim is unsupported."],
            publication_allowed=False,
        )


def make_graph(
    status: ReviewStatus,
    *,
    packet_run_id: str = "RUN1",
    draft_run_id: str = "RUN1",
    review_run_id: str = "RUN1",
):
    call_log: list[str] = []

    services = WorkflowServices(
        scope_resolver=FixedScopeResolver(call_log),
        evidence_provider=FakeEvidenceProvider(
            call_log,
            packet_run_id=packet_run_id,
        ),
        fundamental_analyst=FakeFundamentalAnalyst(
            call_log,
            draft_run_id=draft_run_id,
        ),
        claim_reviewer=FakeClaimReviewer(
            call_log,
            status=status,
            review_run_id=review_run_id,
        ),
    )

    return build_research_graph(services), call_log


def invoke(graph):
    return graph.invoke(
        {
            "research_run_id": "RUN1",
            "request": make_request(),
            "run_status": ResearchRunStatus.RECEIVED,
        }
    )


def test_pass_routes_to_published():
    graph, call_log = make_graph(ReviewStatus.PASS)

    result = invoke(graph)

    assert result["run_status"] == ResearchRunStatus.PUBLISHED
    assert result["review_result"].status == ReviewStatus.PASS
    assert result["final_output"].review_status == ReviewStatus.PASS
    assert [
        claim.claim_id
        for claim in result["final_output"].claims
    ] == ["C1", "C2"]
    assert "partial_result" not in result
    assert "failure_reason" not in result
    assert call_log == [
        "resolve_scope",
        "collect_evidence",
        "fundamental_analyst",
        "claim_review",
    ]


def test_partial_routes_to_partial():
    graph, call_log = make_graph(ReviewStatus.PARTIAL)

    result = invoke(graph)

    assert result["run_status"] == ResearchRunStatus.PARTIAL
    assert result["review_result"].status == ReviewStatus.PARTIAL
    assert result["partial_result"].review_result.status == ReviewStatus.PARTIAL
    assert result["partial_result"].draft == result["draft"]
    assert "final_output" not in result
    assert "failure_reason" not in result
    assert call_log[-1] == "claim_review"


def test_fail_routes_to_preserved_failure():
    graph, call_log = make_graph(ReviewStatus.FAIL)

    result = invoke(graph)

    assert result["run_status"] == ResearchRunStatus.FAILED
    assert result["review_result"].status == ReviewStatus.FAIL
    assert result["failure_reason"] == "Critical claim is unsupported."
    assert "final_output" not in result
    assert "partial_result" not in result
    assert call_log[-1] == "claim_review"


def test_evidence_packet_run_id_mismatch_stops_workflow():
    graph, _ = make_graph(
        ReviewStatus.PASS,
        packet_run_id="WRONG",
    )

    with pytest.raises(
        ValueError,
        match="EvidencePacket research_run_id",
    ):
        invoke(graph)


def test_draft_run_id_mismatch_stops_workflow():
    graph, _ = make_graph(
        ReviewStatus.PASS,
        draft_run_id="WRONG",
    )

    with pytest.raises(
        ValueError,
        match="FundamentalResearchDraft research_run_id",
    ):
        invoke(graph)


def test_review_run_id_mismatch_stops_workflow():
    graph, _ = make_graph(
        ReviewStatus.PASS,
        review_run_id="WRONG",
    )

    with pytest.raises(
        ValueError,
        match="ClaimReviewResult research_run_id",
    ):
        invoke(graph)
