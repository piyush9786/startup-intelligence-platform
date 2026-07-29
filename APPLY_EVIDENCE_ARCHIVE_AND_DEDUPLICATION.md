# Verified Scheme Evidence Archive and Deduplication

The current 77 verified scheme versions have reviewer-manifest evidence, URLs,
and metadata hashes, but no raw HTML/PDF object in MinIO. This patch adds a
safe backfill command that uses the existing hardened collector and relinks
current verified versions to archived raw snapshots.

It also adds a separate, non-destructive command for the two confirmed duplicate
pairs. Duplicate Scheme rows are marked `superseded`; their versions and proof
remain for audit. External links move to the keeper, aliases are preserved, and
TF-IDF is rebuilt from 75 active verified unique schemes.

## Apply

```bash
cd /home/ps/Project/startup-intelligence-platform
unzip -o ~/Downloads/verified-scheme-evidence-repair.zip -d .
chmod +x scripts/archive_verified_scheme_snapshots.sh \
  scripts/supersede_confirmed_scheme_duplicates.sh

./scripts/archive_verified_scheme_snapshots.sh
./scripts/supersede_confirmed_scheme_duplicates.sh
```

The snapshot command obeys robots.txt and source-domain security restrictions.
It reports blocked sources rather than bypassing those controls.
