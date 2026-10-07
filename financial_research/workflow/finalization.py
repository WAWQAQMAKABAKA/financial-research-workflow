from __future__ import annotations

from financial_research.contracts import (
    ClaimReviewResult,
    FundamentalResearchDraft,
    FundamentalResearchOutput,
    PartialResearchResult,
    ReviewStatus,
)


def _require_matching_run_ids(
    draft: FundamentalResearchDraft,
    review: ClaimReviewResult,
) -> None:
    if draft.research_run_id != review.research_run_id:
        raise ValueError(
            "draft and review research_run_id must match"
        )


def _draft_claim_ids(
    draft: FundamentalResearchDraft,
) -> set[str]:
    return {
        claim.claim_id
        for claim in draft.claims
    }


def finalize_pass(
    draft: FundamentalResearchDraft,
    review: ClaimReviewResult,
) -> FundamentalResearchOutput:
    _require_matching_run_ids(draft, review)

    if review.status != ReviewStatus.PASS:
        raise ValueError(
            "finalize_pass requires PASS ClaimReviewResult"
        )

    draft_claim_ids = _draft_claim_ids(draft)
    approved_claim_ids = set(review.approved_claim_ids)

    if approved_claim_ids != draft_claim_ids:
        missing = sorted(draft_claim_ids - approved_claim_ids)
        unexpected = sorted(approved_claim_ids - draft_claim_ids)

        raise ValueError(
            "PASS review must approve the complete draft claim set; "
            f"missing={missing}, unexpected={unexpected}"
        )

    return FundamentalResearchOutput(
        **draft.model_dump(),
        review_status=ReviewStatus.PASS,
    )


def finalize_partial(
    draft: FundamentalResearchDraft,
    review: ClaimReviewResult,
) -> PartialResearchResult:
    _require_matching_run_ids(draft, review)

    if review.status != ReviewStatus.PARTIAL:
        raise ValueError(
            "finalize_partial requires PARTIAL ClaimReviewResult"
        )

    draft_claim_ids = _draft_claim_ids(draft)

    reviewed_claim_ids = (
        set(review.approved_claim_ids)
        | set(review.rejected_claim_ids)
    )

    if reviewed_claim_ids != draft_claim_ids:
        missing = sorted(draft_claim_ids - reviewed_claim_ids)
        unexpected = sorted(reviewed_claim_ids - draft_claim_ids)

        raise ValueError(
            "PARTIAL review must classify the complete draft claim set; "
            f"missing={missing}, unexpected={unexpected}"
        )

    return PartialResearchResult(
        research_run_id=draft.research_run_id,
        draft=draft,
        review_result=review,
    )
