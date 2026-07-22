from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TimeStampedModel
from apps.documents.models import DocumentChunk, DocumentExtraction


class KnowledgeExtractionRun(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    extraction = models.ForeignKey(
        DocumentExtraction,
        on_delete=models.CASCADE,
        related_name="knowledge_runs",
    )
    extractor_version = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    candidate_count = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["extraction", "extractor_version"],
                name="unique_knowledge_extraction_version",
            )
        ]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["extraction", "extractor_version"]),
        ]

    def __str__(self) -> str:
        return f"{self.extraction_id} - {self.extractor_version} - {self.status}"


class SchemeCandidate(TimeStampedModel):
    class Kind(models.TextChoices):
        SCHEME = "scheme", "Scheme"
        FUND = "fund", "Fund"
        GRANT = "grant", "Grant"
        LOAN = "loan", "Loan"
        GUARANTEE = "guarantee", "Credit guarantee"
        BENEFIT = "benefit", "Benefit"
        RECOGNITION = "recognition", "Recognition"
        REGISTRATION = "registration", "Registration"
        CERTIFICATE = "certificate", "Certificate"
        POLICY = "policy", "Policy"
        PROGRAM = "program", "Program"
        INCUBATOR = "incubator", "Incubator support"
        UNKNOWN = "unknown", "Unknown"

    class ReviewStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        NEEDS_REVIEW = "needs_review", "Needs review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        PUBLISHED = "published", "Published"

    run = models.ForeignKey(
        KnowledgeExtractionRun,
        on_delete=models.CASCADE,
        related_name="candidates",
    )
    stable_key = models.CharField(max_length=64)
    title = models.CharField(max_length=500)
    kind = models.CharField(
        max_length=30,
        choices=Kind.choices,
        default=Kind.UNKNOWN,
    )
    authority_name = models.CharField(max_length=500, blank=True)
    ministry_name = models.CharField(max_length=500, blank=True)
    summary = models.TextField(blank=True)
    objective_text = models.TextField(blank=True)
    eligibility_text = models.TextField(blank=True)
    benefits_text = models.TextField(blank=True)
    application_text = models.TextField(blank=True)
    required_documents_text = models.TextField(blank=True)
    official_url = models.URLField(max_length=2000, blank=True)
    application_url = models.URLField(max_length=2000, blank=True)
    financial_amount_min = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
    )
    financial_amount_max = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
    )
    currency = models.CharField(max_length=10, default="INR", blank=True)
    start_page = models.PositiveIntegerField(null=True, blank=True)
    end_page = models.PositiveIntegerField(null=True, blank=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    review_status = models.CharField(
        max_length=30,
        choices=ReviewStatus.choices,
        default=ReviewStatus.NEEDS_REVIEW,
    )
    raw_text = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["run", "start_page", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["run", "stable_key"],
                name="unique_candidate_run_stable_key",
            )
        ]
        indexes = [
            models.Index(fields=["review_status", "-confidence"]),
            models.Index(fields=["kind", "review_status"]),
            models.Index(fields=["run", "start_page"]),
        ]

    def __str__(self) -> str:
        return self.title


class CandidateEvidence(TimeStampedModel):
    class EvidenceType(models.TextChoices):
        TITLE = "title", "Title"
        SUMMARY = "summary", "Summary"
        OBJECTIVE = "objective", "Objective"
        ELIGIBILITY = "eligibility", "Eligibility"
        BENEFIT = "benefit", "Benefit"
        APPLICATION = "application", "Application"
        DOCUMENT = "document", "Required document"
        AUTHORITY = "authority", "Authority"
        AMOUNT = "amount", "Financial amount"
        GENERAL = "general", "General"

    candidate = models.ForeignKey(
        SchemeCandidate,
        on_delete=models.CASCADE,
        related_name="evidence",
    )
    chunk = models.ForeignKey(
        DocumentChunk,
        on_delete=models.PROTECT,
        related_name="candidate_evidence",
    )
    evidence_type = models.CharField(
        max_length=30,
        choices=EvidenceType.choices,
        default=EvidenceType.GENERAL,
    )
    quote = models.TextField()
    page_number = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["candidate", "page_number", "chunk__chunk_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["candidate", "chunk", "evidence_type"],
                name="unique_candidate_chunk_evidence_type",
            )
        ]

    def __str__(self) -> str:
        return f"{self.candidate_id} - {self.evidence_type}"


