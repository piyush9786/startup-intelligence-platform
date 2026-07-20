import pytest

from apps.discovery.services.link_discovery import discover_links
from apps.sources.models import Source


@pytest.mark.django_db
def test_discovers_relevant_links_and_rejects_assets():
    source = Source.objects.create(
        name="Example",
        official_domain="example.gov.in",
        listing_url="https://example.gov.in/schemes",
        authority_tier=Source.AuthorityTier.OFFICIAL_AUTHORITY,
        respect_robots_txt=False,
    )
    candidates = discover_links(
        source=source,
        parent_url=source.listing_url,
        content=b"""
        <main>
          <a href='/schemes/seed-grant'>Seed grant eligibility</a>
          <a href='/files/guidelines.pdf'>Scheme guidelines</a>
          <a href='/images/logo.png'>Logo</a>
          <a href='/login'>Login</a>
        </main>
        """,
    )
    by_url = {item.normalized_url: item for item in candidates}
    assert by_url["https://example.gov.in/schemes/seed-grant"].allowed
    assert by_url["https://example.gov.in/files/guidelines.pdf"].allowed
    assert "https://example.gov.in/images/logo.png" not in by_url
    assert not by_url["https://example.gov.in/login"].allowed
