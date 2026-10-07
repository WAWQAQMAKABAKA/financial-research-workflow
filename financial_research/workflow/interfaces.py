from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from financial_research.contracts import (
    ClaimReviewResult,
    EvidencePacket,
    FundamentalResearchDraft,
    ResearchRequest,
    ResolvedExecutionScope,
)


class ScopeResolver(Protocol):
    def resolve(
        self,
        request: ResearchRequest,
        research_run_id: str,
    ) -> ResolvedExecutionScope:
        ...


class EvidenceProvider(Protocol):
    def collect(
        self,
        request: ResearchRequest,
        execution_scope: ResolvedExecutionScope,
        research_run_id: str,
    ) -> list[EvidencePacket]:
        ...


class FundamentalAnalyst(Protocol):
    def analyze(
        self,
        request: ResearchRequest,
        evidence_packets: list[EvidencePacket],
        research_run_id: str,
    ) -> FundamentalResearchDraft:
        ...


class ClaimReviewer(Protocol):
    def review(
        self,
        draft: FundamentalResearchDraft,
        evidence_packets: list[EvidencePacket],
        research_run_id: str,
    ) -> ClaimReviewResult:
        ...


@dataclass(frozen=True)
class WorkflowServices:
    scope_resolver: ScopeResolver
    evidence_provider: EvidenceProvider
    fundamental_analyst: FundamentalAnalyst
    claim_reviewer: ClaimReviewer