class EligibilityRuleCandidate(TimeStampedModel):
    class ReviewStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    candidate = models.ForeignKey(
        SchemeCandidate,
        on_delete=models.CASCADE,
        related_name="eligibility_rules",
    )
    source_chunk = models.ForeignKey(
        DocumentChunk,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="eligibility_rule_candidates",
    )
    field_name = models.CharField(max_length=100)
    operator = models.CharField(max_length=30)
    value = models.JSONField()
    unit = models.CharField(max_length=50, blank=True)
    human_text = models.TextField()
    confidence = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    review_status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.DRAFT,
    )
    review_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_eligibility_rule_candidates",
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def clean(self) -> None:
        super().clean()

        reviewed_statuses = {
            self.ReviewStatus.APPROVED,
            self.ReviewStatus.REJECTED,
        }

        if self.review_status in reviewed_statuses:
            errors = {}

            if self.reviewed_by_id is None:
                errors["reviewed_by"] = "A reviewed eligibility rule requires a reviewer."

            if self.reviewed_at is None:
                errors["reviewed_at"] = "A reviewed eligibility rule requires a review timestamp."

            if errors:
                raise ValidationError(errors)

    class Meta:
        ordering = ["candidate", "field_name", "created_at"]
        indexes = [
            models.Index(fields=["field_name", "operator"]),
            models.Index(fields=["review_status", "-confidence"]),
        ]

    def __str__(self) -> str:
        return f"{self.field_name} {self.operator} {self.value}"


class StructuredCandidateReviewMixin(models.Model):
    class ReviewStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    review_status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.DRAFT,
    )
    review_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def clean(self) -> None:
        super().clean()

        reviewed_statuses = {
            self.ReviewStatus.APPROVED,
            self.ReviewStatus.REJECTED,
        }

        if self.review_status in reviewed_statuses:
            errors = {}

            if self.reviewed_by_id is None:
                errors["reviewed_by"] = "A reviewed item requires a reviewer."

            if self.reviewed_at is None:
                errors["reviewed_at"] = "A reviewed item requires a review timestamp."

            if errors:
                raise ValidationError(errors)

    class Meta:
        abstract = True


