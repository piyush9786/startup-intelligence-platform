import pytest
from django.core.exceptions import ValidationError

from apps.schemes.models import Authority
from apps.schemes.services.authority_normalizer import (
    find_authority_by_name,
    normalize_authority_name,
    register_authority_alias,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "Department of Science & Technology (DST)",
            "department of science and technology",
        ),
        (
            "Department of Science and Technology",
            "department of science and technology",
        ),
        (
            "Ministry of MSME",
            ("ministry of micro small and medium enterprises"),
        ),
        (
            ("Ministry of Development of north -eastern Region,"),
            ("ministry of development of north eastern region"),
        ),
        (
            ("Ministry of Electronics & Information Technology (MeitY)"),
            ("ministry of electronics and information technology"),
        ),
    ],
)
def test_normalizes_observed_authority_variants(
    raw,
    expected,
):
    assert normalize_authority_name(raw) == expected


@pytest.mark.django_db
def test_registers_and_resolves_authority_alias():
    authority = Authority.objects.create(
        name=("Department of Science and Technology"),
    )

    register_authority_alias(
        authority=authority,
        alias=("Department of Science & Technology (DST)"),
        source="v4-review",
        verified=True,
    )

    assert find_authority_by_name("Department of Science and Technology (DST)") == authority


@pytest.mark.django_db
def test_rejects_alias_collision():
    first = Authority.objects.create(
        name="First authority",
    )
    second = Authority.objects.create(
        name="Second authority",
    )

    register_authority_alias(
        authority=first,
        alias="Shared authority",
    )

    with pytest.raises(ValidationError):
        register_authority_alias(
            authority=second,
            alias="Shared authority",
        )
