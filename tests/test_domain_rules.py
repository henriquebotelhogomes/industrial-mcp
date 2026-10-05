"""Unit tests for domain physics rules and zero-crossing arithmetic."""

from src.ml.domain_rules import DomainRuleEngine


def test_zero_crossing_displacement_forward():
    # Pivot moving Forward crosses from 359° to 2° -> displacement should be +3.0°
    disp = DomainRuleEngine.calculate_angular_displacement(359.0, 2.0, direction="Forward")
    assert round(disp, 1) == 3.0


def test_zero_crossing_displacement_reverse():
    # Pivot moving Reverse crosses from 1° to 358° -> displacement should be -3.0°
    disp = DomainRuleEngine.calculate_angular_displacement(1.0, 358.0, direction="Reverse")
    assert round(disp, 1) == -3.0


def test_encoder_jump_detection():
    # A jump of 45 degrees in 10 seconds is physically impossible for a center pivot (> 6 deg/min)
    is_jump, msg = DomainRuleEngine.detect_encoder_jump(
        previous_angle=10.0,
        current_angle=55.0,
        elapsed_seconds=10.0,
        direction="Forward",
    )
    assert is_jump is True
    assert "Salto anômalo" in msg


def test_pump_pressure_congruence():
    # Wet mode with 0.3 bar pressure -> anomaly (cavitation or burst)
    is_anomaly, msg = DomainRuleEngine.validate_pump_pressure_congruence(
        water_mode="Wet",
        pressure_begin=0.3,
        nominal_pressure=3.2,
    )
    assert is_anomaly is True
    assert "Bomba acionada" in msg

    # Wet mode with 3.1 bar pressure -> nominal
    is_anomaly_normal, _ = DomainRuleEngine.validate_pump_pressure_congruence(
        water_mode="Wet",
        pressure_begin=3.1,
        nominal_pressure=3.2,
    )
    assert is_anomaly_normal is False

    # Machine stopped -> 0 pressure is nominal and must NOT trigger anomaly
    is_anomaly_stopped, _ = DomainRuleEngine.validate_pump_pressure_congruence(
        water_mode="Wet",
        pressure_begin=0.0,
        nominal_pressure=3.2,
        running_status="Stopped",
    )
    assert is_anomaly_stopped is False


def test_unit_conversions():
    # 77 Fahrenheit = 25 Celsius
    celsius = DomainRuleEngine.fahrenheit_to_celsius(77.0)
    assert round(celsius, 1) == 25.0

    # 10 mph ~ 4.47 m/s
    ms = DomainRuleEngine.mph_to_ms(10.0)
    assert round(ms, 2) == 4.47