class BenefitCandidate(
    StructuredCandidateReviewMixin,
    TimeStampedModel,
):
    candidate = models.ForeignKey(
        SchemeCandidate,
        on_delete=models.CASCADE,
        related_name="benefit_items",
    )
    source_chunk = models.ForeignKey(
        DocumentChunk,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="benefit_candidates",
    )
    benefit_type = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    amount_min = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
    )
    amount_max = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
    )
    currency = models.CharField(max_length=10, default="INR", blank=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        ordering = ["candidate", "created_at"]


class RequiredDocumentCandidate(
    StructuredCandidateReviewMixin,
    TimeStampedModel,
):
    candidate = models.ForeignKey(
        SchemeCandidate,
        on_delete=models.CASCADE,
        related_name="required_document_items",
    )
    source_chunk = models.ForeignKey(
        DocumentChunk,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="required_document_candidates",
    )
    name = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    mandatory = models.BooleanField(default=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        ordering = ["candidate", "name"]


class ApplicationStepCandidate(
    StructuredCandidateReviewMixin,
    TimeStampedModel,
):
    candidate = models.ForeignKey(
        SchemeCandidate,
        on_delete=models.CASCADE,
        related_name="application_steps",
    )
    source_chunk = models.ForeignKey(
        DocumentChunk,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="application_step_candidates",
    )
    step_number = models.PositiveIntegerField()
    instruction = models.TextField()
    url = models.URLField(max_length=2000, blank=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        ordering = ["candidate", "step_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["candidate", "step_number"],
                name="unique_candidate_application_step",
            )
        ]


class CandidateResolution(TimeStampedModel):
    class Classification(models.TextChoices):
        UNRESOLVED = "unresolved", "Unresolved"
        CANONICAL = "canonical", "Canonical scheme"
        SUPPORTING = "supporting", "Supporting evidence"
        DUPLICATE = "duplicate", "Duplicate candidate"
        REJECTED = "rejected", "Rejected extraction"

    candidate = models.OneToOneField(
        SchemeCandidate,
        on_delete=models.CASCADE,
        related_name="resolution",
    )
    canonical_title = models.CharField(
        max_length=500,
        blank=True,
    )
    resolved_authority = models.ForeignKey(
        "schemes.Authority",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="candidate_resolutions",
    )
    classification = models.CharField(
        max_length=20,
        choices=Classification.choices,
        default=Classification.UNRESOLVED,
    )
    primary_candidate = models.ForeignKey(
        SchemeCandidate,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="dependent_resolutions",
    )
    review_notes = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="candidate_resolutions",
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        ordering = [
            "classification",
            "canonical_title",
            "candidate",
        ]
        indexes = [
            models.Index(
                fields=[
                    "classification",
                    "-resolved_at",
                ]
            ),
            models.Index(
                fields=[
                    "resolved_authority",
                    "classification",
                ]
            ),
        ]

    def clean(self) -> None:
        super().clean()

        publishable = {
            self.Classification.CANONICAL,
            self.Classification.SUPPORTING,
        }
        primary_required = {
            self.Classification.SUPPORTING,
            self.Classification.DUPLICATE,
        }

        if self.classification in publishable:
            if not self.canonical_title.strip():
                raise ValidationError(
                    {"canonical_title": ("A canonical title is required for this classification.")}
                )

            if self.resolved_authority_id is None:
                raise ValidationError(
                    {
                        "resolved_authority": (
                            "A resolved authority is required for this classification."
                        )
                    }
                )

        if self.classification in primary_required and self.primary_candidate_id is None:
            raise ValidationError(
                {"primary_candidate": ("A primary candidate is required for this classification.")}
            )

        if self.primary_candidate_id is not None and self.primary_candidate_id == self.candidate_id:
            raise ValidationError({"primary_candidate": ("A candidate cannot reference itself.")})

    def __str__(self) -> str:
        return f"{self.candidate.title} - {self.classification}"


class CandidateCuration(TimeStampedModel):
    class ReviewStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    candidate = models.OneToOneField(
        SchemeCandidate,
        on_delete=models.CASCADE,
        related_name="curation",
    )
    canonical_summary = models.TextField()
    canonical_objective = models.TextField(blank=True)
    canonical_eligibility_text = models.TextField(blank=True)
    official_url = models.URLField(max_length=2000)
    application_url = models.URLField(
        max_length=2000,
        blank=True,
    )
    canonical_support_types = models.JSONField(
        null=True,
        blank=True,
        default=None,
    )
    canonical_categories = models.JSONField(
        null=True,
        blank=True,
        default=None,
    )
    canonical_benefits = models.JSONField(
        null=True,
        blank=True,
        default=None,
    )
    canonical_required_documents = models.JSONField(
        null=True,
        blank=True,
        default=None,
    )
    canonical_application_steps = models.JSONField(
        null=True,
        blank=True,
        default=None,
    )
    review_status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.DRAFT,
    )
    review_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="candidate_curations",
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        ordering = ["review_status", "candidate"]

    def clean(self) -> None:
        super().clean()

        errors = {}

        for field_name in (
            "canonical_support_types",
            "canonical_categories",
        ):
            value = getattr(self, field_name)

            if value is None:
                continue

            if not isinstance(value, list):
                errors[field_name] = "The curated replacement must be a JSON list."
                continue

            if any(not isinstance(item, str) or not item.strip() for item in value):
                errors[field_name] = "Every curated value must be a non-empty string."

        for field_name in (
            "canonical_benefits",
            "canonical_required_documents",
            "canonical_application_steps",
        ):
            value = getattr(self, field_name)

            if value is None:
                continue

            if not isinstance(value, list):
                errors[field_name] = "The curated replacement must be a JSON list."
                continue

            if any(not isinstance(item, dict) for item in value):
                errors[field_name] = "Every curated row must be a JSON object."

        if isinstance(self.canonical_benefits, list):
            for row in self.canonical_benefits:
                if not isinstance(row, dict):
                    continue

                description = row.get("description", "")
                currency = row.get("currency", "INR")

                if not isinstance(description, str) or not description.strip():
                    errors["canonical_benefits"] = "Every curated benefit requires a description."
                    break

                if not isinstance(currency, str) or len(currency.strip()) != 3:
                    errors["canonical_benefits"] = (
                        "Every curated benefit requires a three-letter currency code."
                    )
                    break

        if isinstance(self.canonical_required_documents, list):
            for row in self.canonical_required_documents:
                if not isinstance(row, dict):
                    continue

                name = row.get("name", "")
                if not isinstance(name, str) or not name.strip():
                    errors["canonical_required_documents"] = (
                        "Every curated required document requires a name."
                    )
                    break

        if isinstance(self.canonical_application_steps, list):
            step_numbers = []

            for row in self.canonical_application_steps:
                if not isinstance(row, dict):
                    continue

                step_number = row.get("step_number")
                instruction = row.get("instruction", "")

                if not isinstance(step_number, int) or step_number < 1:
                    errors["canonical_application_steps"] = (
                        "Every curated application step requires a positive integer step number."
                    )
                    break

                if not isinstance(instruction, str) or not instruction.strip():
                    errors["canonical_application_steps"] = (
                        "Every curated application step requires an instruction."
                    )
                    break

                step_numbers.append(step_number)

            if step_numbers and len(step_numbers) != len(set(step_numbers)):
                errors["canonical_application_steps"] = (
                    "Curated application step numbers must be unique."
                )

        if errors:
            raise ValidationError(errors)

        if self.review_status == self.ReviewStatus.APPROVED:
            errors = {}

            if not self.canonical_summary.strip():
                errors["canonical_summary"] = "An approved curation requires a canonical summary."

            if not self.official_url.strip():
                errors["official_url"] = "An approved curation requires an official scheme URL."

            if self.reviewed_by_id is None:
                errors["reviewed_by"] = "An approved curation requires a reviewer."

            if self.reviewed_at is None:
                errors["reviewed_at"] = "An approved curation requires a review timestamp."

            if errors:
                raise ValidationError(errors)

    def __str__(self) -> str:
        return f"{self.candidate.title} - {self.review_status}"


class CandidatePublication(TimeStampedModel):
    class Role(models.TextChoices):
        PRIMARY = "primary", "Primary"
        SUPPORTING = "supporting", "Supporting"

    candidate = models.OneToOneField(
        SchemeCandidate,
        on_delete=models.PROTECT,
        related_name="publication",
    )
    scheme = models.ForeignKey(
        "schemes.Scheme",
        on_delete=models.PROTECT,
        related_name="candidate_publications",
    )
    scheme_version = models.ForeignKey(
        "schemes.SchemeVersion",
        on_delete=models.PROTECT,
        related_name="candidate_publications",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.PRIMARY,
    )
    publication_hash = models.CharField(max_length=64, db_index=True)
    published_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="candidate_publications",
    )
    published_at = models.DateTimeField()
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-published_at", "candidate"]
        constraints = [
            models.UniqueConstraint(
                fields=["scheme_version"],
                condition=models.Q(role="primary"),
                name="unique_primary_candidate_publication",
            ),
        ]
        indexes = [
            models.Index(fields=["role", "-published_at"]),
            models.Index(fields=["scheme", "scheme_version"]),
        ]

    def clean(self) -> None:
        super().clean()
        if (
            self.scheme_version_id is not None
            and self.scheme_id is not None
            and self.scheme_version.scheme_id != self.scheme_id
        ):
            raise ValidationError(
                {"scheme_version": ("The scheme version must belong to the selected scheme.")}
            )

    def __str__(self) -> str:
        return (
            f"{self.candidate.title} → {self.scheme.canonical_name} "
            f"v{self.scheme_version.version_number}"
        )


