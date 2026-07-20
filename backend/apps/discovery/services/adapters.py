from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings

DEFAULT_ADAPTER = {
    "include_keywords": [
        "scheme",
        "fund",
        "grant",
        "loan",
        "credit",
        "subsidy",
        "startup",
        "msme",
        "incubator",
        "accelerator",
        "challenge",
        "policy",
        "guideline",
        "benefit",
        "registration",
        "recognition",
        "certificate",
        "apply",
        "eligibility",
    ],
    "exclude_keywords": [
        "login",
        "logout",
        "privacy",
        "terms",
        "contact",
        "newsletter",
        "password",
        "otp",
        "javascript:",
        "mailto:",
        "tel:",
    ],
    "max_depth": 2,
    "max_pages": 100,
}


@lru_cache(maxsize=1)
def _registry() -> dict[str, dict[str, object]]:
    path = Path(settings.BASE_DIR) / "catalog/discovery/source_adapters.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def adapter_for(domain: str) -> dict[str, object]:
    configured = _registry().get(domain.lower(), {})
    return {**DEFAULT_ADAPTER, **configured}
