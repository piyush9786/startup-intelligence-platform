from __future__ import annotations

from contextlib import suppress
from datetime import date
from hashlib import sha256
from typing import Any
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import OuterRef, Subquery

from apps.accounts.models import User
from apps.recommendations.models import (
    EligibilityVerificationDecision,
    EligibilityVerificationEvidence,
    EligibilityVerificationSubmission,
)
from apps.sources.services.storage import (
    delete_object,
    upload_bytes,
)
from apps.startups.models import StartupProfile

ALLOWED_REVIEWER_ROLES = {
    User.Role.REVIEWER,
    User.Role.ADMIN,
}


def _validate_submitter(
    *,
    startup_profile: Any,
    submitted_by: Any,
) -> None:
    if submitted_by is None or not getattr(
        submitted_by,
        "is_authenticated",
        False,
    ):
        raise ValidationError("An authenticated submitter is required.")

    if not getattr(submitted_by, "is_active", False):
        raise ValidationError("The submitter account is inactive.")

    if not getattr(submitted_by, "is_staff", False) and startup_profile.owner_id != submitted_by.id:
        raise ValidationError("Only the startup owner or staff may submit verification evidence.")


def _validate_reviewer(reviewer: Any) -> None:
    if reviewer is None or not getattr(
        reviewer,
        "is_authenticated",
        False,
    ):
        raise ValidationError("An authenticated reviewer is required.")

    if not getattr(reviewer, "is_active", False):
        raise ValidationError("The reviewer account is inactive.")

    if (
        not getattr(reviewer, "is_superuser", False)
        and getattr(reviewer, "role", None) not in ALLOWED_REVIEWER_ROLES
    ):
        raise ValidationError(
            "Only reviewers or administrators may review eligibility verification submissions."
        )


def _submission_snapshot(
    submission: EligibilityVerificationSubmission,
) -> dict[str, Any]:
    return {
        "id": str(submission.id),
        "startup_profile_id": str(submission.startup_profile_id),
        "scheme_version_id": str(submission.scheme_version_id),
        "eligibility_rule_id": str(submission.eligibility_rule_id),
        "submitted_by_id": (
            str(submission.submitted_by_id) if submission.submitted_by_id else None
        ),
        "supersedes_id": (str(submission.supersedes_id) if submission.supersedes_id else None),
        "claim_value": submission.claim_value,
        "claim_text": submission.claim_text,
        "created_at": submission.created_at.isoformat(),
    }


def _rule_snapshot(
    submission: EligibilityVerificationSubmission,
) -> dict[str, Any]:
    rule = submission.eligibility_rule
    return {
        "id": str(rule.id),
        "scheme_version_id": str(rule.scheme_version_id),
        "field_path": rule.field_path,
        "operator": rule.operator,
        "expected_value": rule.expected_value,
        "mandatory": rule.mandatory,
        "rule_group": rule.rule_group,
        "evidence_text": rule.evidence_text,
        "evidence_page": rule.evidence_page,
        "manually_verified": rule.manually_verified,
    }


def _evidence_snapshot(
    submission: EligibilityVerificationSubmission,
) -> list[dict[str, Any]]:
    return [
        {
            "id": str(evidence.id),
            "filename": evidence.filename,
            "mime_type": evidence.mime_type,
            "size_bytes": evidence.size_bytes,
            "content_hash": evidence.content_hash,
            "storage_key": evidence.storage_key,
            "uploaded_by_id": (str(evidence.uploaded_by_id) if evidence.uploaded_by_id else None),
            "created_at": evidence.created_at.isoformat(),
        }
        for evidence in submission.evidence.order_by(
            "created_at",
            "id",
        )
    ]


def _normalized_evidence_filename(filename: str) -> str:
    normalized = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not normalized or normalized in {".", ".."}:
        raise ValidationError({"file": "A valid filename is required."})
    return normalized


