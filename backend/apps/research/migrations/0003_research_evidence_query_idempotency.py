"""Deduplicate research rows before adding redelivery constraints."""
from django.db import migrations, models
from django.db.models import Count


def _delete_duplicate_groups(
    model,
    *,
    group_fields: tuple[str, ...],
) -> None:
    duplicates = (
        model.objects.values(*group_fields)
        .annotate(row_count=Count("id"))
        .filter(row_count__gt=1)
    )
    for group in duplicates.iterator():
        filters = {
            field: group[field]
            for field in group_fields
        }
        ids = list(
            model.objects.filter(**filters)
            .order_by("created_at", "id")
            .values_list("id", flat=True)
        )
        if len(ids) > 1:
            model.objects.filter(id__in=ids[1:]).delete()


def deduplicate_research_rows(apps, schema_editor):
    ResearchSearchQuery = apps.get_model(
        "research",
        "ResearchSearchQuery",
    )
    ResearchEvidence = apps.get_model(
        "research",
        "ResearchEvidence",
    )
    _delete_duplicate_groups(
        ResearchSearchQuery,
        group_fields=(
            "research_request_id",
            "query",
            "provider",
        ),
    )
    _delete_duplicate_groups(
        ResearchEvidence,
        group_fields=(
            "research_request_id",
            "content_hash",
        ),
    )


class Migration(migrations.Migration):
    dependencies = [
        (
            "research",
            "0002_research_request_integrity_and_status",
        ),
    ]

    operations = [
        migrations.RunPython(
            deduplicate_research_rows,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="researchsearchquery",
            constraint=models.UniqueConstraint(
                fields=(
                    "research_request",
                    "query",
                    "provider",
                ),
                name="research_unique_search_query",
            ),
        ),
        migrations.AddConstraint(
            model_name="researchevidence",
            constraint=models.UniqueConstraint(
                fields=(
                    "research_request",
                    "content_hash",
                ),
                name="research_unique_evidence_per_request",
            ),
        ),
    ]
