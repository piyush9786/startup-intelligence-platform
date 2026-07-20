from apps.discovery.models import DiscoveredURL
from apps.discovery.services.classifier import classify_page


def test_classifies_scheme_detail_from_sections():
    page_type = classify_page(
        url="https://example.gov.in/program/seed-support",
        title="Seed Support",
        text=("Eligibility\nBenefits\nDocuments Required\nHow to Apply\nFunding Amount"),
    )
    assert page_type == DiscoveredURL.PageType.SCHEME_DETAIL


def test_classifies_login_shell():
    page_type = classify_page(
        url="https://example.gov.in/login",
        text="Login Forgot password OTP Change Password",
    )
    assert page_type == DiscoveredURL.PageType.LOGIN


def test_classifies_startup_scheme_page():
    page_type = classify_page(
        url=("https://example.gov.in/content/startup-scheme.html"),
        anchor_text="DPIIT recognition and startup benefits",
    )

    assert page_type == DiscoveredURL.PageType.SCHEME_DETAIL
