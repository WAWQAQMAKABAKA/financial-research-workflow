from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from financial_research.contracts import (
    ClaimType,
    EvidencePacket,
    FundamentalResearchDraft,
    ResearchRequest,
)
from financial_research.modeling import StructuredResearchModel


FUNDAMENTAL_ANALYST_SYSTEM_PROMPT = """
You are the Fundamental Analyst inside an evidence-grounded financial research
workflow.

Your mandate is company fundamentals only.

You may analyze:
- revenue, profit, margins, expenses and cash flow;
- business, product and geographic contribution;
- company-disclosed operating drivers;
- product, pipeline and commercialization progress where relevant to company
  fundamentals;
- management guidance;
- balance sheet and liquidity;
- earnings quality;
- major fundamental risks;
- assumptions and disconfirming conditions;
- outlook for the explicitly stated research horizon.

You must not:
- make buy, sell, hold or position-sizing recommendations;
- use portfolio position, cost or P&L;
- produce valuation or target prices;
- perform market-structure or trading analysis;
- invent evidence;
- treat absence from supplied evidence as proof of whole-report non-disclosure;
- turn management explanation into independently established fact;
- treat historical facts as sufficient proof of a forward view;
- use benchmark answers, ground truth or evaluator-only material.

Claim semantics:
- OBSERVED_FACT: directly supported by supplied evidence.
- MANAGEMENT_EXPLANATION: management's stated explanation, directly supported by
  supplied evidence and clearly attributed.
- ANALYST_INFERENCE: an analyst interpretation supported by prior claims and
  explicit assumptions.
- FORWARD_VIEW: a forward-looking research judgment supported by prior claims,
  explicit assumptions and relevant disconfirming conditions.

Every substantive conclusion must remain traceable through the claim chain.

Use only evidence IDs supplied in the EvidencePacket objects.

If evidence is insufficient, preserve the limitation and use an appropriately
bounded conclusion or UNDETERMINED outlook rather than inventing completeness.

Do not provide hidden chain-of-thought. Return only the requested structured
research artifact.
""".strip()


class FundamentalAnalystEngine:
    def __init__(
        self,
        model: StructuredResearchModel,
    ) -> None:
        self._model = model

    def analyze(
        self,
        request: ResearchRequest,
        evidence_packets: list[EvidencePacket],
        research_run_id: str,
    ) -> FundamentalResearchDraft:
        payload = self._build_input_payload(
            request=request,
            evidence_packets=evidence_packets,
            research_run_id=research_run_id,
        )

        raw = self._model.generate(
            system_prompt=FUNDAMENTAL_ANALYST_SYSTEM_PROMPT,
            input_payload=payload,
            output_schema=FundamentalResearchDraft,
        )

        if isinstance(raw, FundamentalResearchDraft):
            draft = raw
        elif isinstance(raw, BaseModel):
            draft = FundamentalResearchDraft.model_validate(
                raw.model_dump()
            )
        else:
            draft = FundamentalResearchDraft.model_validate(raw)

        self._validate_identity(
            request=request,
            draft=draft,
            research_run_id=research_run_id,
        )

        self._validate_evidence_references(
            draft=draft,
            evidence_packets=evidence_packets,
        )

        return draft

    @staticmethod
    def _build_input_payload(
        *,
        request: ResearchRequest,
        evidence_packets: list[EvidencePacket],
        research_run_id: str,
    ) -> dict[str, Any]:
        return {
            "research_run_id": research_run_id,
            "request": request.model_dump(mode="json"),
            "evidence_packets": [
                packet.model_dump(mode="json")
                for packet in evidence_packets
            ],
        }

    @staticmethod
    def _validate_identity(
        *,
        request: ResearchRequest,
        draft: FundamentalResearchDraft,
        research_run_id: str,
    ) -> None:
        mismatches: list[str] = []

        if draft.research_run_id != research_run_id:
            mismatches.append("research_run_id")

        if draft.company != request.company:
            mismatches.append("company")

        if draft.ticker != request.ticker:
            mismatches.append("ticker")

        if draft.as_of != request.as_of:
            mismatches.append("as_of")

        if draft.report_period != request.report_period:
            mismatches.append("report_period")

        if draft.research_scope != request.research_scope:
            mismatches.append("research_scope")

        if mismatches:
            raise ValueError(
                "FundamentalResearchDraft identity mismatch: "
                f"{sorted(mismatches)}"
            )

    @staticmethod
    def _validate_evidence_references(
        *,
        draft: FundamentalResearchDraft,
        evidence_packets: list[EvidencePacket],
    ) -> None:
        known_evidence_ids = {
            item.evidence_id
            for packet in evidence_packets
            for item in packet.evidence_items
        }

        for claim in draft.claims:
            if claim.claim_type not in {
                ClaimType.OBSERVED_FACT,
                ClaimType.MANAGEMENT_EXPLANATION,
            }:
                continue

            unknown = (
                set(claim.evidence_refs)
                - known_evidence_ids
            )

            if unknown:
                raise ValueError(
                    f"claim {claim.claim_id} references unknown evidence: "
                    f"{sorted(unknown)}"
                )
