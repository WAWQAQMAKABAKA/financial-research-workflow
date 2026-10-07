from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from financial_research.analysts.fundamental import (
    FUNDAMENTAL_ANALYST_SYSTEM_PROMPT,
    FundamentalAnalystEngine,
)
from financial_research.contracts import (
    AnswerSufficiency,
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
    ResearchQuestion,
    ResearchRequest,
    ResolvedExecutionScope,
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


def make_request() -> ResearchRequest:
    return ResearchRequest(
        company="Example Co",
        ticker="600000",
        as_of=AS_OF,
        report_period="2026H1",
        research_questions=[
            ResearchQuestion(
                question_id="Q1",
                text="How did revenue change?",
            )
        ],
    )


def make_scope() -> ResolvedExecutionScope:
    return ResolvedExecutionScope(
        authorized_corpus="issuer_disclosures",
        document_scope=["2026H1"],
        corpus_version="v1",
        source_permissions=["public_disclosure"],
        resolved_at=AS_OF,
    )


def make_packet() -> EvidencePacket:
    return EvidencePacket(
        research_run_id="RUN1",
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


def make_valid_draft() -> FundamentalResearchDraft:
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
        research_run_id="RUN1",
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


def test_valid_structured_draft_is_accepted():
    model = CapturingModel(
        make_valid_draft().model_dump()
    )

    engine = FundamentalAnalystEngine(model)

    result = engine.analyze(
        make_request(),
        [make_packet()],
        "RUN1",
    )

    assert isinstance(
        result,
        FundamentalResearchDraft,
    )
    assert result.research_run_id == "RUN1"
    assert [
        claim.claim_id
        for claim in result.claims
    ] == ["C1", "C2"]


def test_model_receives_only_research_request_and_evidence_payload():
    model = CapturingModel(
        make_valid_draft()
    )

    engine = FundamentalAnalystEngine(model)

    engine.analyze(
        make_request(),
        [make_packet()],
        "RUN1",
    )

    assert len(model.calls) == 1

    payload = model.calls[0]["input_payload"]

    assert set(payload) == {
        "research_run_id",
        "request",
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

    payload_keys = set(collect_keys(payload))

    forbidden_exact_keys = {
        "position",
        "average_cost",
        "p&l",
        "expected_answer",
        "ground_truth",
        "benchmark",
    }

    assert payload_keys.isdisjoint(forbidden_exact_keys)

    # Legitimate evidence vocabulary must not cause substring false positives.
    assert "target_proposition" in payload_keys


def test_unknown_evidence_reference_is_rejected():
    draft = make_valid_draft()

    bad_fact = draft.claims[0].model_copy(
        update={
            "evidence_refs": ["UNKNOWN"],
        }
    )

    bad_draft = draft.model_copy(
        update={
            "claims": [
                bad_fact,
                draft.claims[1],
            ]
        }
    )

    engine = FundamentalAnalystEngine(
        CapturingModel(bad_draft)
    )

    with pytest.raises(
        ValueError,
        match="unknown evidence",
    ):
        engine.analyze(
            make_request(),
            [make_packet()],
            "RUN1",
        )


def test_identity_drift_is_rejected():
    draft = make_valid_draft().model_copy(
        update={
            "ticker": "WRONG",
        }
    )

    engine = FundamentalAnalystEngine(
        CapturingModel(draft)
    )

    with pytest.raises(
        ValueError,
        match="identity mismatch",
    ):
        engine.analyze(
            make_request(),
            [make_packet()],
            "RUN1",
        )


def test_invalid_model_output_is_rejected_by_contract():
    engine = FundamentalAnalystEngine(
        CapturingModel(
            {
                "company": "Example Co",
                "ticker": "600000",
            }
        )
    )

    with pytest.raises(ValidationError):
        engine.analyze(
            make_request(),
            [make_packet()],
            "RUN1",
        )


def test_prompt_preserves_analyst_boundary():
    prompt = FUNDAMENTAL_ANALYST_SYSTEM_PROMPT.lower()

    assert "fundamentals only" in prompt
    assert "buy, sell, hold" in prompt
    assert "portfolio position" in prompt
    assert "target prices" in prompt
    assert "benchmark answers" in prompt
    assert "ground truth" in prompt
    assert "hidden chain-of-thought" in prompt
    assert "observed_fact" in prompt
    assert "management_explanation" in prompt
    assert "analyst_inference" in prompt
    assert "forward_view" in prompt