def add_verification_evidence(
    *,
    submission: EligibilityVerificationSubmission,
    uploaded_by: Any,
    uploaded_file: Any,
) -> EligibilityVerificationEvidence:
    if uploaded_file is None:
        raise ValidationError({"file": "An evidence file is required."})

    filename = _normalized_evidence_filename(
        str(getattr(uploaded_file, "name", "")),
    )
    content = uploaded_file.read()

    if not isinstance(content, bytes) or not content:
        raise ValidationError({"file": "The evidence file must not be empty."})

    content_hash = sha256(content).hexdigest()
    content_type = getattr(uploaded_file, "content_type", "") or "application/octet-stream"

    uploaded_storage_key: str | None = None

    try:
        with transaction.atomic():
            locked_submission = (
                EligibilityVerificationSubmission.objects.select_for_update()
                .select_related("startup_profile")
                .get(pk=submission.pk)
            )

            _validate_submitter(
                startup_profile=locked_submission.startup_profile,
                submitted_by=uploaded_by,
            )

            if not locked_submission.is_current:
                raise ValidationError("Evidence may only be added to the current submission.")

            if locked_submission.decisions.exists():
                raise ValidationError(
                    "A reviewed submission is frozen. "
                    "Create a new submission to provide more evidence."
                )

            if locked_submission.evidence.filter(
                content_hash=content_hash,
            ).exists():
                raise ValidationError({"file": "This evidence file has already been submitted."})

            uploaded_storage_key = (
                "eligibility/"
                f"{locked_submission.startup_profile_id}/"
                f"{locked_submission.id}/"
                f"{uuid4().hex}-{filename}"
            )

            upload_bytes(
                object_key=uploaded_storage_key,
                content=content,
                content_type=content_type,
                bucket_name=settings.MINIO_BUCKET_STARTUP_EVIDENCE,
            )

            return EligibilityVerificationEvidence.objects.create(
                submission=locked_submission,
                uploaded_by=uploaded_by,
                filename=filename,
                mime_type=content_type,
                size_bytes=len(content),
                content_hash=content_hash,
                storage_key=uploaded_storage_key,
            )
    except Exception:
        if uploaded_storage_key is not None:
            with suppress(Exception):
                delete_object(
                    uploaded_storage_key,
                    bucket_name=(settings.MINIO_BUCKET_STARTUP_EVIDENCE),
                )
        raise


@transaction.atomic
def create_verification_submission(
    *,
    startup_profile: Any,
    scheme_version: Any,
    eligibility_rule: Any,
    submitted_by: Any,
    claim_value: Any = None,
    claim_text: str = "",
) -> EligibilityVerificationSubmission:
    if eligibility_rule.scheme_version_id != scheme_version.id:
        raise ValidationError("The eligibility rule must belong to the selected scheme version.")

    if not eligibility_rule.field_path.startswith("manual."):
        raise ValidationError(
            {
                "eligibility_rule": (
                    "Verification submissions are only accepted for manual eligibility gates."
                )
            }
        )

    if claim_value is None and not claim_text.strip():
        raise ValidationError("A structured claim value or explanatory claim text is required.")

    # Lock a stable parent row so even the first submission for this
    # startup and rule is serialized. Locking only an existing current
    # submission cannot protect the no-row-yet case.
    locked_startup_profile = (
        StartupProfile.objects.select_for_update()
        .only(
            "id",
            "owner_id",
        )
        .get(pk=startup_profile.pk)
    )

    _validate_submitter(
        startup_profile=locked_startup_profile,
        submitted_by=submitted_by,
    )

    current_submission = (
        EligibilityVerificationSubmission.objects.select_for_update()
        .filter(
            startup_profile=locked_startup_profile,
            eligibility_rule=eligibility_rule,
            is_current=True,
        )
        .order_by("-created_at", "-id")
        .first()
    )

    if current_submission is not None:
        EligibilityVerificationSubmission.objects.filter(
            pk=current_submission.pk,
        ).update(is_current=False)

    return EligibilityVerificationSubmission.objects.create(
        startup_profile=locked_startup_profile,
        scheme_version=scheme_version,
        eligibility_rule=eligibility_rule,
        submitted_by=submitted_by,
        supersedes=current_submission,
        is_current=True,
        claim_value=claim_value,
        claim_text=claim_text.strip(),
    )


@transaction.atomic
def review_verification_submission(
    *,
    submission: EligibilityVerificationSubmission,
    reviewer: Any,
    outcome: str,
    verified_value: Any = None,
    review_notes: str = "",
    valid_from: date,
    expires_on: date | None = None,
) -> EligibilityVerificationDecision:
    _validate_reviewer(reviewer)

    locked_submission = (
        EligibilityVerificationSubmission.objects.select_for_update()
        .select_related(
            "startup_profile",
            "scheme_version",
            "eligibility_rule",
        )
        .prefetch_related("evidence")
        .get(pk=submission.pk)
    )

    if not locked_submission.is_current:
        raise ValidationError("Only the current verification submission may be reviewed.")

    if outcome not in EligibilityVerificationDecision.Outcome.values:
        raise ValidationError({"outcome": "Unsupported review outcome."})

    if outcome == EligibilityVerificationDecision.Outcome.APPROVED and verified_value is None:
        raise ValidationError({"verified_value": "Approved decisions require a verified value."})

    if outcome == EligibilityVerificationDecision.Outcome.REJECTED and verified_value is not None:
        raise ValidationError(
            {"verified_value": ("Rejected decisions cannot include a verified value.")}
        )

    if expires_on is not None and expires_on < valid_from:
        raise ValidationError({"expires_on": "Expiry cannot precede the valid-from date."})

    return EligibilityVerificationDecision.objects.create(
        submission=locked_submission,
        reviewed_by=reviewer,
        outcome=outcome,
        verified_value=verified_value,
        review_notes=review_notes.strip(),
        valid_from=valid_from,
        expires_on=expires_on,
        submission_snapshot=_submission_snapshot(
            locked_submission,
        ),
        rule_snapshot=_rule_snapshot(
            locked_submission,
        ),
        evidence_snapshot=_evidence_snapshot(
            locked_submission,
        ),
    )


