"""Domain rules and physics-based sanity checks for Center Pivot and sensor telemetry.

Transposed and hardened from legacy production collector logic (Readings_Irrigation.php,
Readings_SoilMoisture.php, Readings_Weather.php).
"""

from typing import Any

from pydantic import BaseModel, Field


class TelemetryEvent(BaseModel):
    """Pydantic model representing an ingested industrial telemetry packet."""

    id_farm: int
    id_equip: int
    farm_name: str | None = None
    pivot_name: str | None = None
    timestamp: str
    current_angle: float = Field(ge=0.0, le=360.0, description="Pivot angular position (0-360 deg)")
    direction: str = Field(default="Forward", description="Forward or Reverse")
    running_status: str = Field(default="Stopped", description="Running or Stopped")
    water_mode: str = Field(default="Dry", description="Wet or Dry")
    percent_timer: float = Field(ge=0.0, le=100.0, description="Timer percentage (0-100%)")
    pressure_begin: float = Field(default=0.0, ge=0.0, description="Base/pivot head pressure in bar or mca")
    pressure_end: float = Field(default=0.0, ge=0.0, description="End tower pressure")
    flow_rate: float = Field(default=0.0, ge=0.0, description="Flow rate (m3/h or gpm)")
    nominal_pressure: float | None = Field(default=None, description="Nominal service pressure from equipment registry")
    pivot_radius: float | None = Field(default=None, description="Pivot radius in meters")


class AnomalyReport(BaseModel):
    """Result of domain rule and ML checks on a telemetry event."""

    is_anomaly: bool
    anomaly_types: list[str] = Field(default_factory=list)
    confidence_score: float = 0.0
    details: dict[str, Any] = Field(default_factory=dict)
    recommended_action: str | None = None
    requires_operator_approval: bool = False


class DomainRuleEngine:
    """Deterministic, physics-based validator for industrial telemetry."""

    MIN_OPERATIONAL_PRESSURE_BAR: float = 1.2
    MAX_ANGULAR_DELTA_PER_MINUTE: float = 6.0  # Physical speed limit: 360 deg in ~60 min min = 6 deg/min

    @classmethod
    def validate_pump_pressure_congruence(
        cls,
        water_mode: str,
        pressure_begin: float,
        nominal_pressure: float | None = None,
    ) -> tuple[bool, str | None]:
        """Cross-checks pump/water mode against physical pressure line readings.

        Mitigates false positives from legacy systems:
        If water_mode is 'Wet' (pump commanded ON), but pressure is below min threshold,
        indicates either pump cavitation, pipe burst, dry well, or false control feedback.
        """
        threshold = cls.MIN_OPERATIONAL_PRESSURE_BAR
        if nominal_pressure and nominal_pressure > 0:
            threshold = max(0.8, nominal_pressure * 0.4)

        if water_mode.lower() == "wet" and pressure_begin < threshold:
            return True, f"Bomba acionada (Wet), mas pressão medida ({pressure_begin:.2f}) abaixo do limiar operacional ({threshold:.2f}). Risco de cavitação ou rompimento de adutora."

        return False, None

    @classmethod
    def calculate_angular_displacement(
        cls,
        previous_angle: float,
        current_angle: float,
        direction: str = "Forward",
    ) -> float:
        """Calculates true physical displacement handling the 360 -> 0 zero-crossing boundary.

        Based on Readings_Irrigation.php angle sub-slicing logic.
        """
        raw_diff = current_angle - previous_angle

        if direction.lower() == "forward":
            # Moving clockwise (increasing angle): 359 -> 2 = +3 deg
            if raw_diff < -180.0:
                return raw_diff + 360.0
            elif raw_diff > 180.0:
                # Potential backward jump or severe glitch
                return raw_diff - 360.0
            return raw_diff
        else:
            # Moving counter-clockwise / Reverse (decreasing angle): 2 -> 359 = -3 deg
            if raw_diff > 180.0:
                return raw_diff - 360.0
            elif raw_diff < -180.0:
                return raw_diff + 360.0
            return raw_diff

    @classmethod
    def detect_encoder_jump(
        cls,
        previous_angle: float,
        current_angle: float,
        elapsed_seconds: float,
        direction: str = "Forward",
    ) -> tuple[bool, str | None]:
        """Detects physical impossibility: encoder telemetry jumping faster than physical gear limits."""
        if elapsed_seconds <= 0:
            return False, None

        displacement = abs(cls.calculate_angular_displacement(previous_angle, current_angle, direction))
        displacement_per_minute = (displacement / elapsed_seconds) * 60.0

        if displacement_per_minute > cls.MAX_ANGULAR_DELTA_PER_MINUTE:
            return True, f"Salto anômalo no encoder angular: {displacement:.2f}° em {elapsed_seconds:.1f}s ({displacement_per_minute:.1f}°/min > limite de {cls.MAX_ANGULAR_DELTA_PER_MINUTE}°/min)."

        return False, None

    @classmethod
    def fahrenheit_to_celsius(cls, tf: float) -> float:
        """Converts Fahrenheit to Celsius per Readings_SoilMoisture.php."""
        return (tf - 32.0) / 1.8

    @classmethod
    def mph_to_ms(cls, mph: float) -> float:
        """Converts wind speed from mph to m/s per Readings_Weather.php."""
        return mph * 0.44704
