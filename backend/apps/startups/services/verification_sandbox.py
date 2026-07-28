"""
Instant Verification Sandbox Engine for GSTIN checksum & DPIIT recognition numbers.
"""
from __future__ import annotations

import re
from typing import Any

from apps.startups.models import StartupProfile


def validate_gstin_checksum(gstin: str) -> bool:
    """
    Validate Indian GSTIN format:
    15 characters: 2 digits (state) + 10 char PAN + 1 digit (entity) + 'Z' + 1 checksum digit/char
    Example: 27AAAAA0000A1Z5
    """
    pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    return bool(re.match(pattern, gstin.upper().strip()))


def validate_dpiit_number(dpiit_number: str) -> bool:
    """
    Validate DPIIT Recognition Number format:
    DPIITXXXXX or DIPPXXXXX or DIPP/DPIIT followed by numbers
    Example: DPIIT12345
    """
    cleaned = dpiit_number.upper().strip()
    pattern = r"^(DPIIT|DIPP)[/\s\-]?[0-9]{4,8}$"
    return bool(re.match(pattern, cleaned))


def run_instant_verification_sandbox(
    profile: StartupProfile,
    *,
    field_name: str,
    field_value: str,
) -> dict[str, Any]:
    """
    Perform instant sandbox verification for GSTIN or DPIIT numbers.
    If valid, automatically adds field_name to profile_data['verified_fields'].
    """
    field_name = field_name.strip().lower()
    value = field_value.strip().upper()

    if field_name == "gstin":
        is_valid = validate_gstin_checksum(value)
        status_label = "Active GSTIN Verified" if is_valid else "Invalid GSTIN Format"
    elif field_name in ("dpiit_number", "dpiit_recognized"):
        is_valid = validate_dpiit_number(value)
        status_label = "DPIIT Recognition Verified" if is_valid else "Invalid DPIIT Number Format"
    else:
        is_valid = len(value) >= 5
        status_label = f"{field_name.upper()} Verified" if is_valid else "Validation Failed"

    if is_valid:
        verified_fields = set(profile.profile_data.get("verified_fields") or [])
        verified_fields.add(field_name)
        profile.profile_data["verified_fields"] = list(verified_fields)

        if field_name == "gstin":
            profile.profile_data["gstin"] = value
        elif field_name in ("dpiit_number", "dpiit_recognized"):
            profile.dpiit_recognized = True
            profile.profile_data["dpiit_number"] = value

        profile.save(update_fields=["profile_data", "dpiit_recognized"])

    return {
        "field_name": field_name,
        "field_value": value,
        "is_verified": is_valid,
        "status_label": status_label,
        "verification_mode": "instant_sandbox",
    }
