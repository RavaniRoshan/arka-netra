from __future__ import annotations

import pandas as pd
from typing import Optional

from solaris.alerts.schema import (
    AlertRecord,
    ALERT_STATES,
    create_alert_record,
    now_utc,
)


class AlertStateMachine:
    """
    State machine for alert lifecycle management.
    States: NORMAL → WATCH → WARNING → CRITICAL → RESOLVED
    Special: UNCERTAIN (for stale/missing data)
    """

    def __init__(
        self,
        watch_probability: float = 0.35,
        warning_probability: float = 0.55,
        critical_probability: float = 0.78,
        anomaly_watch: float = 45.0,
        anomaly_supporting_warning: float = 70.0,
        uncertain_confidence_width: float = 0.3,
    ):
        self.watch_probability = watch_probability
        self.warning_probability = warning_probability
        self.critical_probability = critical_probability
        self.anomaly_watch = anomaly_watch
        self.anomaly_supporting_warning = anomaly_supporting_warning
        self.uncertain_confidence_width = uncertain_confidence_width

    def compute_state(
        self,
        flare_probability: float,
        anomaly_index: float,
        confidence_low: float,
        confidence_high: float,
        is_stale: bool = False,
    ) -> str:
        """Compute alert state from prediction metrics."""
        if is_stale:
            return "UNCERTAIN"

        confidence_width = confidence_high - confidence_low
        if confidence_width > self.uncertain_confidence_width:
            if flare_probability < self.warning_probability:
                return "UNCERTAIN"

        p = float(flare_probability)
        a = float(anomaly_index)

        if p >= self.critical_probability or (p >= self.warning_probability + 0.10 and a >= self.anomaly_supporting_warning):
            return "CRITICAL"
        if p >= self.warning_probability:
            return "WARNING"
        if p >= self.watch_probability or a >= self.anomaly_watch:
            return "WATCH"
        return "NORMAL"

    def compute_transition(
        self,
        current_state: str,
        new_state: str,
    ) -> str:
        """Determine transition string."""
        if current_state == new_state:
            return f"No change ({new_state})"
        return f"{current_state} → {new_state}"

    def generate_alerts(
        self,
        predictions: pd.DataFrame,
        config_hash: str,
        data_hash: str,
    ) -> list[AlertRecord]:
        """Generate alert records for all prediction rows."""
        alerts = []
        current_state = "NORMAL"

        for _, row in predictions.iterrows():
            new_state = self.compute_state(
                flare_probability=row.get("flare_probability", 0.0),
                anomaly_index=row.get("anomaly_index", 0.0),
                confidence_low=row.get("confidence_low", 0.0),
                confidence_high=row.get("confidence_high", 1.0),
                is_stale=row.get("is_stale", False) if "is_stale" in row else False,
            )

            transition = self.compute_transition(current_state, new_state)

            alert = create_alert_record(
                state=new_state,
                transition_from=transition,
                flare_probability=row.get("flare_probability", 0.0),
                anomaly_index=row.get("anomaly_index", 0.0),
                confidence_low=row.get("confidence_low", 0.0),
                confidence_high=row.get("confidence_high", 1.0),
                scenario=row.get("scenario", "unknown"),
                data_source=row.get("data_mode", "unknown"),
                model_version=row.get("model_version", "unknown"),
                config_hash=config_hash,
                data_hash=data_hash,
            )
            alerts.append(alert)
            current_state = new_state

        return alerts

    def state_summary(self, predictions: pd.DataFrame, is_stale: bool = False) -> dict:
        """Get summary of states in predictions."""
        states = []
        for _, row in predictions.iterrows():
            state = self.compute_state(
                flare_probability=row.get("flare_probability", 0.0),
                anomaly_index=row.get("anomaly_index", 0.0),
                confidence_low=row.get("confidence_low", 0.0),
                confidence_high=row.get("confidence_high", 1.0),
                is_stale=is_stale,
            )
            states.append(state)
        return pd.Series(states).value_counts().to_dict()