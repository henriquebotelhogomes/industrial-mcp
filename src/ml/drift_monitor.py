"""Data Drift and Signal Integrity Monitor for SCADA / PLC Telemetry."""

from typing import Any

import numpy as np
import polars as pl

from src.config import settings
from src.core.logging import logger
from src.ml.domain_rules import TelemetryEvent


class TelemetryDriftMonitor:
    """Monitors distribution drift and sensor degradation over streaming windows."""

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.baseline_stats: dict[str, dict[str, float]] = {}
        self.recent_buffer: list[TelemetryEvent] = []
        self._load_gold_baseline()

    def _load_gold_baseline(self) -> None:
        """Computes reference baseline distributions from Gold layer."""
        gold_path = settings.gold_parquet_dir / "pivot_gold_metrics.parquet"
        if not gold_path.exists():
            # Default fallback baseline
            self.baseline_stats = {
                "pressure_begin": {"mean": 3.2, "std": 0.4},
                "percent_timer": {"mean": 65.0, "std": 15.0},
                "flow_rate": {"mean": 180.0, "std": 20.0},
            }
            return

        try:
            df = pl.read_parquet(gold_path)
            # Only consider operating equipment with non-zero readings
            active_df = df.filter(pl.col("pressure_begin") > 0.5)
            if len(active_df) < 5:
                active_df = df

            p_vals = active_df["pressure_begin"].to_numpy()
            p_vals = np.where(p_vals > 10.0, p_vals / 10.0, p_vals)
            p_mean = float(np.mean(p_vals)) if len(p_vals) > 0 and np.mean(p_vals) > 0 else 3.2
            p_std = max(0.2, float(np.std(p_vals))) if len(p_vals) > 0 else 0.4

            pct_vals = active_df["percent_timer"].to_numpy()
            pct_mean = float(np.mean(pct_vals)) if len(pct_vals) > 0 and np.mean(pct_vals) > 0 else 65.0
            pct_std = max(5.0, float(np.std(pct_vals))) if len(pct_vals) > 0 else 15.0

            # Flow rate: check if active telemetry has positive flow, otherwise use nominal flow
            flow_series = active_df["flow_rate"].filter(active_df["flow_rate"] > 0)
            if len(flow_series) >= 5:
                flow_vals = flow_series.to_numpy()
            elif "nominal_flow" in df.columns:
                flow_vals = df["nominal_flow"].drop_nulls().to_numpy()
            else:
                flow_vals = np.array([180.0])

            flow_mean = float(np.mean(flow_vals)) if len(flow_vals) > 0 else 180.0
            flow_std = max(10.0, float(np.std(flow_vals))) if len(flow_vals) > 0 else 20.0

            self.baseline_stats = {
                "pressure_begin": {"mean": p_mean, "std": p_std},
                "percent_timer": {"mean": pct_mean, "std": pct_std},
                "flow_rate": {"mean": flow_mean, "std": flow_std},
            }
            logger.info("drift_monitor_baseline_loaded", **self.baseline_stats)
        except Exception as e:
            logger.warn("drift_monitor_fallback_used", error=str(e))
            self.baseline_stats = {
                "pressure_begin": {"mean": 3.2, "std": 0.4},
                "percent_timer": {"mean": 65.0, "std": 15.0},
                "flow_rate": {"mean": 180.0, "std": 20.0},
            }

    def record_event(self, event: TelemetryEvent) -> None:
        """Appends event to sliding window buffer."""
        self.recent_buffer.append(event)
        if len(self.recent_buffer) > self.window_size:
            self.recent_buffer.pop(0)

    def evaluate_drift(self) -> dict[str, Any]:
        """Calculates normalized Z-score shift across recent sliding window."""
        if len(self.recent_buffer) < 10:
            return {"drift_detected": False, "status": "INSUFFICIENT_DATA", "sample_count": len(self.recent_buffer)}

        pressures = [e.pressure_begin for e in self.recent_buffer if e.pressure_begin > 0.0]
        flows = [e.flow_rate for e in self.recent_buffer if e.flow_rate > 0.0]
        timers = [e.percent_timer for e in self.recent_buffer]

        shifts: dict[str, float] = {}
        drift_flags: list[str] = []

        if pressures and "pressure_begin" in self.baseline_stats:
            p_mean = float(np.mean(pressures))
            base = self.baseline_stats["pressure_begin"]
            z_shift = abs(p_mean - base["mean"]) / base["std"]
            shifts["pressure_z_shift"] = round(z_shift, 2)
            if z_shift > 3.0:
                drift_flags.append(f"Pressure baseline shift (Z={z_shift:.1f} > 3.0)")

        if flows and "flow_rate" in self.baseline_stats:
            f_mean = float(np.mean(flows))
            base = self.baseline_stats["flow_rate"]
            z_shift = abs(f_mean - base["mean"]) / base["std"]
            shifts["flow_z_shift"] = round(z_shift, 2)
            if z_shift > 3.0:
                drift_flags.append(f"Flow baseline shift (Z={z_shift:.1f} > 3.0)")

        if timers and "percent_timer" in self.baseline_stats:
            t_mean = float(np.mean(timers))
            base = self.baseline_stats["percent_timer"]
            z_shift = abs(t_mean - base["mean"]) / base["std"]
            shifts["timer_z_shift"] = round(z_shift, 2)
            if z_shift > 3.0:
                drift_flags.append(f"Timer baseline shift (Z={z_shift:.1f} > 3.0)")

        is_drift = len(drift_flags) > 0
        return {
            "drift_detected": is_drift,
            "status": "DRIFT_ALERT" if is_drift else "STABLE",
            "sample_count": len(self.recent_buffer),
            "shifts": shifts,
            "warnings": drift_flags,
        }


drift_monitor = TelemetryDriftMonitor()
