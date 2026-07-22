from django.contrib import admin

from .models import (
    ApplicationStepCandidate,
    BenefitCandidate,
    CandidateCuration,
    CandidateEvidence,
    CandidatePublication,
    CandidateResolution,
    EligibilityRuleCandidate,
    ExternalCapitalSupportRecord,
    ExternalCertificationRequirementRecord,
    ExternalKnowledgeDataset,
    ExternalSchemeDataset,
    ExternalSchemeRecord,
    KnowledgeExtractionRun,
    PublishedEvidence,
    RequiredDocumentCandidate,
    SchemeCandidate,
)


class EvidenceInline(admin.TabularInline):
    model = CandidateEvidence
    extra = 0
    readonly_fields = (
        "chunk",
        "evidence_type",
        "quote",
        "page_number",
    )
    can_delete = False
    show_change_link = True


class EligibilityRuleInline(admin.TabularInline):
    model = EligibilityRuleCandidate
    extra = 0
    show_change_link = True


class BenefitInline(admin.TabularInline):
    model = BenefitCandidate
    extra = 0
    show_change_link = True


class RequiredDocumentInline(admin.TabularInline):
    model = RequiredDocumentCandidate
    extra = 0
    show_change_link = True


class ApplicationStepInline(admin.TabularInline):
    model = ApplicationStepCandidate
    extra = 0
    show_change_link = True


@admin.register(KnowledgeExtractionRun)
class KnowledgeExtractionRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "extraction",
        "extractor_version",
        "status",
        "candidate_count",
        "finished_at",
    )
    list_filter = ("status", "extractor_version")
    search_fields = (
        "extraction__source_document__source__name",
        "extraction__source_document__source_url",
    )
    readonly_fields = (
        "started_at",
        "finished_at",
        "error_message",
        "metadata",
    )


@admin.register(SchemeCandidate)
class SchemeCandidateAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "kind",
        "review_status",
        "confidence",
        "authority_name",
        "start_page",
        "end_page",
    )
    list_filter = (
        "kind",
        "review_status",
        "run__extractor_version",
    )
    search_fields = (
        "title",
        "authority_name",
        "ministry_name",
        "eligibility_text",
        "benefits_text",
    )
    readonly_fields = (
        "stable_key",
        "raw_text",
        "metadata",
        "created_at",
        "updated_at",
    )
    inlines = (
        EligibilityRuleInline,
        BenefitInline,
        RequiredDocumentInline,
        ApplicationStepInline,
        EvidenceInline,
    )


admin.site.register(CandidateEvidence)
admin.site.register(EligibilityRuleCandidate)
admin.site.register(BenefitCandidate)
admin.site.register(RequiredDocumentCandidate)
admin.site.register(ApplicationStepCandidate)


@admin.register(CandidateResolution)
class CandidateResolutionAdmin(admin.ModelAdmin):
    list_display = (
        "candidate",
        "classification",
        "canonical_title",
        "resolved_authority",
        "primary_candidate",
        "resolved_by",
        "resolved_at",
    )
    list_filter = (
        "classification",
        "resolved_authority",
        "resolved_at",
    )
    search_fields = (
        "candidate__title",
        "canonical_title",
        "resolved_authority__name",
        "review_notes",
    )
    raw_id_fields = (
        "candidate",
        "resolved_authority",
        "primary_candidate",
        "resolved_by",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )


class PublishedEvidenceInline(admin.TabularInline):
    model = PublishedEvidence
    extra = 0
    can_delete = False
    readonly_fields = (
        "candidate_evidence",
        "evidence_type",
        "quote",
        "page_number",
        "metadata",
        "created_at",
        "updated_at",
    )


@admin.register(CandidatePublication)
class CandidatePublicationAdmin(admin.ModelAdmin):
    list_display = (
        "candidate",
        "scheme",
        "scheme_version",
        "role",
        "published_by",
        "published_at",
    )
    list_filter = ("role", "published_at", "scheme__authority")
    search_fields = (
        "candidate__title",
        "scheme__canonical_name",
        "publication_hash",
    )
    raw_id_fields = (
        "candidate",
        "scheme",
        "scheme_version",
        "published_by",
    )
    readonly_fields = (
        "publication_hash",
        "published_at",
        "metadata",
        "created_at",
        "updated_at",
    )
    inlines = (PublishedEvidenceInline,)


@admin.register(PublishedEvidence)
class PublishedEvidenceAdmin(admin.ModelAdmin):
    list_display = (
        "publication",
        "evidence_type",
        "page_number",
        "candidate_evidence",
    )
    list_filter = ("evidence_type",)
    search_fields = (
        "quote",
        "publication__candidate__title",
        "publication__scheme__canonical_name",
    )
    raw_id_fields = ("publication", "candidate_evidence")
    readonly_fields = (
        "publication",
        "candidate_evidence",
        "evidence_type",
        "quote",
        "page_number",
        "metadata",
        "created_at",
        "updated_at",
    )


@admin.register(CandidateCuration)
class CandidateCurationAdmin(admin.ModelAdmin):
    list_display = (
        "candidate",
        "review_status",
        "official_url",
        "reviewed_by",
        "reviewed_at",
    )
    list_filter = (
        "review_status",
        "reviewed_at",
    )
    search_fields = (
        "candidate__title",
        "canonical_summary",
        "canonical_objective",
        "official_url",
    )
    raw_id_fields = (
        "candidate",
        "reviewed_by",
    )
    readonly_fields = (
        "reviewed_by",
        "reviewed_at",
        "created_at",
        "updated_at",
    )