class PublishedEvidence(TimeStampedModel):
    publication = models.ForeignKey(
        CandidatePublication,
        on_delete=models.CASCADE,
        related_name="evidence_snapshots",
    )
    candidate_evidence = models.ForeignKey(
        CandidateEvidence,
        on_delete=models.PROTECT,
        related_name="published_snapshots",
    )
    evidence_type = models.CharField(max_length=30)
    quote = models.TextField()
    page_number = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["publication", "page_number", "candidate_evidence"]
        constraints = [
            models.UniqueConstraint(
                fields=["publication", "candidate_evidence"],
                name="unique_publication_candidate_evidence",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.publication_id} - {self.evidence_type} - page {self.page_number or '-'}"

class ExternalSchemeDataset(TimeStampedModel):
    dataset_key = models.CharField(
        max_length=150,
        unique=True,
    )
    dataset_name = models.CharField(max_length=500)
    source_filename = models.CharField(max_length=500)
    source_sheet = models.CharField(max_length=250, blank=True)
    source_row_count = models.PositiveIntegerField(default=0)
    record_count = models.PositiveIntegerField(default=0)
    normalization_version = models.CharField(max_length=100)
    content_sha256 = models.CharField(
        max_length=64,
        db_index=True,
    )
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["dataset_key"]

    def __str__(self) -> str:
        return self.dataset_name


class ExternalSchemeRecord(TimeStampedModel):
    class ReviewStatus(models.TextChoices):
        NEEDS_REVIEW = "needs_review", "Needs review"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    dataset = models.ForeignKey(
        ExternalSchemeDataset,
        on_delete=models.CASCADE,
        related_name="records",
    )
    external_id = models.CharField(max_length=150)
    scheme_name = models.CharField(max_length=500)
    normalized_name = models.CharField(
        max_length=500,
        db_index=True,
    )

    ministry = models.TextField(blank=True)
    department = models.TextField(blank=True)
    sector = models.TextField(blank=True)
    startup_stage = models.JSONField(default=list, blank=True)
    startup_type = models.TextField(blank=True)
    industry = models.JSONField(default=list, blank=True)
    central_state = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=250, blank=True)

    funding_type = models.TextField(blank=True)
    funding_amount = models.TextField(blank=True)
    financial_instrument = models.TextField(blank=True)
    eligibility = models.TextField(blank=True)
    women_eligible = models.CharField(max_length=100, blank=True)
    sc_st_eligible = models.CharField(max_length=100, blank=True)
    dpiit_required = models.CharField(max_length=100, blank=True)
    startup_age_limit = models.TextField(blank=True)
    revenue_criteria = models.TextField(blank=True)
    tax_benefits = models.TextField(blank=True)

    documents_required = models.JSONField(default=list, blank=True)
    application_process = models.TextField(blank=True)
    official_website_label = models.TextField(blank=True)
    official_application_url = models.TextField(blank=True)
    source_portal = models.TextField(blank=True)
    claimed_last_updated = models.CharField(
        max_length=100,
        blank=True,
    )

    source_row_number = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    quality_warnings = models.JSONField(default=list, blank=True)
    raw_row = models.JSONField(default=dict, blank=True)
    source_rows = models.JSONField(default=list, blank=True)
    external_ids = models.JSONField(default=list, blank=True)
    record_sha256 = models.CharField(
        max_length=64,
        db_index=True,
    )

    review_status = models.CharField(
        max_length=30,
        choices=ReviewStatus.choices,
        default=ReviewStatus.NEEDS_REVIEW,
    )
    review_notes = models.TextField(blank=True)

    matched_candidate = models.ForeignKey(
        SchemeCandidate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="external_scheme_matches",
    )
    matched_scheme = models.ForeignKey(
        "schemes.Scheme",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="external_scheme_matches",
    )

    class Meta:
        ordering = [
            "scheme_name",
            "dataset",
            "external_id",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["dataset", "external_id"],
                name="unique_external_scheme_dataset_id",
            ),
        ]
        indexes = [
            models.Index(
                fields=[
                    "dataset",
                    "review_status",
                    "normalized_name",
                ],
            ),
        ]

    def __str__(self) -> str:
        return f"{self.scheme_name} ({self.dataset.dataset_key})"

