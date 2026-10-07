from __future__ import annotations

from enum import StrEnum
from typing import NotRequired, TypedDict

from financial_research.contracts import (
    ClaimReviewResult,
    EvidencePacket,
    FundamentalResearchDraft,
    FundamentalResearchOutput,
    PartialResearchResult,
    ResearchRequest,
    ResolvedExecutionScope,
)


class ResearchRunStatus(StrEnum):
    RECEIVED = "RECEIVED"
    VALIDATED = "VALIDATED"
    SCOPE_RESOLVED = "SCOPE_RESOLVED"
    EVIDENCE_COLLECTED = "EVIDENCE_COLLECTED"
    DRAFTED = "DRAFTED"
    REVIEWED = "REVIEWED"
    PUBLISHED = "PUBLISHED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class ResearchState(TypedDict, total=False):
    research_run_id: str
    request: ResearchRequest
    execution_scope: ResolvedExecutionScope
    evidence_packets: list[EvidencePacket]
    draft: FundamentalResearchDraft
    review_result: ClaimReviewResult
    final_output: NotRequired[FundamentalResearchOutput]
    partial_result: NotRequired[PartialResearchResult]
    run_status: ResearchRunStatus
    failure_reason: NotRequired[str]
