# PostgreSQL canonicalization lock fix

This patch fixes:

`FOR UPDATE cannot be applied to the nullable side of an outer join`

It changes the canonicalization query to lock only `ExternalSchemeRecord` rows and removes the unnecessary nullable `matched_scheme` join.

Apply from the project root:

```bash
unzip -o ~/Downloads/canonical-verified-schemes-postgres-lock-fix.zip -d .
chmod +x scripts/publish_verified_external_schemes.sh
./scripts/publish_verified_external_schemes.sh
```
