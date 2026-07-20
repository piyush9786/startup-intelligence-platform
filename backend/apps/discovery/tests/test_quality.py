from apps.discovery.services.quality import POSITIVE_SIGNALS


def test_quality_signal_catalog_contains_core_scheme_sections():
    assert "eligibility" in POSITIVE_SIGNALS
    assert "benefits" in POSITIVE_SIGNALS
    assert "documents required" in POSITIVE_SIGNALS
    assert "application process" in POSITIVE_SIGNALS
