"""LGPD Data Privacy and Deterministic Pseudonymization module."""

import hashlib
from typing import Any

# Salt for deterministic pseudonymization (can be overridden via environment)
PSEUDO_SALT = "INDUSTRIAL_TELEMETRY_LGPD_2026"


def anonymize_identifier(value: str | None, prefix: str = "ANON_") -> str:
    """Deterministically anonymizes personal identifiers (PII) to meet LGPD standards.
    
    Produces consistent pseudonyms (e.g., ANON_B84E3A19) preserving entity linkage
    without exposing raw personal information to logs, prompts, or public APIs.
    """
    if not value or not str(value).strip():
        return f"{prefix}UNKNOWN"
    
    clean_val = str(value).strip().lower()
    hasher = hashlib.sha256(f"{PSEUDO_SALT}:{clean_val}".encode("utf-8"))
    token = hasher.hexdigest()[:8].upper()
    return f"{prefix}{token}"


def sanitize_farm_record(record: dict[str, Any]) -> dict[str, Any]:
    """Applies deterministic pseudonymization to owner and personal fields in a farm record."""
    sanitized = record.copy()
    if "farm_owner" in sanitized and sanitized["farm_owner"]:
        sanitized["farm_owner"] = anonymize_identifier(sanitized["farm_owner"])
    if "Proprietario" in sanitized and sanitized["Proprietario"]:
        sanitized["Proprietario"] = anonymize_identifier(sanitized["Proprietario"])
    return sanitized
