"""Test-only P2-to-FRW boundary experiment.

Archived case identifiers, synthetic payloads.
Not a production EvidenceProvider, source validation or PIT check.
"""
from dataclasses import dataclass
import pytest
from pydantic import ValidationError
from datetime import datetime, timedelta, timezone

from financial_research.contracts import (
    AnswerSufficiency,
    EvidenceAvailability,
    EvidenceItem,
    EvidencePacket,
    EvidenceRelationship,
    QuestionEvidenceState,
    ResearchQuestion,
    ResearchRequest,
    ResolvedExecutionScope,
    TechnicalStatus,
)


@dataclass(frozen=True)
class P2Observation:
    document_id: str
    chunk_index: int
    status: str
    context_text: str | None


class P2TestAdapter:
    """Maps test observations; does not execute P1 or P2."""

    def __init__(self, observation, assessment):
        self.observation = observation
        self.assessment = assessment
        self.diagnostics = []

    def collect(self, request, execution_scope, research_run_id):
        observation = self.observation
        question = request.research_questions[0]

        if observation.document_id not in execution_scope.document_scope:
            raise ValueError("Document outside test execution scope")

        if observation.status == "EXPANDED_VERIFIED":
            if not observation.context_text:
                raise ValueError("Missing test context")

            items = [
                EvidenceItem(
                    evidence_id="TEST_ONLY_E1",
                    target_claim_id="TEST_TARGET_1",
                    target_proposition=(
                        "This is a test-only evidence target."
                    ),
                    source_id="SYNTHETIC_TEST_FIXTURE",
                    document_id=observation.document_id,
                    source_type="test_fixture",
                    published_at=request.as_of - timedelta(days=2),
                    pit_available_at=request.as_of - timedelta(days=1),
                    canonical_location="TEST_ONLY_NOT_CANONICAL",
                    relevant_span=observation.context_text,
                    relationship=EvidenceRelationship.CONTEXT_ONLY,
                    qualifiers=[
                        "Synthetic dates, not actual filing PIT",
                        "No live canonical-source verification",
                    ],
                    provenance={
                        "fixture_kind": "synthetic_contract_test",
                        "p2_status": observation.status,
                    },
                )
            ]
        elif observation.status == "UNAVAILABLE":
            items = []
        else:
            raise ValueError("Unexpected test P2 status")

        self.diagnostics.append({
            "document_id": observation.document_id,
            "chunk_index": observation.chunk_index,
            "p2_status": observation.status,
            "not_question_availability": True,
        })

        return [
            EvidencePacket(
                research_run_id=research_run_id,
                question_id=question.question_id,
                as_of=request.as_of,
                execution_scope=execution_scope,
                evidence_items=items,
                question_state=QuestionEvidenceState(
                    question_id=question.question_id,
                    availability=self.assessment[0],
                    sufficiency=self.assessment[1],
                ),
            )
        ]


def make_inputs(document_id):
    as_of = datetime(2026, 10, 1, tzinfo=timezone.utc)

    request = ResearchRequest(
        company="TEST ONLY",
        ticker="TEST000",
        as_of=as_of,
        report_period="2026H1",
        research_questions=[
            ResearchQuestion(
                question_id="Q1",
                text="Test-only financial evidence question",
            )
        ],
    )

    scope = ResolvedExecutionScope(
        authorized_corpus="synthetic_test_corpus",
        document_scope=[document_id],
        corpus_version="test_only",
        source_permissions=["test_fixture"],
        resolved_at=as_of,
    )

    return request, scope


def test_shenfei_verified_context_is_not_sufficiency():
    observation = P2Observation(
        document_id="600760-2026H1-cninfo-1225517994",
        chunk_index=215,
        status="EXPANDED_VERIFIED",
        context_text="SYNTHETIC_TABLE_CONTEXT_NOT_SOURCE_TEXT",
    )

    # This is an explicit test assessment, not a P2 inference.
    assessment = (
        EvidenceAvailability.PARTIAL,
        AnswerSufficiency.INSUFFICIENT,
    )

    provider = P2TestAdapter(observation, assessment)
    request, scope = make_inputs(observation.document_id)
    packets = provider.collect(request, scope, "RUN_TEST_1")

    assert len(packets) == 1
    packet = packets[0]
    assert packet.research_run_id == "RUN_TEST_1"
    assert len(packet.evidence_items) == 1
    assert (
        packet.evidence_items[0].relationship
        == EvidenceRelationship.CONTEXT_ONLY
    )
    assert (
        packet.evidence_items[0].provenance["p2_status"]
        == "EXPANDED_VERIFIED"
    )
    assert packet.question_state.sufficiency == assessment[1]
    assert packet.question_state.availability == assessment[0]


def test_hengrui_p2_unavailable_does_not_infer_question_state():
    observation = P2Observation(
        document_id="600276-2026H1-cninfo-1225483600",
        chunk_index=234,
        status="UNAVAILABLE",
        context_text=None,
    )

    # Independent simulated assessment, not derived from P2.
    # No other traceable evidence was supplied in this test.
    assessment = (
        EvidenceAvailability.UNAVAILABLE,
        AnswerSufficiency.INSUFFICIENT,
    )

    provider = P2TestAdapter(observation, assessment)
    request, scope = make_inputs(observation.document_id)
    packets = provider.collect(request, scope, "RUN_TEST_2")

    packet = packets[0]
    assert packet.evidence_items == []
    assert packet.question_state.availability == assessment[0]
    assert packet.question_state.sufficiency == assessment[1]
    assert packet.question_state.technical_state.status == TechnicalStatus.OK
    assert provider.diagnostics[0]["p2_status"] == "UNAVAILABLE"
    assert provider.diagnostics[0]["not_question_availability"] is True


@pytest.mark.parametrize(
    "claimed_availability",
    [
        EvidenceAvailability.AVAILABLE,
        EvidenceAvailability.PARTIAL,
    ],
)
def test_empty_packet_rejects_claimed_evidence_availability(
    claimed_availability,
):
    """P2 failure cannot become ungrounded question availability."""
    observation = P2Observation(
        document_id="600276-2026H1-cninfo-1225483600",
        chunk_index=234,
        status="UNAVAILABLE",
        context_text=None,
    )

    provider = P2TestAdapter(
        observation,
        (
            claimed_availability,
            AnswerSufficiency.INSUFFICIENT,
        ),
    )

    request, scope = make_inputs(observation.document_id)

    with pytest.raises(
        ValidationError,
        match="requires traceable evidence_items",
    ):
        provider.collect(
            request,
            scope,
            "RUN_NEGATIVE_TEST",
        )
