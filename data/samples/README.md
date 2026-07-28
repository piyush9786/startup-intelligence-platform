# Sample company data

`indian_b2b_saas_demo.csv` is a synthetic contract fixture for exercising the
historical-company ingestion pipeline. Names, URLs, metrics, and outcomes are
invented; the rows are deliberately marked `unverified` with low confidence.
They must never be presented as evidence about real companies or used to train
production models.

Import it without requiring MinIO:

```bash
python manage.py import_companies \
  --file ../data/samples/indian_b2b_saas_demo.csv \
  --source-slug synthetic-b2b-saas-demo \
  --source-name "Synthetic Indian B2B SaaS demo" \
  --source-type manual \
  --licence internal-demo-only \
  --reliability-score 0.200 \
  --skip-storage-upload
```

Omit `--skip-storage-upload` in the Docker development stack to archive the
unchanged CSV in the configured MinIO bronze bucket before importing it.
