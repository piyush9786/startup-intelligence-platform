from django.contrib import admin

from .models import (
    ApplicationStepCandidate,
    BenefitCandidate,
    CandidateCuration,
    CandidateEvidence,
    CandidatePublication,
    CandidateResolution,
    EligibilityRuleCandidate,
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
