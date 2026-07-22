from django.db import migrations, models
from django.db.models import Count


def supersede_duplicate_onboarding_drafts(
    apps,
    schema_editor,
):
    del schema_editor

    draft_model = apps.get_model(
        "startups",
        "StartupAssessmentDraft",
    )

    duplicate_owner_ids = (
        draft_model.objects.filter(
            status="draft",
            startup_profile__isnull=True,
        )
        .values("owner_id")
        .annotate(draft_count=Count("id"))
        .filter(draft_count__gt=1)
        .values_list("owner_id", flat=True)
    )

    for owner_id in duplicate_owner_ids.iterator():
        draft_ids = list(
            draft_model.objects.filter(
                owner_id=owner_id,
                status="draft",
                startup_profile__isnull=True,
            )
            .order_by("-updated_at", "-id")
            .values_list("id", flat=True)
        )

        draft_model.objects.filter(
            id__in=draft_ids[1:],
        ).update(status="superseded")


class Migration(migrations.Migration):
    dependencies = [
        (
            "startups",
            "0007_startupadvisorbriefingjob",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="startupassessmentdraft",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("submitted", "Submitted"),
                    ("superseded", "Superseded"),
                ],
                default="draft",
                max_length=20,
            ),
        ),
        migrations.RunPython(
            supersede_duplicate_onboarding_drafts,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="startupassessmentdraft",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    status="draft",
                    startup_profile__isnull=True,
                ),
                fields=("owner",),
                name="startup_one_onboarding_draft",
            ),
        ),
    ]
