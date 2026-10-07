from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from financial_research.contracts import (
    ClaimReviewResult,
    EvidencePacket,
    FundamentalResearchDraft,
    ReviewStatus,
)
from financial_research.modeling import StructuredResearchModel


CLAIM_REVIEWER_SYSTEM_PROMPT = """
You are the independent Claim Reviewer inside an evidence-grounded financial
research workflow.

You review a FundamentalResearchDraft against only the supplied EvidencePacket
objects and the explicit claim chain in the draft.

Your job is publication control, not new analysis.

For every substantive claim, determine whether it is acceptable for
publication under the declared claim type and supplied support.

Review principles:
- OBSERVED_FACT must be directly supported by supplied evidence.
- MANAGEMENT_EXPLANATION must be supported by supplied evidence and remain
  explicitly attributable to management.
- ANALYST_INFERENCE must be traceable to supported prior claims and explicit
  assumptions.
- FORWARD_VIEW must be traceable to supported prior claims, explicit
  assumptions, and appropriate disconfirming conditions.
- CONTEXT_ONLY evidence is not direct support for a claim.
- Missing or insufficient evidence must not be converted into certainty.
- Unsupported, overstated, misclassified, or orphaned claims must not pass
  silently.

Publication statuses:
- PASS: every substantive draft claim is approved.
- PARTIAL: at least one substantive claim is approved and at least one is
  rejected; every substantive draft claim must be classified.
- FAIL: publication is not allowed because the research artifact fails the
  publication gate.

You must not:
- rewrite the analyst draft;
- create new claims or evidence;
- produce buy, sell, hold, position-sizing, valuation, or target-price advice;
- use portfolio position, cost, or P&L;
- use benchmark answers, ground truth, or evaluator-only material;
- provide hidden chain-of-thought.

Return only the requested structured ClaimReviewResult.
""".strip()


class ClaimReviewerEngine:
    def __init__(
        self,
        model: StructuredResearchModel,
    ) -> None:
        self._model = model

    def review(
        self,
        draft: FundamentalResearchDraft,
        evidence_packets: list[EvidencePacket],
        research_run_id: str,
    ) -> ClaimReviewResult:
        self._validate_input_run_ids(
            evidence_packets=evidence_packets,
            research_run_id=research_run_id,
        )

        payload = self._build_input_payload(
            draft=draft,
            evidence_packets=evidence_packets,
            research_run_id=research_run_id,
        )

        raw = self._model.generate(
            system_prompt=CLAIM_REVIEWER_SYSTEM_PROMPT,
            input_payload=payload,
            output_schema=ClaimReviewResult,
        )

        if isinstance(raw, ClaimReviewResult):
            result = raw
        elif isinstance(raw, BaseModel):
            result = ClaimReviewResult.model_validate(
                raw.model_dump()
            )
        else:
            result = ClaimReviewResult.model_validate(raw)

        self._validate_result(
            draft=draft,
            result=result,
            research_run_id=research_run_id,
        )

        return result

    @staticmethod
    def _build_input_payload(
        *,
        draft: FundamentalResearchDraft,
        evidence_packets: list[EvidencePacket],
        research_run_id: str,
    ) -> dict[str, Any]:
        return {
            "research_run_id": research_run_id,
            "draft": draft.model_dump(mode="json"),
            "evidence_packets": [
                packet.model_dump(mode="json")
                for packet in evidence_packets
            ],
        }

    @staticmethod
    def _validate_input_run_ids(
        *,
        evidence_packets: list[EvidencePacket],
        research_run_id: str,
    ) -> None:
        mismatched = sorted(
            {
                packet.research_run_id
                for packet in evidence_packets
                if packet.research_run_id != research_run_id
            }
        )

        if mismatched:
            raise ValueError(
                "EvidencePacket research_run_id does not match reviewer run: "
                f"{mismatched}"
            )

    @staticmethod
    def _validate_result(
        *,
        draft: FundamentalResearchDraft,
        result: ClaimReviewResult,
        research_run_id: str,
    ) -> None:
        if draft.research_run_id != research_run_id:
            raise ValueError(
                "draft research_run_id does not match reviewer run"
            )

        if result.research_run_id != research_run_id:
            raise ValueError(
                "ClaimReviewResult research_run_id does not match reviewer run"
            )

        if len(result.approved_claim_ids) != len(
            set(result.approved_claim_ids)
        ):
            raise ValueError(
                "approved_claim_ids cannot contain duplicates"
            )

        if len(result.rejected_claim_ids) != len(
            set(result.rejected_claim_ids)
        ):
            raise ValueError(
                "rejected_claim_ids cannot contain duplicates"
            )

        draft_claim_ids = {
            claim.claim_id
            for claim in draft.claims
        }

        reviewed_claim_ids = (
            set(result.approved_claim_ids)
            | set(result.rejected_claim_ids)
        )

        unknown = reviewed_claim_ids - draft_claim_ids

        if unknown:
            raise ValueError(
                "ClaimReviewResult references unknown draft claims: "
                f"{sorted(unknown)}"
            )

        if result.status in {
            ReviewStatus.PASS,
            ReviewStatus.PARTIAL,
        }:
            missing = draft_claim_ids - reviewed_claim_ids

            if missing:
                raise ValueError(
                    "publishable review must classify the complete draft "
                    f"claim set; missing={sorted(missing)}"
                )