def reviewer_verification_queue(
    *,
    as_of_date: date,
) -> list[dict[str, Any]]:
    latest_effective_decision_id = (
        EligibilityVerificationDecision.objects.filter(
            submission_id=OuterRef("pk"),
            valid_from__lte=as_of_date,
        )
        .order_by(
            "-valid_from",
            "-created_at",
            "-id",
        )
        .values("id")[:1]
    )

    submissions = list(
        EligibilityVerificationSubmission.objects.filter(
            is_current=True,
        )
        .annotate(
            latest_effective_decision_id=Subquery(
                latest_effective_decision_id,
            ),
        )
        .select_related(
            "startup_profile",
            "startup_profile__owner",
            "scheme_version",
            "scheme_version__scheme",
            "eligibility_rule",
            "submitted_by",
        )
        .prefetch_related("evidence")
        .order_by("-created_at", "-id")
    )

    decision_ids = [
        submission.latest_effective_decision_id
        for submission in submissions
        if submission.latest_effective_decision_id is not None
    ]
    decisions_by_id = {
        decision.id: decision
        for decision in EligibilityVerificationDecision.objects.filter(
            id__in=decision_ids,
        ).select_related("reviewed_by")
    }

    results: list[dict[str, Any]] = []

    for submission in submissions:
        decision = decisions_by_id.get(
            submission.latest_effective_decision_id,
        )
        submission_status = "pending"

        if decision is not None:
            if decision.outcome == EligibilityVerificationDecision.Outcome.REJECTED:
                submission_status = "rejected"
            elif decision.expires_on is not None and decision.expires_on < as_of_date:
                submission_status = "expired"
            else:
                submission_status = "approved"

        evidence_items = [
            {
                "id": str(evidence.id),
                "filename": evidence.filename,
                "mime_type": evidence.mime_type,
                "size_bytes": evidence.size_bytes,
                "content_hash": evidence.content_hash,
                "uploaded_by_id": (
                    str(evidence.uploaded_by_id) if evidence.uploaded_by_id else None
                ),
                "created_at": evidence.created_at.isoformat(),
            }
            for evidence in submission.evidence.all()
        ]

        results.append(
            {
                "id": str(submission.id),
                "status": submission_status,
                "startup_profile_id": str(
                    submission.startup_profile_id,
                ),
                "startup_name": (submission.startup_profile.startup_name),
                "startup_owner_id": str(
                    submission.startup_profile.owner_id,
                ),
                "scheme_id": str(
                    submission.scheme_version.scheme_id,
                ),
                "scheme_version_id": str(
                    submission.scheme_version_id,
                ),
                "scheme_name": (submission.scheme_version.scheme.canonical_name),
                "eligibility_rule_id": str(
                    submission.eligibility_rule_id,
                ),
                "field_path": (submission.eligibility_rule.field_path),
                "operator": submission.eligibility_rule.operator,
                "expected_value": (submission.eligibility_rule.expected_value),
                "mandatory": (submission.eligibility_rule.mandatory),
                "evidence_text": (submission.eligibility_rule.evidence_text),
                "evidence_page": (submission.eligibility_rule.evidence_page),
                "submitted_by_id": (
                    str(submission.submitted_by_id) if submission.submitted_by_id else None
                ),
                "claim_value": submission.claim_value,
                "claim_text": submission.claim_text,
                "evidence_count": len(evidence_items),
                "evidence": evidence_items,
                "created_at": submission.created_at.isoformat(),
                "decision": (
                    {
                        "id": str(decision.id),
                        "reviewed_by_id": str(
                            decision.reviewed_by_id,
                        ),
                        "outcome": decision.outcome,
                        "verified_value": decision.verified_value,
                        "review_notes": decision.review_notes,
                        "valid_from": (decision.valid_from.isoformat()),
                        "expires_on": (
                            decision.expires_on.isoformat() if decision.expires_on else None
                        ),
                        "created_at": (decision.created_at.isoformat()),
                    }
                    if decision is not None
                    else None
                ),
            }
        )

    return results


