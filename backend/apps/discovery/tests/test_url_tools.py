import pytest

from apps.discovery.services.url_tools import normalize_url


@pytest.mark.parametrize(
    ("candidate", "expected"),
    [
        (
            "/schemes/grant?utm_source=test&b=2&a=1#eligibility",
            "https://example.gov.in/schemes/grant?a=1&b=2",
        ),
        ("javascript:void(0)", None),
        ("mailto:test@example.com", None),
    ],
)
def test_normalize_url(candidate, expected):
    assert normalize_url("https://example.gov.in/start", candidate) == expected


def test_rejects_unresolved_javascript_template_url():
    candidate = "https://api.example.gov.in/search?searchKey=${searchKey}`"

    assert (
        normalize_url(
            "https://example.gov.in/",
            candidate,
        )
        is None
    )


def test_rejects_encoded_template_url():
    candidate = "https://api.example.gov.in/search?searchKey=%24%7BsearchKey%7D%60"

    assert (
        normalize_url(
            "https://example.gov.in/",
            candidate,
        )
        is None
    )