class ExternalKnowledgeDataset(TimeStampedModel):
    class DatasetKind(models.TextChoices):
        CAPITAL_SUPPORT = (
            "capital_support",
            "Capital support",
        )
        CERTIFICATION_REQUIREMENT = (
            "certification_requirement",
            "Certification requirement",
        )

    dataset_kind = models.CharField(
        max_length=50,
        choices=DatasetKind.choices,
    )
    dataset_key = models.CharField(
        max_length=150,
        unique=True,
    )
    dataset_name = models.CharField(max_length=500)
    source_filename = models.CharField(max_length=500)
    source_sheet = models.CharField(
        max_length=250,
        blank=True,
    )
    source_row_count = models.PositiveIntegerField(
        default=0,
    )
    record_count = models.PositiveIntegerField(default=0)
    normalization_version = models.CharField(
        max_length=100,
    )
    content_sha256 = models.CharField(
        max_length=64,
        db_index=True,
    )
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        ordering = [
            "dataset_kind",
            "dataset_key",
        ]
        indexes = [
            models.Index(
                fields=[
                    "dataset_kind",
                    "is_active",
                ],
            ),
        ]

    def __str__(self) -> str:
        return self.dataset_name


class ExternalCapitalSupportRecord(TimeStampedModel):
    class ReviewStatus(models.TextChoices):
        NEEDS_REVIEW = (
            "needs_review",
            "Needs review",
        )
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    dataset = models.ForeignKey(
        ExternalKnowledgeDataset,
        on_delete=models.CASCADE,
        related_name="capital_support_records",
    )
    external_id = models.CharField(max_length=150)

    support_name = models.CharField(max_length=500)
    support_type = models.CharField(
        max_length=150,
        blank=True,
    )
    scheme_name = models.CharField(
        max_length=500,
        blank=True,
    )
    normalized_name = models.CharField(
        max_length=500,
        db_index=True,
    )

    ministry = models.TextField(blank=True)
    implementing_agency = models.TextField(blank=True)
    funding_category = models.TextField(blank=True)

    minimum_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
    )
    maximum_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
    )
    raw_minimum_amount = models.TextField(blank=True)
    raw_maximum_amount = models.TextField(blank=True)
    currency = models.CharField(
        max_length=10,
        default="INR",
        blank=True,
    )

    interest_rate_text = models.TextField(blank=True)
    collateral_required_text = models.TextField(
        blank=True,
    )
    repayment_required_text = models.TextField(
        blank=True,
    )

    startup_stage = models.JSONField(
        default=list,
        blank=True,
    )
    industry = models.JSONField(
        default=list,
        blank=True,
    )
    eligible_entity = models.TextField(blank=True)
    state = models.CharField(
        max_length=250,
        blank=True,
    )
    funding_purpose = models.TextField(blank=True)
    claimed_scheme_status = models.CharField(
        max_length=100,
        blank=True,
    )

    source_priority_score = (
        models.PositiveSmallIntegerField(
            null=True,
            blank=True,
        )
    )
    source_ai_recommendation_weight = (
        models.DecimalField(
            max_digits=6,
            decimal_places=5,
            null=True,
            blank=True,
        )
    )
    remarks = models.TextField(blank=True)

    matched_external_scheme_ids = models.JSONField(
        default=list,
        blank=True,
    )
    matched_external_schemes = models.ManyToManyField(
        ExternalSchemeRecord,
        blank=True,
        related_name="capital_support_records",
    )
    matched_scheme = models.ForeignKey(
        "schemes.Scheme",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="external_capital_support_matches",
    )

    review_status = models.CharField(
        max_length=30,
        choices=ReviewStatus.choices,
        default=ReviewStatus.NEEDS_REVIEW,
    )
    review_notes = models.TextField(blank=True)

    quality_warnings = models.JSONField(
        default=list,
        blank=True,
    )
    source_row_number = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    raw_row = models.JSONField(
        default=dict,
        blank=True,
    )
    record_sha256 = models.CharField(
        max_length=64,
        db_index=True,
    )

    class Meta:
        ordering = [
            "support_name",
            "dataset",
            "external_id",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "dataset",
                    "external_id",
                ],
                name=(
                    "unique_external_capital_dataset_id"
                ),
            ),
        ]
        indexes = [
            models.Index(
                fields=[
                    "dataset",
                    "review_status",
                    "normalized_name",
                ],
            ),
            models.Index(
                fields=[
                    "support_type",
                    "review_status",
                ],
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.support_name} "
            f"({self.dataset.dataset_key})"
        )


