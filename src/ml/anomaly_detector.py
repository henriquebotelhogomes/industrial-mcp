"""Isolation Forest-based operational anomaly detector for SCADA / PLC telemetry."""

import numpy as np
from sklearn.ensemble import IsolationForest

from src.core.logging import logger
from src.ml.domain_rules import AnomalyReport, DomainRuleEngine, TelemetryEvent


class OperationalAnomalyDetector:
    """Hybrid detector combining deterministic physics rules with Isolation Forest ML."""

    def __init__(self, contamination: float = 0.05):
        self.contamination = contamination
        self.model = IsolationForest(
            n_estimators=30,
            contamination=contamination,
            random_state=42,
            n_jobs=1,
        )
        self.is_fitted = False
        self._bootstrap_default_model()

    def _bootstrap_default_model(self) -> None:
        """Trains initial baseline model on synthetic + historical boundaries.

        Ensures zero-day readiness if training dataset has not been recomputed yet.
        Normal features:
          [pressure_begin, percent_timer, angular_speed, pressure_ratio, flow_rate]
        """
        np.random.seed(42)
        n_samples = 300

        # Normal operating distribution for standard center pivot
        pressure = np.random.normal(loc=3.2, scale=0.4, size=n_samples).clip(1.5, 5.0)
        percent_timer = np.random.uniform(30.0, 95.0, size=n_samples)
        # Typical speed: 0.1 to 2.5 deg / min depending on percent_timer
        angular_speed = (percent_timer / 100.0) * np.random.uniform(1.0, 2.5, size=n_samples)
        pressure_ratio = np.random.normal(loc=0.85, scale=0.05, size=n_samples).clip(0.65, 0.98)
        flow_rate = np.random.normal(loc=180.0, scale=15.0, size=n_samples).clip(120.0, 260.0)

        X_normal = np.column_stack([pressure, percent_timer, angular_speed, pressure_ratio, flow_rate])
        self.fit(X_normal)

    def fit(self, X: np.ndarray) -> None:
        """Fits the Isolation Forest on clean baseline telemetry."""
        self.model.fit(X)
        self.is_fitted = True
        logger.info("isolation_forest_trained", n_samples=X.shape[0], contamination=self.contamination)

    def extract_features(
        self,
        event: TelemetryEvent,
        prev_event: TelemetryEvent | None = None,
        elapsed_seconds: float = 60.0,
    ) -> tuple[np.ndarray, float]:
        """Extracts numerical features from telemetry event."""
        if prev_event and elapsed_seconds > 0:
            disp = abs(
                DomainRuleEngine.calculate_angular_displacement(
                    prev_event.current_angle,
                    event.current_angle,
                    event.direction,
                )
            )
            angular_speed = (disp / elapsed_seconds) * 60.0
        else:
            angular_speed = (event.percent_timer / 100.0) * 1.5

        p_begin = max(0.0, event.pressure_begin)
        p_ratio = (event.pressure_end / p_begin) if p_begin > 0.1 else 0.0
        flow = event.flow_rate

        features = np.array([[p_begin, event.percent_timer, angular_speed, p_ratio, flow]], dtype=np.float64)
        return features, angular_speed

    def evaluate(
        self,
        event: TelemetryEvent,
        prev_event: TelemetryEvent | None = None,
        elapsed_seconds: float = 60.0,
    ) -> AnomalyReport:
        """Evaluates event against both deterministic physics rules and statistical ML."""
        anomalies: list[str] = []
        details: dict[str, float | str] = {}
        requires_hitl = False

        # 1. Deterministic Domain Rule: Pump vs Pressure
        is_pump_anomaly, pump_msg = DomainRuleEngine.validate_pump_pressure_congruence(
            water_mode=event.water_mode,
            pressure_begin=event.pressure_begin,
            nominal_pressure=event.nominal_pressure,
        )
        if is_pump_anomaly and pump_msg:
            anomalies.append(pump_msg)
            requires_hitl = True

        # 2. Deterministic Domain Rule: Encoder Angular Jump
        if prev_event:
            is_jump, jump_msg = DomainRuleEngine.detect_encoder_jump(
                previous_angle=prev_event.current_angle,
                current_angle=event.current_angle,
                elapsed_seconds=elapsed_seconds,
                direction=event.direction,
            )
            if is_jump and jump_msg:
                anomalies.append(jump_msg)
                requires_hitl = True

        # 3. Machine Learning (Isolation Forest)
        features, angular_speed = self.extract_features(event, prev_event, elapsed_seconds)
        raw_score = float(self.model.decision_function(features)[0])
        # In IsolationForest, predict == -1 if decision_function < 0. Avoids duplicate tree traversal.
        prediction = -1 if raw_score < 0 else 1

        details["decision_score"] = round(raw_score, 4)
        details["angular_speed_deg_min"] = round(angular_speed, 2)

        # Confidence: normalize raw score to [0, 1] range for anomaly likelihood
        # Typically raw_score is in [-0.5, 0.5]
        confidence = float(np.clip(1.0 - (raw_score + 0.3) / 0.6, 0.0, 1.0))

        if prediction == -1 and event.running_status.lower() == "running":
            anomalies.append(
                f"Assinatura estatística anômala detectada por Isolation Forest (score: {raw_score:.3f})."
            )

        is_anomaly = len(anomalies) > 0
        recommended_action = None
        if is_anomaly:
            if "Bomba acionada" in " ".join(anomalies):
                recommended_action = "PARADA DE EMERGÊNCIA DA BOMBA (Intervenção SCADA recomendada - HITL)"
            elif "Salto anômalo" in " ".join(anomalies):
                recommended_action = "DESLIGAR PIVÔ POR SEGURANÇA ESTRUTURAL (Risco de desalinhamento de vão)"
            else:
                recommended_action = "SOLICITAR REINSPEÇÃO DE TELEMETRIA AO AGENTE DE DIAGNÓSTICO"

        return AnomalyReport(
            is_anomaly=is_anomaly,
            anomaly_types=anomalies,
            confidence_score=round(confidence, 3),
            details=details,
            recommended_action=recommended_action,
            requires_operator_approval=requires_hitl,
        )


detector = OperationalAnomalyDetector()
