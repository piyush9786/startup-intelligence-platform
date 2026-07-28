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


def test_nested_noise_elements_do_not_break_extraction():
    payload = extract_html(
        b"""
        <html>
          <head>
            <title>Startup Grant</title>
          </head>
          <body>
            <div class="modal">
              <div class="modal-content">
                <span>Login</span>
                <p>Forgot your password</p>
              </div>
            </div>

            <main>
              <h1>Prototype Grant</h1>
              <p>Funding support for eligible startups.</p>

              <h2>Eligibility</h2>
              <p>The startup must be incorporated in India.</p>

              <h2>Benefits</h2>
              <p>Grant support is available for prototype development.</p>
            </main>
          </body>
        </html>
        """
    )

    assert payload.title == "Startup Grant"
    assert "Prototype Grant" in payload.combined_text
    assert "incorporated in India" in payload.combined_text
    assert "Forgot your password" not in payload.combined_text
