from __future__ import annotations

import re

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.schemes.models import Authority, AuthorityAlias

EXACT_NORMALIZATION_MAP = {
    "dbt": "department of biotechnology",
    "department of biotechnology dbt": ("department of biotechnology"),
    "dst": "department of science and technology",
    "department of science and technology dst": ("department of science and technology"),
    "meity": ("ministry of electronics and information technology"),
    "ministry of electronics and information technology meity": (
        "ministry of electronics and information technology"
    ),
    "ministry of msme": ("ministry of micro small and medium enterprises"),
    "ministry of micro small medium enterprises": (
        "ministry of micro small and medium enterprises"
    ),
    "mofpi": "ministry of food processing industries",
    "ministry of food processing industries mofpi": ("ministry of food processing industries"),
}


def normalize_authority_name(value: str) -> str:
    normalized = (value or "").casefold()
    normalized = normalized.replace("&", " and ")

    normalized = re.sub(
        r"north\s*-\s*eastern",
        "north eastern",
        normalized,
    )
    normalized = re.sub(
        r"[^a-z0-9]+",
        " ",
        normalized,
    )
    normalized = " ".join(normalized.split())

    return EXACT_NORMALIZATION_MAP.get(
        normalized,
        normalized,
    )


def find_authority_by_name(
    value: str,
) -> Authority | None:
    normalized = normalize_authority_name(value)

    if not normalized:
        return None

    alias = (
        AuthorityAlias.objects.select_related("authority")
        .filter(normalized_alias=normalized)
        .first()
    )

    if alias is not None:
        return alias.authority

    matches = [
        authority
        for authority in Authority.objects.all()
        if normalize_authority_name(authority.name) == normalized
    ]

    if len(matches) == 1:
        return matches[0]

    return None


@transaction.atomic
def register_authority_alias(
    *,
    authority: Authority,
    alias: str,
    source: str = "",
    verified: bool = False,
) -> AuthorityAlias:
    normalized = normalize_authority_name(alias)

    if not normalized:
        raise ValidationError("Authority alias cannot be blank.")

    existing = (
        AuthorityAlias.objects.select_for_update().filter(normalized_alias=normalized).first()
    )

    if existing is not None and existing.authority_id != authority.id:
        raise ValidationError("This normalized alias is already assigned to another authority.")

    authority_alias, _created = AuthorityAlias.objects.update_or_create(
        normalized_alias=normalized,
        defaults={
            "authority": authority,
            "alias": alias.strip(),
            "source": source.strip(),
            "verified": verified,
        },
    )

    return authority_alias
