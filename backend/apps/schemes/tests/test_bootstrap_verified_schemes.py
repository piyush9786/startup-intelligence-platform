import pytest
from django.core.management import call_command

from apps.schemes.models import EligibilityRule, Scheme, SchemeVersion

pytestmark = pytest.mark.django_db

EXPECTED_SCHEMES = {
    "A Scheme for Promotion of Innovation, Rural Industries and Entrepreneurship (ASPIRE)",
    "Biotechnology Ignition Grant Scheme (BIG)",
    "Credit Guarantee Scheme for Startups (CGSS)",
    "Fund of Funds for Startups (FFS)",
    "NIDHI Entrepreneur-in-Residence (NIDHI-EIR)",
    "NIDHI Seed Support Programme (NIDHI-SSP)",
    "Startup India Seed Fund Scheme (SISFS)",
}


def test_bootstrap_verified_schemes_creates_complete_public_catalog():
    call_command("bootstrap_verified_schemes")

    schemes = Scheme.objects.filter(
        canonical_name__in=EXPECTED_SCHEMES,
        lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
        current_version__verification_status=(
            SchemeVersion.VerificationStatus.VERIFIED
        ),
    ).select_related("current_version")

    assert set(schemes.values_list("canonical_name", flat=True)) == EXPECTED_SCHEMES
    assert all(scheme.current_version.official_url for scheme in schemes)
    assert EligibilityRule.objects.filter(
        scheme_version__scheme__in=schemes,
        manually_verified=True,
    ).exists()


def test_bootstrap_verified_schemes_is_idempotent():
    call_command("bootstrap_verified_schemes")
    first_counts = (
        Scheme.objects.count(),
        SchemeVersion.objects.count(),
        EligibilityRule.objects.count(),
    )

    call_command("bootstrap_verified_schemes")

    assert (
        Scheme.objects.count(),
        SchemeVersion.objects.count(),
        EligibilityRule.objects.count(),
    ) == first_counts
