"""Boundary-only tests with an injected fake service.

No real retrieval, Financial Evidence Service, or
source-backed sufficiency judgment is exercised.
"""

from datetime import timedelta

import pytest
from pydantic import ValidationError

from financial_research.contracts import (
    AnswerSufficiency,
    EvidenceAvailability,
    QuestionEvidenceState,
)
from financial_research.workflow.evidence_service_adapter import (
    EvidenceServiceProviderAdapter,
)

from tests.test_workflow_graph import (
    make_packet,
    make_request,
    make_scope,
)


class FakeService:
    def __init__(self, result, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def fetch_packets(
        self, request, execution_scope, research_run_id
    ):
        self.calls.append((
            request, execution_scope, research_run_id
        ))
        if self.error is not None:
            raise self.error
        return self.result


def valid_case():
    request = make_request()
    scope = make_scope().model_copy(
        update={"document_scope": ["DOC1"]}
    )
    packet = make_packet().model_copy(
        update={"execution_scope": scope}
    )
    return request, scope, packet


def collect(result, request=None, scope=None, error=None):
    baseline_request, baseline_scope, _ = valid_case()

    if request is None:
        request = baseline_request
    if scope is None:
        scope = baseline_scope

    service = FakeService(result, error=error)
    adapter = EvidenceServiceProviderAdapter(service)

    output = adapter.collect(
        request, scope, "RUN1"
    )
    return output, service


def test_valid_packet_crosses_adapter():
    request, scope, packet = valid_case()
    result, service = collect(
        [packet], request=request, scope=scope
    )

    assert len(result) == 1
    assert result[0] == packet
    assert service.calls == [(request, scope, "RUN1")]


def test_explicit_unavailable_packet_is_allowed():
    request, scope, packet = valid_case()
    unavailable = packet.model_copy(
        update={
            "evidence_items": [],
            "question_state": QuestionEvidenceState(
                question_id="Q1",
                availability=EvidenceAvailability.UNAVAILABLE,
                sufficiency=AnswerSufficiency.INSUFFICIENT,
            ),
        }
    )

    result, _ = collect(
        [unavailable], request=request, scope=scope
    )
    assert result[0].evidence_items == []
    assert (
        result[0].question_state.availability
        == EvidenceAvailability.UNAVAILABLE
    )


def test_missing_question_packet_fails():
    with pytest.raises(ValueError, match="one packet"):
        collect([])


def test_duplicate_question_packet_fails():
    _, _, packet = valid_case()
    with pytest.raises(ValueError, match="duplicate"):
        collect([packet, packet])


def test_unrequested_question_packet_fails():
    _, _, packet = valid_case()
    state = packet.question_state.model_copy(
        update={"question_id": "Q_OTHER"}
    )
    altered = packet.model_copy(
        update={
            "question_id": "Q_OTHER",
            "question_state": state,
        }
    )
    with pytest.raises(ValueError, match="unrequested"):
        collect([altered])


def test_wrong_research_run_fails():
    _, _, packet = valid_case()
    altered = packet.model_copy(
        update={"research_run_id": "OTHER"}
    )
    with pytest.raises(ValueError, match="research_run_id"):
        collect([altered])


def test_wrong_research_cutoff_fails():
    _, _, packet = valid_case()
    altered = packet.model_copy(
        update={
            "as_of": packet.as_of + timedelta(days=1)
        }
    )
    with pytest.raises(ValueError, match="as_of"):
        collect([altered])


def test_mismatched_execution_scope_fails():
    _, _, packet = valid_case()
    altered_scope = packet.execution_scope.model_copy(
        update={"corpus_version": "different"}
    )
    altered = packet.model_copy(
        update={"execution_scope": altered_scope}
    )
    with pytest.raises(ValueError, match="execution_scope"):
        collect([altered])


def test_unauthorized_document_fails():
    _, _, packet = valid_case()
    item = packet.evidence_items[0].model_copy(
        update={"document_id": "OUTSIDE_SCOPE"}
    )
    altered = packet.model_copy(
        update={"evidence_items": [item]}
    )

    with pytest.raises(ValueError, match="outside"):
        collect([altered])


def test_mutated_future_pit_is_revalidated():
    _, _, packet = valid_case()
    item = packet.evidence_items[0].model_copy(
        update={
            "pit_available_at":
                packet.as_of + timedelta(days=1)
        }
    )
    altered = packet.model_copy(
        update={"evidence_items": [item]}
    )

    with pytest.raises(ValidationError):
        collect([altered])


def test_service_failure_is_not_silently_insufficient():
    with pytest.raises(
        RuntimeError, match="source backend unavailable"
    ):
        collect(
            [],
            error=RuntimeError(
                "source backend unavailable"
            ),
        )


def test_non_packet_result_fails():
    with pytest.raises(TypeError, match="non-EvidencePacket"):
        collect([{"question_id": "Q1"}])


def test_non_list_result_fails():
    with pytest.raises(TypeError, match="return a list"):
        collect(None)
