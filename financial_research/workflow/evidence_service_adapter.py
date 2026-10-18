"""FRW boundary adapter for an injected Financial Evidence Service.

This module does not implement retrieval, source validation,
PIT observation policy, or evidence sufficiency adjudication.

No production Financial Evidence Service is provided here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from financial_research.contracts import (
    EvidencePacket,
    ResearchRequest,
    ResolvedExecutionScope,
)


class EvidenceScopeAuthorizationError(PermissionError):
    """Explicit document authorization is absent or invalid."""


class FinancialEvidenceServiceClient(Protocol):
    def fetch_packets(
        self,
        request: ResearchRequest,
        execution_scope: ResolvedExecutionScope,
        research_run_id: str,
    ) -> list[EvidencePacket]:
        ...


@dataclass(frozen=True)
class EvidenceServiceProviderAdapter:
    service: FinancialEvidenceServiceClient

    def collect(
        self,
        request: ResearchRequest,
        execution_scope: ResolvedExecutionScope,
        research_run_id: str,
    ) -> list[EvidencePacket]:
        """Validate service output before LangGraph receives it.

        This boundary checks transport consistency only.
        The service remains responsible for provenance,
        runtime PIT admission, observation history, source
        versions, and independent sufficiency assessment.
        """
        if not isinstance(request, ResearchRequest):
            raise TypeError("request must be ResearchRequest")

        if not isinstance(
            execution_scope, ResolvedExecutionScope
        ):
            raise TypeError(
                "execution_scope must be ResolvedExecutionScope"
            )

        if (
            not isinstance(research_run_id, str)
            or not research_run_id
        ):
            raise ValueError("research_run_id is required")

        # Fail closed before calling the evidence backend.
        # An empty scope is not corpus-wide authorization.
        if (
            not execution_scope.document_scope
            or any(
                not document_id.strip()
                for document_id in execution_scope.document_scope
            )
        ):
            raise EvidenceScopeAuthorizationError(
                "document_scope requires at least one "
                "explicit nonblank authorized document ID"
            )

        permitted = set(execution_scope.document_scope)

        raw_packets = self.service.fetch_packets(
            request,
            execution_scope,
            research_run_id,
        )

        if not isinstance(raw_packets, list):
            raise TypeError(
                "Financial Evidence Service must return a list"
            )

        requested_ids = {
            question.question_id
            for question in request.research_questions
        }

        received_ids = set()
        validated_packets = []

        for raw_packet in raw_packets:
            if not isinstance(raw_packet, EvidencePacket):
                raise TypeError(
                    "Financial Evidence Service returned "
                    "a non-EvidencePacket item"
                )

            # Revalidate, including PIT boundaries, instead
            # of trusting a potentially mutated model instance.
            packet = EvidencePacket.model_validate(
                raw_packet.model_dump(mode="python")
            )

            if packet.research_run_id != research_run_id:
                raise ValueError(
                    "evidence packet research_run_id mismatch"
                )

            if packet.as_of != request.as_of:
                raise ValueError(
                    "evidence packet as_of mismatch"
                )

            if packet.execution_scope != execution_scope:
                raise ValueError(
                    "evidence packet execution_scope mismatch"
                )

            if packet.question_id not in requested_ids:
                raise ValueError(
                    "evidence packet has an unrequested question"
                )

            if packet.question_id in received_ids:
                raise ValueError(
                    "duplicate evidence packet question"
                )

            for item in packet.evidence_items:
                if item.document_id not in permitted:
                    raise ValueError(
                        "evidence document outside "
                        "resolved document_scope"
                    )

            received_ids.add(packet.question_id)
            validated_packets.append(packet)

        if received_ids != requested_ids:
            raise ValueError(
                "Financial Evidence Service must return "
                "one packet per research question"
            )

        return validated_packets
