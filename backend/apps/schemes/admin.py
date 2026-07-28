from django.contrib import admin

from .models import (
    Authority,
    AuthorityAlias,
    EligibilityRule,
    PrerequisiteConcept,
    Scheme,
    SchemeGraphProjectionRun,
    SchemePrerequisite,
    SchemeUnlock,
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


@admin.register(PrerequisiteConcept)
class PrerequisiteConceptAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "key",
        "category",
        "lifecycle_status",
        "verified_by",
        "verified_at",
    )
    list_filter = (
        "category",
        "lifecycle_status",
    )
    search_fields = (
        "name",
        "key",
        "description",
        "evidence_text",
    )
    raw_id_fields = (
        "source_document",
        "verified_by",
    )


@admin.register(SchemePrerequisite)
class SchemePrerequisiteAdmin(admin.ModelAdmin):
    list_display = (
        "scheme_version",
        "prerequisite",
        "requirement_type",
        "origin",
        "review_status",
        "reviewed_by",
    )
    list_filter = (
        "requirement_type",
        "origin",
        "review_status",
    )
    search_fields = (
        "scheme_version__scheme__canonical_name",
        "prerequisite__name",
        "evidence_text",
    )
    raw_id_fields = (
        "scheme_version",
        "prerequisite",
        "source_document",
        "reviewed_by",
    )


@admin.register(SchemeUnlock)
class SchemeUnlockAdmin(admin.ModelAdmin):
    list_display = (
        "predecessor_version",
        "unlocked_version",
        "origin",
        "review_status",
        "reviewed_by",
    )
    list_filter = (
        "origin",
        "review_status",
    )
    search_fields = (
        "predecessor_version__scheme__canonical_name",
        "unlocked_version__scheme__canonical_name",
        "evidence_text",
    )
    raw_id_fields = (
        "predecessor_version",
        "unlocked_version",
        "source_document",
        "reviewed_by",
    )


@admin.register(SchemeGraphProjectionRun)
class SchemeGraphProjectionRunAdmin(admin.ModelAdmin):
    list_display = (
        "graph_version",
        "status",
        "scheme_node_count",
        "prerequisite_node_count",
        "prerequisite_edge_count",
        "unlock_edge_count",
        "created_at",
    )
    list_filter = (
        "graph_version",
        "status",
    )
    readonly_fields = (
        "graph_version",
        "status",
        "source_hash",
        "scheme_node_count",
        "prerequisite_node_count",
        "prerequisite_edge_count",
        "unlock_edge_count",
        "started_at",
        "finished_at",
        "error_message",
        "metadata",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
