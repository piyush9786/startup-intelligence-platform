from django.contrib import admin

from .models import (
    Authority,
    AuthorityAlias,
    EligibilityRule,
    Scheme,
    SchemeVersion,
)


class EligibilityRuleInline(admin.TabularInline):
    model = EligibilityRule
    extra = 0


@admin.register(Authority)
class AuthorityAdmin(admin.ModelAdmin):
    list_display = ("name", "authority_type", "ministry", "state")
    search_fields = ("name", "ministry", "department")


@admin.register(Scheme)
class SchemeAdmin(admin.ModelAdmin):
    list_display = ("canonical_name", "authority", "lifecycle_status", "current_version")
    list_filter = ("lifecycle_status", "authority")
    search_fields = ("canonical_name", "short_name")


@admin.register(SchemeVersion)
class SchemeVersionAdmin(admin.ModelAdmin):
    list_display = (
        "scheme",
        "version_number",
        "application_status",
        "verification_status",
        "deadline",
    )
    list_filter = ("verification_status", "application_status")
    search_fields = ("scheme__canonical_name", "description", "objective")
    inlines = [EligibilityRuleInline]


@admin.register(AuthorityAlias)
class AuthorityAliasAdmin(admin.ModelAdmin):
    list_display = (
        "alias",
        "normalized_alias",
        "authority",
        "verified",
        "source",
    )
    list_filter = (
        "verified",
        "source",
    )
    search_fields = (
        "alias",
        "normalized_alias",
        "authority__name",
    )
    raw_id_fields = ("authority",)
