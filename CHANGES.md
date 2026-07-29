# Hybrid scheme reranker changes

- Adds `GET /api/v1/schemes/hybrid-search/`.
- Uses active TF-IDF as 30% of an auditable score instead of treating cosine similarity as the final recommendation.
- Adds deterministic eligibility, support type, sector, stage, location, and evidence signals.
- Applies the selected startup profile when provided and account-visible.
- Excludes closed and deterministically ineligible schemes.
- Adds strict filters for women-specific, loan, tax, seed-funding, sector, and stage intents.
- Returns an explicit no-match response instead of unrelated fallback schemes.
- Shows a clearly labelled hybrid relevance score in the Scheme Explorer.
- Hides unranked external aliases while a hybrid canonical search is active.
- Leaves TF-IDF v6 in candidate status and does not alter the ML registry or catalog data.
