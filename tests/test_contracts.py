from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from financial_research.contracts import (
    AnswerSufficiency,
    ClaimLinkedItem,
    ClaimReviewResult,
    ClaimType,
    Confidence,
    EvidenceAvailability,
    EvidenceConflict,
    EvidenceItem,
    EvidencePacket,
    EvidenceRelationship,
    FundamentalClaim,
    FundamentalOutlook,
    FundamentalOutlookAssessment,
    FundamentalResearchDraft,
    FundamentalResearchOutput,
    PartialResearchResult,
    QuestionEvidenceState,
    ResearchQuestion,
    ResearchRequest,
    ResolvedExecutionScope,
    ReviewStatus,
)


AS_OF = datetime(2026, 8, 31, 23, 59, tzinfo=timezone.utc)
EARLIER = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)


def make_scope() -> ResolvedExecutionScope:
    return ResolvedExecutionScope(
        authorized_corpus="issuer_disclosures",
        document_scope=["2026H1"],
        corpus_version="v1",
        source_permissions=["public_disclosure"],
        resolved_at=AS_OF,
    )


def make_evidence(
    *,
    evidence_id: str = "E1",
    claim_id: str | None = "C1",
    pit_available_at: datetime = EARLIER,
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        claim_id=claim_id,
        source_id="SRC1",
        document_id="DOC1",
        source_type="filing",
        published_at=EARLIER,
        pit_available_at=pit_available_at,
        canonical_location="page:10",
        relevant_span="Revenue increased during the reporting period.",
        relationship=EvidenceRelationship.SUPPORTS,
    )


def test_research_request_accepts_one_to_five_questions():
    req = ResearchRequest(
        company="Example Co",
        ticker="600000",
        as_of=AS_OF,
        report_period="2026H1",
        research_questions=[
            ResearchQuestion(question_id="Q1", text="How did revenue change?")
        ],
    )

    assert req.horizon == 2
    assert req.research_questions[0].text == "How did revenue change?"


def test_research_request_rejects_more_than_five_questions():
    with pytest.raises(ValidationError):
        ResearchRequest(
            company="Example Co",
            ticker="600000",
            as_of=AS_OF,
            report_period="2026H1",
            research_questions=[
                ResearchQuestion(question_id=f"Q{i}", text=f"Question {i}")
                for i in range(6)
            ],
        )


def test_research_request_requires_timezone_aware_as_of():
    with pytest.raises(ValidationError, match="timezone-aware"):
        ResearchRequest(
            company="Example Co",
            ticker="600000",
            as_of=datetime(2026, 8, 31, 23, 59),
            report_period="2026H1",
            research_questions=[
                ResearchQuestion(question_id="Q1", text="Question")
            ],
        )


def test_runtime_contract_rejects_benchmark_or_gt_fields():
    with pytest.raises(ValidationError):
        ResearchRequest.model_validate(
            {
                "company": "Example Co",
                "ticker": "600000",
                "as_of": AS_OF,
                "report_period": "2026H1",
                "research_questions": [
                    {"question_id": "Q1", "text": "Question"}
                ],
                "expected_answer": "benchmark shortcut",
            }
        )


def test_evidence_requires_claim_or_target_proposition():
    with pytest.raises(ValidationError, match="bind"):
        EvidenceItem(
            evidence_id="E1",
            source_id="SRC1",
            document_id="DOC1",
            source_type="filing",
            published_at=EARLIER,
            pit_available_at=EARLIER,
            canonical_location="page:10",
            relevant_span="Relevant disclosure.",
            relationship=EvidenceRelationship.CONTEXT_ONLY,
        )


def test_evidence_packet_rejects_post_cutoff_evidence():
    with pytest.raises(ValidationError, match="unavailable"):
        EvidencePacket(
            research_run_id="RUN1",
            question_id="Q1",
            as_of=AS_OF,
            execution_scope=make_scope(),
            evidence_items=[
                make_evidence(pit_available_at=LATER)
            ],
            question_state=QuestionEvidenceState(
                question_id="Q1",
                availability=EvidenceAvailability.AVAILABLE,
                sufficiency=AnswerSufficiency.SUFFICIENT,
            ),
        )


def test_resolved_conflict_requires_resolution_basis():
    with pytest.raises(ValidationError, match="resolution_basis"):
        EvidenceConflict(
            conflict_id="X1",
            proposition="Revenue direction conflicts.",
            evidence_refs=["E1"],
            resolved=True,
        )


def test_technical_failure_is_separate_from_evidence_sufficiency():
    state = QuestionEvidenceState(
        question_id="Q1",
        availability=EvidenceAvailability.UNAVAILABLE,
        sufficiency=AnswerSufficiency.INSUFFICIENT,
        technical_state={
            "status": "FAILED",
            "error_class": "IndexUnavailable",
            "message": "Evidence index unavailable.",
        },
    )

    assert state.technical_state.status == "FAILED"
    assert state.sufficiency == AnswerSufficiency.INSUFFICIENT


def test_forward_view_requires_support_and_assumptions():
    with pytest.raises(ValidationError, match="supporting_claim_ids"):
        FundamentalClaim(
            claim_id="C2",
            claim_type=ClaimType.FORWARD_VIEW,
            text="Margins should improve next period.",
            assumptions=["Input costs remain stable."],
        )

    with pytest.raises(ValidationError, match="explicit assumptions"):
        FundamentalClaim(
            claim_id="C2",
            claim_type=ClaimType.FORWARD_VIEW,
            text="Margins should improve next period.",
            supporting_claim_ids=["C1"],
        )


