# Source registry

`sources.csv` is the version-controlled control plane for authoritative data sources.

Rules:

- Use an official government, public institution, or authorised delivery domain.
- Keep one canonical row per `official_domain`.
- Separate additional trusted domains with `|` in `allowed_domains`.
- Never use news or blog URLs as authoritative evidence sources.
- Changes to this file should be reviewed through Git.

Import it with:

```bash
python manage.py import_sources
```
