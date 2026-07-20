from django.contrib import admin

from .models import StartupProfile


@admin.register(StartupProfile)
class StartupProfileAdmin(admin.ModelAdmin):
    list_display = (
        "startup_name",
        "owner",
        "stage",
        "state",
        "dpiit_recognized",
        "udyam_registered",
    )
    list_filter = ("stage", "state", "dpiit_recognized", "udyam_registered")
    search_fields = ("startup_name", "legal_name", "description")
