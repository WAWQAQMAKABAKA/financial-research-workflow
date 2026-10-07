from datetime import datetime, timezone

import pytest

from financial_research.contracts import (
    ClaimReviewResult,
    ClaimType,
    Confidence,
    FundamentalClaim,
    FundamentalOutlook,
    FundamentalOutlookAssessment,
    FundamentalResearchDraft,
    FundamentalResearchOutput,
    PartialResearchResult,
    ReviewStatus,
)
from financial_research.workflow.finalization import (
    finalize_partial,
    finalize_pass,
)


AS_OF = datetime(
    2026,
    8,
    31,
    23,
    59,
    tzinfo=timezone.utc,
)


def make_draft() -> FundamentalResearchDraft:
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
        claims=[
            fact,
            inference,
        ],
        fundamental_outlook=FundamentalOutlookAssessment(
            outlook=FundamentalOutlook.IMPROVING,
            supporting_claim_ids=["C1", "C2"],
        ),
        confidence=Confidence.MEDIUM,
        research_run_id="RUN1",
    )


def test_finalize_pass_creates_complete_final_output():
    draft = make_draft()

    review = ClaimReviewResult(
        research_run_id="RUN1",
        status=ReviewStatus.PASS,
        approved_claim_ids=["C1", "C2"],
        publication_allowed=True,
    )

    result = finalize_pass(
        draft,
        review,
    )

    assert isinstance(
        result,
        FundamentalResearchOutput,
    )
    assert result.review_status == ReviewStatus.PASS
    assert result.executive_summary == draft.executive_summary
    assert [
        claim.claim_id
        for claim in result.claims
    ] == ["C1", "C2"]


def test_finalize_pass_rejects_incomplete_review_coverage():
    draft = make_draft()

    review = ClaimReviewResult(
        research_run_id="RUN1",
        status=ReviewStatus.PASS,
        approved_claim_ids=["C1"],
        publication_allowed=True,
    )

    with pytest.raises(
        ValueError,
        match="complete draft claim set",
    ):
        finalize_pass(
            draft,
            review,
        )


def test_finalize_partial_preserves_original_draft():
    draft = make_draft()

    review = ClaimReviewResult(
        research_run_id="RUN1",
        status=ReviewStatus.PARTIAL,
        approved_claim_ids=["C1"],
        rejected_claim_ids=["C2"],
        reasons=[
            "C2 lacks sufficient forward support."
        ],
        publication_allowed=True,
    )

    result = finalize_partial(
        draft,
        review,
    )

    assert isinstance(
        result,
        PartialResearchResult,
    )
    assert result.draft == draft
    assert result.review_result == review
    assert result.draft.executive_summary == (
        "Revenue improved and momentum appears durable."
    )


def test_finalize_partial_rejects_unreviewed_claim():
    draft = make_draft()

    extra = FundamentalClaim(
        claim_id="C3",
        claim_type=ClaimType.ANALYST_INFERENCE,
        text="Margin pressure may ease.",
        supporting_claim_ids=["C1"],
        assumptions=[
            "Input costs do not increase materially."
        ],
    )

    draft = draft.model_copy(
        update={
            "claims": [
                *draft.claims,
                extra,
            ]
        }
    )

    review = ClaimReviewResult(
        research_run_id="RUN1",
        status=ReviewStatus.PARTIAL,
        approved_claim_ids=["C1"],
        rejected_claim_ids=["C2"],
        reasons=[
            "C2 lacks sufficient forward support."
        ],
        publication_allowed=True,
    )

    with pytest.raises(
        ValueError,
        match="classify the complete draft claim set",
    ):
        finalize_partial(
            draft,
            review,
        )


def test_finalizers_reject_wrong_review_status():
    draft = make_draft()

    partial_review = ClaimReviewResult(
        research_run_id="RUN1",
        status=ReviewStatus.PARTIAL,
        approved_claim_ids=["C1"],
        rejected_claim_ids=["C2"],
        reasons=["C2 rejected."],
        publication_allowed=True,
    )

    pass_review = ClaimReviewResult(
        research_run_id="RUN1",
        status=ReviewStatus.PASS,
        approved_claim_ids=["C1", "C2"],
        publication_allowed=True,
    )

    with pytest.raises(
        ValueError,
        match="requires PASS",
    ):
        finalize_pass(
            draft,
            partial_review,
        )

    with pytest.raises(
        ValueError,
        match="requires PARTIAL",
    ):
        finalize_partial(
            draft,
            pass_review,
        )