@admin.register(ExternalSchemeDataset)
class ExternalSchemeDatasetAdmin(admin.ModelAdmin):
    list_display = (
        "dataset_key",
        "dataset_name",
        "source_row_count",
        "record_count",
        "normalization_version",
        "is_active",
        "updated_at",
    )
    list_filter = (
        "is_active",
        "normalization_version",
    )
    search_fields = (
        "dataset_key",
        "dataset_name",
        "source_filename",
    )
    readonly_fields = (
        "content_sha256",
        "created_at",
        "updated_at",
    )


@admin.register(ExternalSchemeRecord)
class ExternalSchemeRecordAdmin(admin.ModelAdmin):
    list_display = (
        "scheme_name",
        "dataset",
        "review_status",
        "funding_type",
        "central_state",
        "state",
        "warning_count",
        "matched_scheme",
    )
    list_filter = (
        "dataset",
        "review_status",
        "central_state",
        "state",
    )
    search_fields = (
        "scheme_name",
        "normalized_name",
        "external_id",
        "ministry",
        "department",
        "sector",
        "eligibility",
    )
    raw_id_fields = (
        "matched_candidate",
        "matched_scheme",
    )
    readonly_fields = (
        "dataset",
        "external_id",
        "normalized_name",
        "record_sha256",
        "raw_row",
        "source_rows",
        "external_ids",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Warnings")
    def warning_count(self, obj):
        return len(obj.quality_warnings or [])

@admin.register(ExternalKnowledgeDataset)
class ExternalKnowledgeDatasetAdmin(admin.ModelAdmin):
    list_display = (
        "dataset_key",
        "dataset_kind",
        "record_count",
        "normalization_version",
        "is_active",
        "updated_at",
    )
    list_filter = (
        "dataset_kind",
        "is_active",
        "normalization_version",
    )
    search_fields = (
        "dataset_key",
        "dataset_name",
        "source_filename",
    )
    readonly_fields = (
        "dataset_kind",
        "dataset_key",
        "dataset_name",
        "source_filename",
        "source_sheet",
        "source_row_count",
        "record_count",
        "normalization_version",
        "content_sha256",
        "metadata",
        "created_at",
        "updated_at",
    )


@admin.register(ExternalCapitalSupportRecord)
class ExternalCapitalSupportRecordAdmin(
    admin.ModelAdmin,
):
    list_display = (
        "support_name",
        "support_type",
        "dataset",
        "review_status",
        "maximum_amount",
        "warning_count",
        "external_scheme_match_count",
        "matched_scheme",
    )
    list_filter = (
        "dataset",
        "review_status",
        "support_type",
        "funding_category",
        "state",
    )
    search_fields = (
        "external_id",
        "support_name",
        "scheme_name",
        "normalized_name",
        "ministry",
        "implementing_agency",
        "eligible_entity",
        "funding_purpose",
    )
    raw_id_fields = (
        "matched_scheme",
    )
    filter_horizontal = (
        "matched_external_schemes",
    )
    readonly_fields = (
        "dataset",
        "external_id",
        "support_name",
        "support_type",
        "scheme_name",
        "normalized_name",
        "ministry",
        "implementing_agency",
        "funding_category",
        "implementing_agency",
        "funding_category",
        "minimum_amount",
        "maximum_amount",
        "raw_minimum_amount",
        "raw_maximum_amount",
        "currency",
        "interest_rate_text",
        "collateral_required_text",
        "repayment_required_text",
        "startup_stage",
        "industry",
        "eligible_entity",
        "state",
        "funding_purpose",
        "claimed_scheme_status",
        "source_priority_score",
        "source_ai_recommendation_weight",
        "remarks",
        "matched_external_scheme_ids",
        "quality_warnings",
        "source_row_number",
        "raw_row",
        "record_sha256",
        "created_at",
        "updated_at",
    )
    list_select_related = (
        "dataset",
        "matched_scheme",
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "matched_external_schemes",
            )
        )

    @admin.display(description="Warnings")
    def warning_count(self, obj):
        return len(obj.quality_warnings or [])

    @admin.display(description="Scheme matches")
    def external_scheme_match_count(self, obj):
        return obj.matched_external_schemes.count()


@admin.register(
    ExternalCertificationRequirementRecord
)
class ExternalCertificationRequirementRecordAdmin(
    admin.ModelAdmin,
):
    list_display = (
        "certificate_name",
        "certificate_type",
        "dataset",
        "review_status",
        "display_eligible",
        "issuing_authority",
        "warning_count",
    )
    list_filter = (
        "dataset",
        "review_status",
        "display_eligible",
        "certificate_type",
        "requirement_level",
    )
    search_fields = (
        "external_id",
        "certificate_name",
        "normalized_name",
        "description",
        "eligibility",
        "benefits",
        "issuing_authority",
    )
    readonly_fields = (
        "dataset",
        "external_id",
        "certificate_name",
        "normalized_name",
        "certificate_type",
        "description",
        "industry",
        "startup_stage",
        "requirement_level",
        "eligibility",
        "benefits",
        "validity",
        "renewal_period",
        "issuing_authority",
        "official_document_text",
        "official_apply_url",
        "source_priority_score",
        "display_eligible",
        "quality_warnings",
        "source_row_number",
        "raw_row",
        "record_sha256",
        "created_at",
        "updated_at",
    )
    list_select_related = (
        "dataset",
    )

    @admin.display(description="Warnings")
    def warning_count(self, obj):
        return len(obj.quality_warnings or [])
