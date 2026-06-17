from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


ALERT_STATES = {"NORMAL", "WATCH", "WARNING", "CRITICAL", "RESOLVED", "UNCERTAIN"}


@dataclass
class AlertRecord:
    alert_id: str
    timestamp: str
    state: str
    transition_from: str
    flare_probability: float
    anomaly_index: float
    confidence_low: float
    confidence_high: float
    scenario: str
    data_source: str
    model_version: str
    config_hash: str
    data_hash: str
    operator_notes: str = ""
    resolution_time: str = ""
    resolution_reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> AlertRecord:
        return cls(**d)

    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict(), indent=2)


def create_alert_id() -> str:
    return str(uuid.uuid4())


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_alert_record(
    state: str,
    transition_from: str,
    flare_probability: float,
    anomaly_index: float,
    confidence_low: float,
    confidence_high: float,
    scenario: str,
    data_source: str,
    model_version: str,
    config_hash: str,
    data_hash: str,
    operator_notes: str = "",
) -> AlertRecord:
    return AlertRecord(
        alert_id=create_alert_id(),
        timestamp=now_utc(),
        state=state,
        transition_from=transition_from,
        flare_probability=float(flare_probability),
        anomaly_index=float(anomaly_index),
        confidence_low=float(confidence_low),
        confidence_high=float(confidence_high),
        scenario=str(scenario),
        data_source=str(data_source),
        model_version=str(model_version),
        config_hash=str(config_hash),
        data_hash=str(data_hash),
        operator_notes=operator_notes,
    )