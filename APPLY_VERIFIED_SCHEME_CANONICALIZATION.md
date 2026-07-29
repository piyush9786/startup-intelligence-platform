# Publish the 70 verified external schemes

This hotfix does **not** claim a second independent verification. It publishes
only external records that are already marked `verified` by the bundled review
manifest and preserves their official URL, reviewer note, dataset key, source
row, record hash, and raw imported evidence.

Run from the active project directory:

```bash
cd /home/ps/Project/startup-intelligence-platform
unzip -o ~/Downloads/canonical-verified-schemes-hotfix.zip -d .
chmod +x scripts/publish_verified_external_schemes.sh
./scripts/publish_verified_external_schemes.sh
```

Expected final state:

- 77 unique active canonical verified schemes
- 78 verified external records linked to canonical schemes
- 0 verified external records left unmatched
- 11 rejected records remain rejected and unpublished
- a new active candidate TF-IDF index containing all 77 current SchemeVersion IDs
- dashboard `Verified schemes` count becomes 77 automatically

The command is transactional and idempotent. Re-running it does not create
additional schemes or versions when the reviewed data has not changed.
