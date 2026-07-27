# Historical Company Data Foundation V1

## Scope

This phase establishes the governed input layer for historical startup
intelligence. It does not calculate peer similarity, benchmarks, risks, or
recommendations yet. Those outputs must be built on reviewed source records and
time-series observations from this layer.

The existing `sources` app remains responsible for government-scheme crawling.
Historical company provenance is isolated in `apps.companies` because its source
types, reliability rules, identities, and update cadence are different.

## Data lineage

```text
CompanyDataSource
        |
        +---- RawCompanyDataset (immutable CSV checksum + bronze storage URI)
        |
        +---- CompanySourceRecord ---- Company ---- CompanyAlias
                                           |
                                           +---- CompanyMetric
                                           |
                                           +---- CompanyOutcome
```

Every metric and outcome points to both the logical source and the exact raw
dataset that supplied its current value. Re-importing the same source file is
idempotent. A later file updates the source record but creates a new dated
metric observation rather than overwriting history.

## Source governance

`reliability_score` is a governance input, not a statistical probability.
Reviewers assign a value from 0 to 1 using the following starting rubric:

| Range | Intended use |
| --- | --- |
| 0.90–1.00 | Authoritative registry, audited filing, or primary disclosure |
| 0.70–0.89 | Reputable structured dataset with documented methodology |
| 0.40–0.69 | Secondary report requiring corroboration |
| 0.00–0.39 | Discovery or synthetic data; never sufficient by itself |

A company may be marked `verified` only after its identity and current status
are supported by reviewed provenance. Conflicting sources remain represented as
separate source records and should move the company to `disputed` until a
reviewer resolves the conflict.

## CSV contract

Required columns:

```text
external_id
canonical_name
industry
business_model
country
operating_status
confidence_score
```

Optional identity fields include aliases separated by `|`, sub-industry,
customer segment, location, founded year, website, and source record URL.

A metric observation is optional, but when present all four columns are
required:

```text
metric_name, metric_value, metric_unit, observation_date
```

Supported V1 metric names are `revenue`, `employee_count`, `customer_count`,
`monthly_growth`, `burn_rate`, `runway_months`, `funding_total`, and
`valuation`. Dates use ISO `YYYY-MM-DD`. Financial units should use an ISO
currency code such as `INR` or `USD`; ratios and counts use explicit units such
as `ratio`, `people`, or `customers`.

## Import workflow

```bash
python manage.py import_companies \
  --file /data/companies.csv \
  --source-slug government-portal-2026 \
  --source-name "Government portal company export" \
  --source-type government \
  --source-url https://data.example.gov/companies \
  --licence "Open Government Data Licence" \
  --reliability-score 0.950
```

The command:

1. Computes a SHA-256 checksum and registers the raw dataset.
2. Validates the complete CSV before creating company facts.
3. Uploads the unchanged file to
   `s3://<raw-bucket>/company-datasets/<source>/<checksum>/...`.
4. Resolves records idempotently by `(source, external_id)`.
5. Stores dated metric and outcome evidence.
6. Marks the dataset processed or records the failure reason.

`--skip-storage-upload` is intended only for tests and local contract fixtures.

## API

Authenticated users can read and filter:

```text
GET /api/v1/companies/
GET /api/v1/companies/{id}/
```

The detail response includes aliases, time-series metrics, outcomes, and a
provenance count. Source and raw-dataset APIs are admin-only:

```text
/api/v1/company-data-sources/
/api/v1/company-datasets/
```

## Next implementation boundary

Phase 2 should use Airflow to invoke this same import contract and persist task
attempt/freshness metadata. Phase 3 should publish versioned dataset events
containing the `RawCompanyDataset.dataset_id` and `storage_path`, never the CSV
payload itself. Peer selection and benchmark tables belong to Phase 4 after a
reviewed dataset is available.
