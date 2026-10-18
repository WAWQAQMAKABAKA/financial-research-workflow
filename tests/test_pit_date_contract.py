"""Deterministic FRW date-level PIT contract tests.

Synthetic timestamps only; no source-backed Provider is exercised.
"""

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from financial_research.contracts import (
    AnswerSufficiency,
    EvidenceAvailability,
    EvidenceItem,
    EvidencePacket,
    EvidenceRelationship,
    QuestionEvidenceState,
    ResolvedExecutionScope,
)

SH = ZoneInfo("Asia/Shanghai")
D = date(2026, 8, 28)
GATE = datetime(2026, 8, 29, 0, 0, tzinfo=SH)


def make_item(**overrides):
    values = {
        "evidence_id": "E1",
        "target_claim_id": "C1",
        "target_proposition": "Synthetic proposition",
        "source_id": "CNINFO_TEST",
        "document_id": "SYNTHETIC_DOC",
        "source_type": "official_report",
        "published_on": D,
        "published_at": None,
        "pit_available_at": GATE,
        "observed_at": None,
        "source_version_id": None,
        "pit_time_basis": "date_end_conservative",
        "canonical_location": "synthetic:0-20",
        "relevant_span": "SYNTHETIC_CONTEXT_NOT_REAL_EVIDENCE",
        "relationship": EvidenceRelationship.CONTEXT_ONLY,
        "provenance": {
            "publication_precision": "date",
            "pit_policy": "shanghai_next_calendar_day",
        },
    }
    values.update(overrides)
    return EvidenceItem(**values)


def make_packet(item, as_of):
    scope = ResolvedExecutionScope(
        authorized_corpus="synthetic",
        document_scope=["SYNTHETIC_DOC"],
        corpus_version="test",
        source_permissions=["read"],
        resolved_at=datetime(
            2026, 8, 28, 0, 0, tzinfo=SH
        ),
    )

    return EvidencePacket(
        research_run_id="TEST_RUN",
        question_id="Q1",
        as_of=as_of,
        execution_scope=scope,
        evidence_items=[item],
        question_state=QuestionEvidenceState(
            question_id="Q1",
            availability=EvidenceAvailability.PARTIAL,
            sufficiency=AnswerSufficiency.INSUFFICIENT,
        ),
    )


def test_date_level_gate_opens_at_next_midnight():
    item = make_item()
    assert item.published_on == D
    assert item.published_at is None
    assert item.pit_available_at == GATE
    assert item.pit_time_basis == "date_end_conservative"
    assert item.source_version_id is None


@pytest.mark.parametrize("hour,minute,second", [
    (0, 0, 0),
    (12, 0, 0),
    (23, 59, 59),
])
def test_date_level_rejects_announcement_day(
    hour, minute, second
):
    early = datetime(
        2026, 8, 28,
        hour, minute, second,
        tzinfo=SH,
    )
    with pytest.raises(ValidationError):
        make_item(pit_available_at=early)


def test_date_only_requires_explicit_time_basis():
    with pytest.raises(ValidationError):
        make_item(pit_time_basis="legacy_unclassified")


def test_date_only_cannot_claim_verified_timestamp_basis():
    with pytest.raises(ValidationError):
        make_item(pit_time_basis="verified_timestamp")


def test_missing_publication_identity_rejected():
    with pytest.raises(ValidationError):
        make_item(published_on=None)


def test_verified_timestamp_cannot_have_earlier_pit():
    published = datetime(
        2026, 8, 28, 12, 0, tzinfo=SH
    )
    earlier = datetime(
        2026, 8, 28, 11, 0, tzinfo=SH
    )
    with pytest.raises(ValidationError):
        make_item(
            published_at=published,
            pit_available_at=earlier,
            pit_time_basis="verified_timestamp",
        )


def test_observation_timestamp_must_be_timezone_aware():
    with pytest.raises(ValidationError):
        make_item(
            observed_at=datetime(2026, 10, 4, 7, 22)
        )


def test_packet_rejects_before_date_gate():
    with pytest.raises(ValidationError):
        make_packet(
            make_item(),
            datetime(2026, 8, 28, 23, 59, tzinfo=SH),
        )


def test_packet_at_gate_accepts_retrospective_evidence():
    observed = datetime(
        2026, 10, 4, 7, 22, tzinfo=timezone.utc
    )

    item = make_item(observed_at=observed)
    packet = make_packet(item, GATE)

    assert packet.evidence_items[0].observed_at == observed
    assert packet.evidence_items[0].published_at is None

    # This demonstrates retrospective contract transport,
    # not proof of live availability at the historical cutoff.
    assert observed > packet.as_of


def test_legacy_timestamp_keeps_unclassified_basis():
    published = datetime(
        2026, 8, 28, 12, 0, tzinfo=SH
    )

    item = make_item(
        published_on=None,
        published_at=published,
        pit_available_at=published,
        pit_time_basis="legacy_unclassified",
    )

    assert item.published_at == published
    assert item.pit_time_basis == "legacy_unclassified"
