from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

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
    ResolvedExecutionScope,
    ReviewStatus,
)
from financial_research.review import (
    CLAIM_REVIEWER_SYSTEM_PROMPT,
    ClaimReviewerEngine,
)


AS_OF = datetime(
    2026,
    8,
    31,
    23,
    59,
    tzinfo=timezone.utc,
)

EARLIER = datetime(
    2026,
    8,
    30,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_scope() -> ResolvedExecutionScope:
    return ResolvedExecutionScope(
        authorized_corpus="issuer_disclosures",
        document_scope=["2026H1"],
        corpus_version="v1",
        source_permissions=["public_disclosure"],
        resolved_at=AS_OF,
    )


def make_packet(
    run_id: str = "RUN1",
) -> EvidencePacket:
    return EvidencePacket(
        research_run_id=run_id,
        question_id="Q1",
        as_of=AS_OF,
        execution_scope=make_scope(),
        evidence_items=[
            EvidenceItem(
                evidence_id="E1",
                claim_id="C1",
                source_id="SRC1",
                document_id="DOC1",
                source_type="filing",
                published_at=EARLIER,
                pit_available_at=EARLIER,
                canonical_location="page:10",
                relevant_span=(
                    "Revenue increased during the reporting period."
                ),
                relationship=EvidenceRelationship.SUPPORTS,
            )
        ],
        question_state=QuestionEvidenceState(
            question_id="Q1",
            availability=EvidenceAvailability.AVAILABLE,
            sufficiency=AnswerSufficiency.SUFFICIENT,
        ),
    )


def make_draft(
    run_id: str = "RUN1",
) -> FundamentalResearchDraft:
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
        assumptions=[
            "Demand conditions remain broadly stable."
        ],
    )

    return FundamentalResearchDraft(
        company="Example Co",
        ticker="600000",
        as_of=AS_OF,
        report_period="2026H1",
        resolved_horizon=["2026Q3"],
        executive_summary=(
            "Revenue improved and momentum appears durable."
        ),
        claims=[fact, inference],
        fundamental_outlook=FundamentalOutlookAssessment(
            outlook=FundamentalOutlook.IMPROVING,
            supporting_claim_ids=["C1", "C2"],
        ),
        confidence=Confidence.MEDIUM,
        research_run_id=run_id,
    )


class CapturingModel:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate(
        self,
        *,
        system_prompt,
        input_payload,
        output_schema,
    ):
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "input_payload": input_payload,
                "output_schema": output_schema,
            }
        )
        return self.response


def test_valid_pass_review_is_accepted():
    response = ClaimReviewResult(
        research_run_id="RUN1",
        status=ReviewStatus.PASS,
        approved_claim_ids=["C1", "C2"],
        publication_allowed=True,
    )

    model = CapturingModel(response)
    reviewer = ClaimReviewerEngine(model)

    result = reviewer.review(
        make_draft(),
        [make_packet()],
        "RUN1",
    )

    assert result.status == ReviewStatus.PASS
    assert result.approved_claim_ids == ["C1", "C2"]


def test_valid_partial_review_is_accepted_and_payload_is_bounded():
    response = ClaimReviewResult(
        research_run_id="RUN1",
        status=ReviewStatus.PARTIAL,
        approved_claim_ids=["C1"],
        rejected_claim_ids=["C2"],
        reasons=["C2 lacks sufficient forward support."],
        publication_allowed=True,
    )

    model = CapturingModel(response)
    reviewer = ClaimReviewerEngine(model)

    result = reviewer.review(
        make_draft(),
        [make_packet()],
        "RUN1",
    )

    assert result.status == ReviewStatus.PARTIAL
    assert len(model.calls) == 1

    call = model.calls[0]

    assert call["output_schema"] is ClaimReviewResult

    payload = call["input_payload"]

    assert set(payload) == {
        "research_run_id",
        "draft",
        "evidence_packets",
    }

    def collect_keys(value):
        keys = []

        if isinstance(value, dict):
            for key, child in value.items():
                keys.append(str(key).lower())
                keys.extend(collect_keys(child))

        elif isinstance(value, list):
            for child in value:
                keys.extend(collect_keys(child))

        return keys

    keys = set(collect_keys(payload))

    forbidden = {
        "position",
        "average_cost",
        "p&l",
        "expected_answer",
        "ground_truth",
        "benchmark",
    }

    assert not (keys & forbidden)
    assert "target_proposition" in keys


def test_unknown_claim_reference_is_rejected():
    response = ClaimReviewResult(
        research_run_id="RUN1",
        status=ReviewStatus.PARTIAL,
        approved_claim_ids=["C1"],
        rejected_claim_ids=["UNKNOWN"],
        reasons=["Unknown claim."],
        publication_allowed=True,
    )

    reviewer = ClaimReviewerEngine(
        CapturingModel(response)
    )

    with pytest.raises(
        ValueError,
        match="unknown draft claims",
    ):
        reviewer.review(
            make_draft(),
            [make_packet()],
            "RUN1",
        )


def test_publishable_review_requires_complete_claim_coverage():
    response = ClaimReviewResult(
        research_run_id="RUN1",
        status=ReviewStatus.PASS,
        approved_claim_ids=["C1"],
        publication_allowed=True,
    )

    reviewer = ClaimReviewerEngine(
        CapturingModel(response)
    )

    with pytest.raises(
        ValueError,
        match="complete draft claim set",
    ):
        reviewer.review(
            make_draft(),
            [make_packet()],
            "RUN1",
        )


def test_review_result_run_id_mismatch_is_rejected():
    response = ClaimReviewResult(
        research_run_id="WRONG",
        status=ReviewStatus.PASS,
        approved_claim_ids=["C1", "C2"],
        publication_allowed=True,
    )

    reviewer = ClaimReviewerEngine(
        CapturingModel(response)
    )

    with pytest.raises(
        ValueError,
        match="ClaimReviewResult research_run_id",
    ):
        reviewer.review(
            make_draft(),
            [make_packet()],
            "RUN1",
        )


def test_evidence_packet_run_id_mismatch_is_rejected():
    response = ClaimReviewResult(
        research_run_id="RUN1",
        status=ReviewStatus.PASS,
        approved_claim_ids=["C1", "C2"],
        publication_allowed=True,
    )

    reviewer = ClaimReviewerEngine(
        CapturingModel(response)
    )

    with pytest.raises(
        ValueError,
        match="EvidencePacket research_run_id",
    ):
        reviewer.review(
            make_draft(),
            [make_packet("WRONG")],
            "RUN1",
        )


def test_invalid_model_output_is_rejected_by_contract():
    reviewer = ClaimReviewerEngine(
        CapturingModel(
            {
                "research_run_id": "RUN1",
                "status": "PASS",
            }
        )
    )

    with pytest.raises(ValidationError):
        reviewer.review(
            make_draft(),
            [make_packet()],
            "RUN1",
        )


def test_reviewer_prompt_preserves_publication_gate_boundary():
    prompt = CLAIM_REVIEWER_SYSTEM_PROMPT.lower()

    assert "publication control" in prompt
    assert "not new analysis" in prompt
    assert "observed_fact" in prompt
    assert "management_explanation" in prompt
    assert "analyst_inference" in prompt
    assert "forward_view" in prompt
    assert "context_only" in prompt
    assert "rewrite the analyst draft" in prompt
    assert "buy, sell, hold" in prompt
    assert "portfolio position" in prompt
    assert "benchmark answers" in prompt
    assert "ground truth" in prompt
    assert "hidden chain-of-thought" in prompt