class ExternalCertificationRequirementRecord(
    TimeStampedModel,
):
    class ReviewStatus(models.TextChoices):
        NEEDS_REVIEW = (
            "needs_review",
            "Needs review",
        )
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    dataset = models.ForeignKey(
        ExternalKnowledgeDataset,
        on_delete=models.CASCADE,
        related_name=(
            "certification_requirement_records"
        ),
    )
    external_id = models.CharField(max_length=150)

    certificate_name = models.CharField(
        max_length=500,
    )
    normalized_name = models.CharField(
        max_length=500,
        db_index=True,
    )
    certificate_type = models.CharField(
        max_length=250,
        blank=True,
    )
    description = models.TextField(blank=True)

    industry = models.JSONField(
        default=list,
        blank=True,
    )
    startup_stage = models.JSONField(
        default=list,
        blank=True,
    )
    requirement_level = models.CharField(
        max_length=100,
        blank=True,
    )

    eligibility = models.TextField(blank=True)
    benefits = models.TextField(blank=True)
    validity = models.TextField(blank=True)
    renewal_period = models.TextField(blank=True)
    issuing_authority = models.TextField(blank=True)
    official_document_text = models.TextField(
        blank=True,
    )
    official_apply_url = models.TextField(blank=True)

    source_priority_score = (
        models.PositiveSmallIntegerField(
            null=True,
            blank=True,
        )
    )
    display_eligible = models.BooleanField(
        default=False,
    )

    review_status = models.CharField(
        max_length=30,
        choices=ReviewStatus.choices,
        default=ReviewStatus.NEEDS_REVIEW,
    )
    review_notes = models.TextField(blank=True)

    quality_warnings = models.JSONField(
        default=list,
        blank=True,
    )
    source_row_number = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    raw_row = models.JSONField(
        default=dict,
        blank=True,
    )
    record_sha256 = models.CharField(
        max_length=64,
        db_index=True,
    )

    class Meta:
        ordering = [
            "certificate_name",
            "dataset",
            "external_id",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "dataset",
                    "external_id",
                ],
                name=(
                    "unique_external_cert_dataset_id"
                ),
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        review_status__in=[
                            "needs_review",
                            "verified",
                        ],
                    )
                    | models.Q(
                        display_eligible=False,
                    )
                ),
                name=(
                    "external_cert_rejected_not_displayable"
                ),
            ),
        ]
        indexes = [
            models.Index(
                fields=[
                    "dataset",
                    "review_status",
                    "display_eligible",
                ],
            ),
            models.Index(
                fields=[
                    "certificate_type",
                    "review_status",
                ],
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.certificate_name} "
            f"({self.dataset.dataset_key})"
        )