def test_output_rejects_orphan_driver_reference():
    fact = FundamentalClaim(
        claim_id="C1",
        claim_type=ClaimType.OBSERVED_FACT,
        text="Revenue increased.",
        evidence_refs=["E1"],
    )

    with pytest.raises(ValidationError, match="driver references unknown"):
        FundamentalResearchOutput(
            company="Example Co",
            ticker="600000",
            as_of=AS_OF,
            report_period="2026H1",
            resolved_horizon=["2026Q3"],
            executive_summary="Fundamentals improved.",
            claims=[fact],
            drivers=[
                ClaimLinkedItem(
                    text="Revenue momentum",
                    supporting_claim_ids=["UNKNOWN"],
                )
            ],
            fundamental_outlook=FundamentalOutlookAssessment(
                outlook=FundamentalOutlook.IMPROVING,
                supporting_claim_ids=["C1"],
            ),
            confidence=Confidence.MEDIUM,
            review_status=ReviewStatus.PASS,
            research_run_id="RUN1",
        )


def test_mixed_and_undetermined_remain_distinct():
    assert FundamentalOutlook.MIXED != FundamentalOutlook.UNDETERMINED

    undetermined = FundamentalOutlookAssessment(
        outlook=FundamentalOutlook.UNDETERMINED
    )
    assert undetermined.supporting_claim_ids == []


def test_claim_review_enforces_publication_gate():
    partial = ClaimReviewResult(
        research_run_id="RUN1",
        status=ReviewStatus.PARTIAL,
        approved_claim_ids=["C1"],
        rejected_claim_ids=["C2"],
        reasons=["C2 lacks support."],
        publication_allowed=True,
    )

    assert partial.publication_allowed is True

    with pytest.raises(ValidationError, match="publication_allowed"):
        ClaimReviewResult(
            research_run_id="RUN1",
            status=ReviewStatus.FAIL,
            reasons=["Critical claim unsupported."],
            publication_allowed=True,
        )


def make_valid_draft() -> FundamentalResearchDraft:
    fact = FundamentalClaim(
        claim_id="C1",
        claim_type=ClaimType.OBSERVED_FACT,
        text="Revenue increased.",
        evidence_refs=["E1"],
    )

    return FundamentalResearchDraft(
        company="Example Co",
        ticker="600000",
        as_of=AS_OF,
        report_period="2026H1",
        resolved_horizon=["2026Q3"],
        executive_summary="Revenue improved in the baseline period.",
        claims=[fact],
        fundamental_outlook=FundamentalOutlookAssessment(
            outlook=FundamentalOutlook.IMPROVING,
            supporting_claim_ids=["C1"],
        ),
        confidence=Confidence.MEDIUM,
        research_run_id="RUN1",
    )


def test_fundamental_draft_cannot_self_assign_review_status():
    payload = make_valid_draft().model_dump()
    payload["review_status"] = ReviewStatus.PASS

    with pytest.raises(ValidationError):
        FundamentalResearchDraft.model_validate(payload)


def test_final_output_requires_review_status_after_review():
    draft = make_valid_draft()

    with pytest.raises(ValidationError):
        FundamentalResearchOutput.model_validate(draft.model_dump())

    final = FundamentalResearchOutput(
        **draft.model_dump(),
        review_status=ReviewStatus.PASS,
    )

    assert final.review_status == ReviewStatus.PASS
    assert final.research_run_id == draft.research_run_id


def test_pass_review_requires_at_least_one_approved_claim():
    with pytest.raises(ValidationError, match="approved claims"):
        ClaimReviewResult(
            research_run_id="RUN1",
            status=ReviewStatus.PASS,
            publication_allowed=True,
        )


def test_partial_review_requires_both_approved_and_rejected_claims():
    with pytest.raises(ValidationError, match="approved claims"):
        ClaimReviewResult(
            research_run_id="RUN1",
            status=ReviewStatus.PARTIAL,
            rejected_claim_ids=["C1"],
            reasons=["Only rejected claims were produced."],
            publication_allowed=True,
        )

    with pytest.raises(ValidationError, match="rejected claims"):
        ClaimReviewResult(
            research_run_id="RUN1",
            status=ReviewStatus.PARTIAL,
            approved_claim_ids=["C1"],
            publication_allowed=True,
        )


def test_partial_research_result_preserves_draft_and_review():
    draft = make_valid_draft()

    review = ClaimReviewResult(
        research_run_id="RUN1",
        status=ReviewStatus.PARTIAL,
        approved_claim_ids=["C1"],
        rejected_claim_ids=["C2"],
        reasons=["C2 is unsupported."],
        publication_allowed=True,
    )

    with pytest.raises(
        ValidationError,
        match="claims absent from draft",
    ):
        PartialResearchResult(
            research_run_id="RUN1",
            draft=draft,
            review_result=review,
        )

    second_claim = FundamentalClaim(
        claim_id="C2",
        claim_type=ClaimType.ANALYST_INFERENCE,
        text="Margin improvement is durable.",
        supporting_claim_ids=["C1"],
        assumptions=["Input costs remain stable."],
    )

    draft_with_two_claims = draft.model_copy(
        update={
            "claims": [draft.claims[0], second_claim],
        }
    )

    result = PartialResearchResult(
        research_run_id="RUN1",
        draft=draft_with_two_claims,
        review_result=review,
    )

    assert result.review_result.status == ReviewStatus.PARTIAL
    assert result.draft.executive_summary == draft.executive_summary


def test_partial_research_result_rejects_non_partial_review():
    draft = make_valid_draft()

    review = ClaimReviewResult(
        research_run_id="RUN1",
        status=ReviewStatus.PASS,
        approved_claim_ids=["C1"],
        publication_allowed=True,
    )

    with pytest.raises(
        ValidationError,
        match="requires PARTIAL",
    ):
        PartialResearchResult(
            research_run_id="RUN1",
            draft=draft,
            review_result=review,
        )
