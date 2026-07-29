# Apply the hybrid verified-scheme reranker

This patch replaces plain text filtering in the Scheme Explorer with an auditable hybrid ranking API.

The final score uses:

- 30% TF-IDF text relevance
- 25% deterministic eligibility
- 15% support-type match
- 10% sector match
- 10% startup-stage match
- 5% location match
- 5% evidence completeness

Strict intent filters prevent misleading results:

- A women-focused query only returns schemes with explicit women/female-founder evidence.
- A loan query only returns loan, credit, debt, guarantee, collateral, interest-rate, or working-capital programmes.
- A seed-funding query only returns explicit seed, prototype, proof-of-concept, grant, or incubator-funding programmes.
- An explicit sector query excludes unrelated sectors.
- A startup profile is applied when one is selected.
- Closed and deterministically ineligible schemes are excluded.

TF-IDF v6 remains a candidate. The API identifies its stage and does not describe the hybrid score as an approval probability.

## Install

```bash
cd /home/ps/Project/startup-intelligence-platform

unzip -o ~/Downloads/hybrid-scheme-reranker-hotfix.zip -d .

chmod +x scripts/apply_hybrid_scheme_reranker.sh
./scripts/apply_hybrid_scheme_reranker.sh
```

Do not use `--gpu`.

## API

```text
GET /api/v1/schemes/hybrid-search/?q=<query>&startup_profile_id=<uuid>&limit=20
```

The response includes:

- detected query intents
- TF-IDF model version and deployment stage
- transparent scoring weights
- final score and component scores
- deterministic eligibility result
- matched intent labels
- evidence snapshot status
- an explicit no-match message

## UI test

Open:

```text
http://localhost:5173/schemes
```

Hard refresh once with `Ctrl+Shift+R`, then try:

```text
biotechnology innovation grant
loan support for manufacturing MSME
women entrepreneur government scheme
seed funding for technology startup
```

The women-focused query should return an explicit no-match message when the catalog has no verified women-specific scheme, rather than showing unrelated general programmes.
