from apps.documents.services.extractors import extract_html


def test_html_extraction_removes_scripts_and_preserves_sections():
    payload = extract_html(
        b"""
        <html>
          <head><title>Scheme Guide</title></head>
          <body>
            <script>ignore me</script>
            <main>
              <h1>Seed Support</h1>
              <p>Funding for prototype-stage startups.</p>
              <h2>Eligibility</h2>
              <p>The entity must be incorporated in India.</p>
            </main>
          </body>
        </html>
        """
    )

    assert payload.title == "Scheme Guide"
    assert len(payload.sections) == 2
    assert "ignore me" not in payload.combined_text
    assert "prototype-stage" in payload.combined_text
    assert payload.sections[1].heading == "Eligibility"
