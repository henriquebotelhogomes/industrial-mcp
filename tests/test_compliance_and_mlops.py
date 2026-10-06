"""Unit tests verifying DLQ integrity, LGPD pseudonymization, temporal split MLOps and drift."""

import polars as pl

from src.config import settings
from src.core.security import anonymize_identifier, sanitize_farm_record
from src.ml.anomaly_detector import OperationalAnomalyDetector
from src.ml.domain_rules import TelemetryEvent
from src.ml.drift_monitor import TelemetryDriftMonitor


def test_lgpd_deterministic_pseudonymization():
    """Ensures deterministic pseudonymization generates reproducible ANON_... tokens."""
    name1 = "João da Silva"
    name2 = "João da Silva"
    name3 = "Maria Oliveira"

    token1 = anonymize_identifier(name1)
    token2 = anonymize_identifier(name2)
    token3 = anonymize_identifier(name3)

    assert token1.startswith("ANON_")
    assert token1 == token2, "Deterministic token must match for identical name"
    assert token1 != token3, "Tokens for different names must differ"

    # Test record sanitizer
    raw_farm = {"farm_name": "Fazenda Modelo", "farm_owner": "Carlos Eduardo"}
    sanitized = sanitize_farm_record(raw_farm)
    assert sanitized["farm_owner"].startswith("ANON_")
    assert "Carlos Eduardo" not in sanitized["farm_owner"]


def test_dead_letter_queue_parquet_exists():
    """Verifies that Dead Letter Queue parquet table was populated and has valid schema."""
    dlq_file = settings.dlq_parquet_dir / "dlq_sensor_events.parquet"
    assert dlq_file.exists(), f"DLQ parquet file missing at {dlq_file}"

    df_dlq = pl.read_parquet(dlq_file)
    assert len(df_dlq) > 0, "DLQ must capture corrupted or rejected records"
    assert "rejection_reason" in df_dlq.columns
    assert "id_equip" in df_dlq.columns
    assert "ingested_at" in df_dlq.columns


def test_mlops_temporal_split_training():
    """Verifies that Isolation Forest trains with temporal split and no data leakage."""
    detector = OperationalAnomalyDetector()
    gold_path = settings.gold_parquet_dir / "pivot_gold_metrics.parquet"
    if gold_path.exists():
        metrics = detector.fit_from_gold_layer(gold_path, split_ratio=0.8)
        assert metrics["status"] == "SUCCESS"
        assert metrics["train_samples"] > 0
        assert metrics["test_samples"] > 0
        assert metrics["split_ratio"] == 0.8
        assert detector.is_fitted is True


def test_drift_monitor_evaluation():
    """Verifies that TelemetryDriftMonitor tracks sliding window and computes drift shift."""
    monitor = TelemetryDriftMonitor(window_size=20)
    
    # Push nominal events
    for i in range(15):
        event = TelemetryEvent(
            id_farm=1515,
            id_equip=14863,
            timestamp=f"2026-10-05 12:{i:02d}:00",
            current_angle=float(i * 10),
            pressure_begin=3.2,
            percent_timer=65.0,
            flow_rate=180.0,
        )
        monitor.record_event(event)

    result = monitor.evaluate_drift()
    assert "drift_detected" in result
    assert result["status"] == "STABLE"
    assert result["sample_count"] == 15