def verification_gate_statuses(
    *,
    startup_profile: Any,
    scheme_version: Any,
    as_of_date: date,
) -> list[dict[str, Any]]:
    rules = list(
        scheme_version.eligibility_rules.filter(
            field_path__startswith="manual.",
        ).order_by(
            "rule_group",
            "field_path",
            "id",
        )
    )

    latest_effective_decision_id = (
        EligibilityVerificationDecision.objects.filter(
            submission_id=OuterRef("pk"),
            valid_from__lte=as_of_date,
        )
        .order_by(
            "-valid_from",
            "-created_at",
            "-id",
        )
        .values("id")[:1]
    )

    submissions = list(
        EligibilityVerificationSubmission.objects.filter(
            startup_profile=startup_profile,
            scheme_version=scheme_version,
            is_current=True,
        )
        .annotate(
            latest_effective_decision_id=Subquery(
                latest_effective_decision_id,
            ),
        )
        .prefetch_related("evidence")
    )

    submissions_by_rule = {submission.eligibility_rule_id: submission for submission in submissions}

    decision_ids = [
        submission.latest_effective_decision_id
        for submission in submissions
        if submission.latest_effective_decision_id is not None
    ]
    decisions_by_id = {
        decision.id: decision
        for decision in EligibilityVerificationDecision.objects.filter(
            id__in=decision_ids,
        )
    }

    results: list[dict[str, Any]] = []

    for rule in rules:
        submission = submissions_by_rule.get(rule.id)
        decision = None
        gate_status = "not_submitted"

        if submission is not None:
            gate_status = "pending"
            decision = decisions_by_id.get(
                submission.latest_effective_decision_id,
            )

            if decision is not None:
                if decision.outcome == EligibilityVerificationDecision.Outcome.REJECTED:
                    gate_status = "rejected"
                elif decision.expires_on is not None and decision.expires_on < as_of_date:
                    gate_status = "expired"
                else:
                    gate_status = "approved"

        results.append(
            {
                "eligibility_rule_id": str(rule.id),
                "field_path": rule.field_path,
                "operator": rule.operator,
                "expected_value": rule.expected_value,
                "mandatory": rule.mandatory,
                "rule_group": rule.rule_group,
                "evidence_text": rule.evidence_text,
                "evidence_page": rule.evidence_page,
                "status": gate_status,
                "resolved": gate_status == "approved",
                "submission": (
                    {
                        "id": str(submission.id),
                        "claim_value": submission.claim_value,
                        "claim_text": submission.claim_text,
                        "evidence_count": len(
                            submission.evidence.all(),
                        ),
                        "created_at": (submission.created_at.isoformat()),
                    }
                    if submission is not None
                    else None
                ),
                "decision": (
                    {
                        "id": str(decision.id),
                        "outcome": decision.outcome,
                        "verified_value": decision.verified_value,
                        "review_notes": decision.review_notes,
                        "valid_from": decision.valid_from.isoformat(),
                        "expires_on": (
                            decision.expires_on.isoformat() if decision.expires_on else None
                        ),
                        "created_at": decision.created_at.isoformat(),
                    }
                    if decision is not None
                    else None
                ),
            }
        )

    return results


def approved_verification_values(
    *,
    startup_profile: Any,
    scheme_version: Any,
    as_of_date: date,
) -> dict[str, dict[str, Any]]:
    latest_decision_id = (
        EligibilityVerificationDecision.objects.filter(
            submission_id=OuterRef("pk"),
            valid_from__lte=as_of_date,
        )
        .order_by(
            "-valid_from",
            "-created_at",
            "-id",
        )
        .values("id")[:1]
    )

    current_submissions = (
        EligibilityVerificationSubmission.objects.filter(
            startup_profile=startup_profile,
            scheme_version=scheme_version,
            is_current=True,
        )
        .annotate(
            latest_decision_id=Subquery(latest_decision_id),
        )
        .exclude(latest_decision_id=None)
    )

    latest_decisions = {
        decision.id: decision
        for decision in EligibilityVerificationDecision.objects.filter(
            id__in=[submission.latest_decision_id for submission in current_submissions],
            outcome=EligibilityVerificationDecision.Outcome.APPROVED,
        ).select_related(
            "submission",
            "submission__eligibility_rule",
        )
    }

    approved: dict[str, dict[str, Any]] = {}

    for submission in current_submissions:
        decision = latest_decisions.get(
            submission.latest_decision_id,
        )
        if decision is None:
            continue

        if decision.expires_on is not None and decision.expires_on < as_of_date:
            continue

        approved[str(submission.eligibility_rule_id)] = {
            "value": decision.verified_value,
            "decision_id": str(decision.id),
            "submission_id": str(submission.id),
            "valid_from": decision.valid_from.isoformat(),
            "expires_on": (decision.expires_on.isoformat() if decision.expires_on else None),
        }

    return approved
