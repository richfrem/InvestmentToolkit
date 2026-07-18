"""Dataclasses mirroring the shared intelligence read-model tables.

These are plain data containers only — no persistence or validation
behavior lives here. Reads/writes against the tables they mirror belong
in ``event_repository.py`` and ``instrument_repository.py`` (ADR-028: one
data layer, one file per table, per responsibility).
"""

from dataclasses import dataclass


@dataclass
class Instrument:
    """Mirrors the ``instrument`` table."""

    instrument_id: str
    ticker: str
    exchange: str | None
    name: str
    active_from: str | None
    active_to: str | None


@dataclass
class IntelligenceEvent:
    """Mirrors the ``intelligence_event`` table."""

    event_id: str
    event_sequence: int
    instrument_id: str | None
    event_type: str
    effective_at: str
    ingested_at: str
    status: str
    title: str | None
    body_markdown: str | None
    content_hash: str
    observed_at: str | None = None
    source_id: str | None = None
    confidence_score: float | None = None
    payload_json: str | None = None
    supersedes_event_id: str | None = None
    idempotency_key: str | None = None
