from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID


def json_ready(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, Mapping):
        return {
            str(key): json_ready(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
        }

    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]

    if isinstance(value, (set, frozenset)):
        normalized = [json_ready(item) for item in value]
        return sorted(
            normalized,
            key=canonical_json,
        )

    if value is None or isinstance(
        value,
        (bool, int, float, str),
    ):
        return value

    raise TypeError(f"Unsupported canonical JSON value: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(
        json_ready(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_sha256(value: Any) -> str:
    encoded = canonical_json(value).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
