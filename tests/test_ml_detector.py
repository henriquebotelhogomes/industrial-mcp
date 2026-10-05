"""Unit tests for Isolation Forest ML anomaly detector and latency benchmark."""

import time

from src.ml.anomaly_detector import OperationalAnomalyDetector
from src.ml.domain_rules import TelemetryEvent


def test_anomaly_detector_nominal_vs_outlier():
    detector = OperationalAnomalyDetector()

    nominal_event = TelemetryEvent(
        id_farm=1515,
        id_equip=14863,
        timestamp="2026-10-05 10:00:00",
        current_angle=45.0,
        direction="Forward",
        running_status="Running",
        water_mode="Wet",
        percent_timer=65.0,
        pressure_begin=3.2,
        pressure_end=2.8,
        flow_rate=185.0,
        nominal_pressure=3.2,
    )

    prev_event = TelemetryEvent(
        id_farm=1515,
        id_equip=14863,
        timestamp="2026-10-05 09:59:00",
        current_angle=44.2,
        direction="Forward",
        running_status="Running",
        water_mode="Wet",
        percent_timer=65.0,
        pressure_begin=3.2,
        pressure_end=2.8,
        flow_rate=185.0,
        nominal_pressure=3.2,
    )

    # Evaluate nominal event
    report = detector.evaluate(nominal_event, prev_event, elapsed_seconds=60.0)
    assert report.is_anomaly is False
    assert report.requires_operator_approval is False

    # Evaluate severely anomalous event (severe pressure drop while running wet)
    anomalous_event = nominal_event.model_copy(update={"pressure_begin": 0.25})
    report_anom = detector.evaluate(anomalous_event, prev_event, elapsed_seconds=60.0)
    assert report_anom.is_anomaly is True
    assert report_anom.requires_operator_approval is True
    assert "Bomba acionada" in " ".join(report_anom.anomaly_types)


def test_inference_latency_sub_10ms():
    detector = OperationalAnomalyDetector()
    event = TelemetryEvent(
        id_farm=1515,
        id_equip=14863,
        timestamp="2026-10-05 10:00:00",
        current_angle=90.0,
        percent_timer=70.0,
        pressure_begin=3.0,
    )

    # Warmup
    detector.evaluate(event, None)

    # Benchmark 50 iterations
    t0 = time.perf_counter()
    for _ in range(50):
        detector.evaluate(event, None)
    elapsed_ms = ((time.perf_counter() - t0) / 50) * 1000.0

    print(f"Mean inference latency: {elapsed_ms:.2f} ms")
    assert elapsed_ms < 10.0, f"Inference took {elapsed_ms:.2f} ms, expected < 10ms"
