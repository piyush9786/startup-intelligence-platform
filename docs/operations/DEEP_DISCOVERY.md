# Phase 2.5: deep discovery and content quality

This phase prevents landing pages, login shells, menus, and footer-heavy pages
from entering the RAG and structured extraction layers.

## Flow

1. Seed each source with its listing URL and sitemap candidates.
2. Discover same-domain links, PDFs, embedded API URLs, and sitemap URLs.
3. Classify discovered URLs by page type.
4. Place relevant candidates in a persistent crawl frontier.
5. Collect, process, and recursively discover detail pages to a bounded depth.
6. Score processed content for startup-domain usefulness.
7. Mark documents as usable for discovery, RAG, and structured extraction.

## Commands

```bash
python manage.py seed_discovery --all
python manage.py discover_links --all-current --limit 20
python manage.py crawl_frontier --limit 10
python manage.py crawl_frontier --source-domain startupindia.gov.in --limit 10
python manage.py assess_document_quality --all
```

## Safety and scope

The crawler remains restricted to registered official domains, honors the
Phase 1 robots policy, applies bounded depth and page limits, rejects assets,
and preserves every raw source document and version.
