from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ResearchScope(StrEnum):
    FUNDAMENTAL = "FUNDAMENTAL"


class RequestedOutput(StrEnum):
    FUNDAMENTAL_RESEARCH = "FUNDAMENTAL_RESEARCH"


class EvidenceRelationship(StrEnum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    CONTEXT_ONLY = "CONTEXT_ONLY"


class EvidenceAvailability(StrEnum):
    AVAILABLE = "AVAILABLE"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"


class AnswerSufficiency(StrEnum):
    SUFFICIENT = "SUFFICIENT"
    PARTIALLY_SUFFICIENT = "PARTIALLY_SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"


class SourceValidationLevel(StrEnum):
    GROUNDED = "GROUNDED"
    DISCLOSURE_CONSISTENT = "DISCLOSURE_CONSISTENT"
    INDEPENDENTLY_CORROBORATED = "INDEPENDENTLY_CORROBORATED"


class TechnicalStatus(StrEnum):
    OK = "OK"
    FAILED = "FAILED"


class ClaimType(StrEnum):
    OBSERVED_FACT = "OBSERVED_FACT"
    MANAGEMENT_EXPLANATION = "MANAGEMENT_EXPLANATION"
    ANALYST_INFERENCE = "ANALYST_INFERENCE"
    FORWARD_VIEW = "FORWARD_VIEW"


class FundamentalOutlook(StrEnum):
    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    DETERIORATING = "DETERIORATING"
    MIXED = "MIXED"
    UNDETERMINED = "UNDETERMINED"


class Confidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNDETERMINED = "UNDETERMINED"


class ReviewStatus(StrEnum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"


def _require_timezone(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


class ResearchQuestion(StrictModel):
    question_id: str = Field(min_length=1)
    text: str = Field(min_length=1)


class ResearchRequest(StrictModel):
    company: str = Field(min_length=1)
    ticker: str = Field(min_length=1)
    as_of: datetime
    report_period: str = Field(min_length=1)
    research_questions: Annotated[list[ResearchQuestion], Field(min_length=1, max_length=5)]
    research_scope: ResearchScope = ResearchScope.FUNDAMENTAL
    horizon: int = Field(default=2, ge=1, le=2)
    requested_output: RequestedOutput = RequestedOutput.FUNDAMENTAL_RESEARCH

    @model_validator(mode="after")
    def validate_request(self) -> ResearchRequest:
        self.as_of = _require_timezone(self.as_of, "as_of")

        ids = [q.question_id for q in self.research_questions]
        if len(ids) != len(set(ids)):
            raise ValueError("research question IDs must be unique")

        return self


class ResolvedExecutionScope(StrictModel):
    authorized_corpus: str = Field(min_length=1)
    document_scope: list[str] = Field(default_factory=list)
    corpus_version: str = Field(min_length=1)
    source_permissions: list[str] = Field(default_factory=list)
    resolved_at: datetime

    @model_validator(mode="after")
    def validate_scope(self) -> ResolvedExecutionScope:
        self.resolved_at = _require_timezone(self.resolved_at, "resolved_at")
        return self


class EvidenceCoverage(StrictModel):
    supported_parts: list[str] = Field(default_factory=list)
    unsupported_parts: list[str] = Field(default_factory=list)
    missing_dimensions: list[str] = Field(default_factory=list)


class EvidenceItem(StrictModel):
    evidence_id: str = Field(min_length=1)
    claim_id: str | None = None
    target_proposition: str | None = None
    source_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    published_at: datetime
    pit_available_at: datetime
    page: str | None = None
    canonical_location: str = Field(min_length=1)
    relevant_span: str = Field(min_length=1)
    qualifiers: list[str] = Field(default_factory=list)
    relationship: EvidenceRelationship
    coverage: EvidenceCoverage = Field(default_factory=EvidenceCoverage)
    validation_level: SourceValidationLevel = SourceValidationLevel.GROUNDED
    provenance: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_evidence_item(self) -> EvidenceItem:
        self.published_at = _require_timezone(self.published_at, "published_at")
        self.pit_available_at = _require_timezone(
            self.pit_available_at,
            "pit_available_at",
        )

        if not self.claim_id and not self.target_proposition:
            raise ValueError(
                "evidence must bind to claim_id and/or target_proposition"
            )

        return self


class EvidenceConflict(StrictModel):
    conflict_id: str = Field(min_length=1)
    proposition: str = Field(min_length=1)
    evidence_refs: Annotated[list[str], Field(min_length=1)]
    resolved: bool = False
    resolution_basis: str | None = None

    @model_validator(mode="after")
    def validate_resolution(self) -> EvidenceConflict:
        if self.resolved and not self.resolution_basis:
            raise ValueError(
                "resolved evidence conflict requires resolution_basis"
            )
        return self


class TechnicalState(StrictModel):
    status: TechnicalStatus = TechnicalStatus.OK
    error_class: str | None = None
    message: str | None = None

    @model_validator(mode="after")
    def validate_failure(self) -> TechnicalState:
        if self.status == TechnicalStatus.FAILED and not self.error_class:
            raise ValueError("FAILED technical state requires error_class")
        return self


class QuestionEvidenceState(StrictModel):
    question_id: str = Field(min_length=1)
    availability: EvidenceAvailability
    sufficiency: AnswerSufficiency
    conflicts: list[EvidenceConflict] = Field(default_factory=list)
    technical_state: TechnicalState = Field(default_factory=TechnicalState)


class EvidencePacket(StrictModel):
    research_run_id: str = Field(min_length=1)
    question_id: str = Field(min_length=1)
    as_of: datetime
    execution_scope: ResolvedExecutionScope
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    question_state: QuestionEvidenceState

    @model_validator(mode="after")
    def validate_packet(self) -> EvidencePacket:
        self.as_of = _require_timezone(self.as_of, "as_of")

        if self.question_state.question_id != self.question_id:
            raise ValueError(
                "question_state.question_id must match EvidencePacket.question_id"
            )

        evidence_ids = [item.evidence_id for item in self.evidence_items]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("evidence IDs must be unique within a packet")

        for item in self.evidence_items:
            if item.pit_available_at > self.as_of:
                raise ValueError(
                    f"evidence {item.evidence_id} is unavailable at packet as_of"
                )

        known_evidence = set(evidence_ids)
        for conflict in self.question_state.conflicts:
            unknown = set(conflict.evidence_refs) - known_evidence
            if unknown:
                raise ValueError(
                    f"conflict {conflict.conflict_id} references unknown evidence: "
                    f"{sorted(unknown)}"
                )

        return self


class FundamentalClaim(StrictModel):
    claim_id: str = Field(min_length=1)
    claim_type: ClaimType
    text: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)
    supporting_claim_ids: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    disconfirming_conditions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_claim_trace(self) -> FundamentalClaim:
        if self.claim_type in {
            ClaimType.OBSERVED_FACT,
            ClaimType.MANAGEMENT_EXPLANATION,
        }:
            if not self.evidence_refs:
                raise ValueError(
                    f"{self.claim_type} requires direct evidence_refs"
                )

        if self.claim_type in {
            ClaimType.ANALYST_INFERENCE,
            ClaimType.FORWARD_VIEW,
        }:
            if not self.supporting_claim_ids:
                raise ValueError(
                    f"{self.claim_type} requires supporting_claim_ids"
                )
            if not self.assumptions:
                raise ValueError(
                    f"{self.claim_type} requires explicit assumptions"
                )

        if self.claim_id in self.supporting_claim_ids:
            raise ValueError("claim cannot support itself")

        return self


class ClaimLinkedItem(StrictModel):
    text: str = Field(min_length=1)
    supporting_claim_ids: Annotated[list[str], Field(min_length=1)]


class FundamentalOutlookAssessment(StrictModel):
    outlook: FundamentalOutlook
    supporting_claim_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_outlook_support(self) -> FundamentalOutlookAssessment:
        if (
            self.outlook != FundamentalOutlook.UNDETERMINED
            and not self.supporting_claim_ids
        ):
            raise ValueError(
                "determinate fundamental outlook requires supporting_claim_ids"
            )
        return self


class FundamentalResearchDraft(StrictModel):
    research_scope: ResearchScope = ResearchScope.FUNDAMENTAL
    company: str = Field(min_length=1)
    ticker: str = Field(min_length=1)
    as_of: datetime
    report_period: str = Field(min_length=1)
    resolved_horizon: Annotated[list[str], Field(min_length=1, max_length=2)]
    executive_summary: str = Field(min_length=1)
    claims: list[FundamentalClaim] = Field(default_factory=list)
    drivers: list[ClaimLinkedItem] = Field(default_factory=list)
    risks: list[ClaimLinkedItem] = Field(default_factory=list)
    fundamental_outlook: FundamentalOutlookAssessment
    key_assumptions: list[str] = Field(default_factory=list)
    disconfirming_conditions: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    source_conflicts: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    suggested_followup_questions: list[str] = Field(default_factory=list)
    confidence: Confidence
    provenance: dict[str, str] = Field(default_factory=dict)
    research_run_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_output(self) -> FundamentalResearchDraft:
        self.as_of = _require_timezone(self.as_of, "as_of")

        claim_ids = [claim.claim_id for claim in self.claims]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("claim IDs must be unique")

        known = set(claim_ids)

        for claim in self.claims:
            unknown = set(claim.supporting_claim_ids) - known
            if unknown:
                raise ValueError(
                    f"claim {claim.claim_id} references unknown claims: "
                    f"{sorted(unknown)}"
                )

        for category, items in (
            ("driver", self.drivers),
            ("risk", self.risks),
        ):
            for item in items:
                unknown = set(item.supporting_claim_ids) - known
                if unknown:
                    raise ValueError(
                        f"{category} references unknown claims: {sorted(unknown)}"
                    )

        unknown_outlook = (
            set(self.fundamental_outlook.supporting_claim_ids) - known
        )
        if unknown_outlook:
            raise ValueError(
                "fundamental outlook references unknown claims: "
                f"{sorted(unknown_outlook)}"
            )

        return self


class FundamentalResearchOutput(FundamentalResearchDraft):
    review_status: ReviewStatus


class ClaimReviewResult(StrictModel):
    research_run_id: str = Field(min_length=1)
    status: ReviewStatus
    approved_claim_ids: list[str] = Field(default_factory=list)
    rejected_claim_ids: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    publication_allowed: bool

    @model_validator(mode="after")
    def validate_publication_gate(self) -> ClaimReviewResult:
        expected = self.status in {ReviewStatus.PASS, ReviewStatus.PARTIAL}

        if self.publication_allowed != expected:
            raise ValueError(
                "publication_allowed must be true for PASS/PARTIAL "
                "and false for FAIL"
            )

        overlap = set(self.approved_claim_ids) & set(self.rejected_claim_ids)
        if overlap:
            raise ValueError(
                f"claims cannot be both approved and rejected: {sorted(overlap)}"
            )

        if self.status == ReviewStatus.PASS:
            if self.rejected_claim_ids:
                raise ValueError("PASS review cannot contain rejected claims")
            if not self.approved_claim_ids:
                raise ValueError("PASS review requires approved claims")

        if self.status == ReviewStatus.PARTIAL:
            if not self.approved_claim_ids:
                raise ValueError("PARTIAL review requires approved claims")
            if not self.rejected_claim_ids:
                raise ValueError("PARTIAL review requires rejected claims")

        if self.status == ReviewStatus.FAIL and not self.reasons:
            raise ValueError("FAIL review requires at least one reason")

        return self


class PartialResearchResult(StrictModel):
    research_run_id: str = Field(min_length=1)
    draft: FundamentalResearchDraft
    review_result: ClaimReviewResult

    @model_validator(mode="after")
    def validate_partial_result(self) -> PartialResearchResult:
        if self.review_result.status != ReviewStatus.PARTIAL:
            raise ValueError(
                "PartialResearchResult requires PARTIAL ClaimReviewResult"
            )

        if not self.review_result.publication_allowed:
            raise ValueError(
                "PartialResearchResult requires publication_allowed=true"
            )

        if self.draft.research_run_id != self.research_run_id:
            raise ValueError(
                "draft research_run_id must match PartialResearchResult"
            )

        if self.review_result.research_run_id != self.research_run_id:
            raise ValueError(
                "review_result research_run_id must match PartialResearchResult"
            )

        draft_claim_ids = {claim.claim_id for claim in self.draft.claims}
        reviewed_claim_ids = (
            set(self.review_result.approved_claim_ids)
            | set(self.review_result.rejected_claim_ids)
        )

        unknown = reviewed_claim_ids - draft_claim_ids

        if unknown:
            raise ValueError(
                "review references claims absent from draft: "
                f"{sorted(unknown)}"
            )

        return self
