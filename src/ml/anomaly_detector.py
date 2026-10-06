from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
from sklearn.ensemble import IsolationForest

from src.config import settings
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
        gold_file = settings.gold_parquet_dir / "pivot_gold_metrics.parquet"
        if gold_file.exists():
            self.fit_from_gold_layer(gold_file)
        else:
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

    def fit_from_gold_layer(self, gold_path: Path | None = None, split_ratio: float = 0.8) -> dict[str, Any]:
        """Trains Isolation Forest on historical Gold telemetry with strict temporal split.

        Enforces strict temporal split (no future data leakage) by sorting chronologically
        and training only on historical window T < T_cutoff, evaluating on T >= T_cutoff.
        """
        path = gold_path or (settings.gold_parquet_dir / "pivot_gold_metrics.parquet")
        if not path.exists():
            logger.warn("gold_parquet_not_found_fallback_to_bootstrap", path=str(path))
            self._bootstrap_default_model()
            return {"status": "FALLBACK_BOOTSTRAP", "reason": "file_not_found"}

        try:
            df = pl.read_parquet(path)
            if df.is_empty():
                self._bootstrap_default_model()
                return {"status": "FALLBACK_BOOTSTRAP", "reason": "empty_dataframe"}

            # Sort strictly chronologically by timestamp
            df_sorted = df.sort("timestamp")
            n_total = len(df_sorted)
            cutoff_idx = int(n_total * split_ratio)

            train_df = df_sorted[:cutoff_idx]
            test_df = df_sorted[cutoff_idx:]

            # Filter nominal training records (running without flagged pump/line anomalies)
            nominal_train = train_df.filter(
                (pl.col("running_status") == "Running")
                & (~pl.col("flag_pressure_anomaly"))
            )

            # Extract real empirical samples from training split
            if len(nominal_train) > 0:
                p_begin = nominal_train["pressure_begin"].to_numpy().clip(0.0, 10.0)
                p_begin = np.where(p_begin > 10.0, p_begin / 10.0, p_begin)
                p_end = nominal_train["pressure_end"].to_numpy().clip(0.0, 10.0)
                percent = nominal_train["percent_timer"].to_numpy().clip(0.0, 100.0)
                ang_speed = (percent / 100.0) * 1.5
                p_ratio = np.where(p_begin > 0.1, p_end / np.maximum(p_begin, 0.1), 0.0)
                flow = nominal_train["flow_rate"].to_numpy().clip(0.0, 500.0)
                X_real = np.column_stack([p_begin, percent, ang_speed, p_ratio, flow])
            else:
                X_real = np.empty((0, 5))

            # Calibrate operational baseline anchored strictly on train_df equipment metadata
            np.random.seed(42)
            n_aug = 200
            nom_p_vals = train_df["nominal_pressure"].drop_nulls().to_numpy()
            nom_p = float(np.mean(nom_p_vals)) if len(nom_p_vals) > 0 else 3.2
            if nom_p > 10.0:
                nom_p = nom_p / 10.0

            nom_flow_vals = train_df["nominal_flow"].drop_nulls().to_numpy()
            nom_flow = float(np.mean(nom_flow_vals)) if len(nom_flow_vals) > 0 else 180.0

            aug_pressure = np.random.normal(loc=nom_p, scale=0.3, size=n_aug).clip(1.5, 5.0)
            aug_percent = np.random.uniform(30.0, 95.0, size=n_aug)
            aug_speed = (aug_percent / 100.0) * np.random.uniform(1.0, 2.5, size=n_aug)
            aug_ratio = np.random.normal(loc=0.85, scale=0.05, size=n_aug).clip(0.65, 0.98)
            aug_flow = np.random.normal(loc=nom_flow, scale=15.0, size=n_aug).clip(100.0, 300.0)

            X_aug = np.column_stack([aug_pressure, aug_percent, aug_speed, aug_ratio, aug_flow])
            X_train = np.vstack([X_real, X_aug]) if len(X_real) > 0 else X_aug
            self.fit(X_train)

            # Evaluate on out-of-time test set (strict temporal validation without leakage)
            p_test = test_df["pressure_begin"].to_numpy().clip(0.0, 10.0)
            p_test = np.where(p_test > 10.0, p_test / 10.0, p_test)
            p_test_end = test_df["pressure_end"].to_numpy().clip(0.0, 10.0)
            pct_test = test_df["percent_timer"].to_numpy().clip(0.0, 100.0)
            speed_test = (pct_test / 100.0) * 1.5
            ratio_test = np.where(p_test > 0.1, p_test_end / np.maximum(p_test, 0.1), 0.0)
            flow_test = test_df["flow_rate"].to_numpy().clip(0.0, 500.0)

            X_test = np.column_stack([p_test, pct_test, speed_test, ratio_test, flow_test])
            preds = self.model.predict(X_test)
            anomaly_rate = float(np.mean(preds == -1))

            metrics = {
                "status": "SUCCESS",
                "total_records": n_total,
                "train_samples": len(X_train),
                "test_samples": len(X_test),
                "test_anomaly_rate": round(anomaly_rate, 4),
                "split_ratio": split_ratio,
            }
            logger.info("temporal_split_training_completed", **metrics)
            return metrics
        except Exception as e:
            logger.error("error_training_from_gold_fallback", error=str(e))
            self._bootstrap_default_model()
            return {"status": "FALLBACK_BOOTSTRAP", "error": str(e)}

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
        if p_begin > 10.0:
            p_begin = p_begin / 10.0
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
            running_status=event.running_status,
        )
        if is_pump_anomaly and pump_msg:
            anomalies.append(pump_msg)
            requires_hitl = True

        # 2. Deterministic Domain Rule: Encoder Angular Jump
        if prev_event and prev_event.id_equip == event.id_equip and event.running_status.lower() == "running":
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
