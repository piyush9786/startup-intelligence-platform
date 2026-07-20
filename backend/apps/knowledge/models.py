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

    class Meta:
        ordering = ["candidate", "field_name", "created_at"]
        indexes = [
            models.Index(fields=["field_name", "operator"]),
            models.Index(fields=["review_status", "-confidence"]),
        ]

    def __str__(self) -> str:
        return f"{self.field_name} {self.operator} {self.value}"


class BenefitCandidate(TimeStampedModel):
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


class RequiredDocumentCandidate(TimeStampedModel):
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


class ApplicationStepCandidate(TimeStampedModel):
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
                    {
                        "canonical_title": (
                            "A canonical title is required "
                            "for this classification."
                        )
                    }
                )

            if self.resolved_authority_id is None:
                raise ValidationError(
                    {
                        "resolved_authority": (
                            "A resolved authority is required "
                            "for this classification."
                        )
                    }
                )

        if (
            self.classification in primary_required
            and self.primary_candidate_id is None
        ):
            raise ValidationError(
                {
                    "primary_candidate": (
                        "A primary candidate is required "
                        "for this classification."
                    )
                }
            )

        if (
            self.primary_candidate_id is not None
            and self.primary_candidate_id
            == self.candidate_id
        ):
            raise ValidationError(
                {
                    "primary_candidate": (
                        "A candidate cannot reference itself."
                    )
                }
            )

    def __str__(self) -> str:
        return (
            f"{self.candidate.title} - "
            f"{self.classification}"
        )
