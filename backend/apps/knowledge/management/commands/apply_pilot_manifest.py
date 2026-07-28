from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.knowledge.models import (
    CandidateCuration,
    CandidatePublication,
    CandidateResolution,
    EligibilityRuleCandidate,
    SchemeCandidate,
)
from apps.knowledge.services.curation import (
    curate_candidate,
    review_eligibility_rule,
    review_structured_item,
)
from apps.knowledge.services.resolution import resolve_candidate
from apps.schemes.models import Authority
from apps.schemes.services.authority_normalizer import (
    find_authority_by_name,
    normalize_authority_name,
    register_authority_alias,
)

DEFAULT_MANIFEST = (
    Path(settings.BASE_DIR) / "apps" / "knowledge" / "pilot" / "manifests" / "startup_pilot_v1.json"
)

STRUCTURED_SPECS = {
    "benefits": "benefit_items",
    "required_documents": "required_document_items",
    "application_steps": "application_steps",
}


@dataclass(frozen=True)
class CandidatePlan:
    manifest_row: dict[str, Any]
    candidate: SchemeCandidate
    rules: dict[str, EligibilityRuleCandidate]
    structured_items: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class PilotPlan:
    manifest: dict[str, Any]
    reviewer: Any
    authority: Authority | None
    candidates: list[CandidatePlan]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CommandError(message)


def _read_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CommandError(f"Could not read manifest: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CommandError(f"Manifest is not valid JSON: {exc}") from exc

    _require(isinstance(manifest, dict), "Manifest root must be a JSON object.")
    _require(manifest.get("schema_version") == 1, "Unsupported manifest schema version.")
    _require(
        isinstance(manifest.get("manifest_key"), str) and manifest["manifest_key"].strip(),
        "Manifest requires a manifest_key.",
    )
    _require(
        isinstance(manifest.get("candidates"), list) and manifest["candidates"],
        "Manifest requires at least one candidate.",
    )
    return manifest


def _reviewer_by_email(email: str):
    user_model = get_user_model()

    try:
        reviewer = user_model.objects.get(email__iexact=email.strip())
    except user_model.DoesNotExist as exc:
        raise CommandError(f"Reviewer not found: {email}") from exc
    except user_model.MultipleObjectsReturned as exc:
        raise CommandError("Reviewer email is not unique.") from exc

    _require(reviewer.is_active, "Reviewer account is inactive.")
    _require(
        reviewer.is_superuser or reviewer.role in {"reviewer", "admin"},
        "Reviewer must have reviewer or admin access.",
    )
    return reviewer


def _decision_sets(
    block: Any,
    *,
    label: str,
) -> tuple[set[str], set[str]]:
    _require(isinstance(block, dict), f"{label} decisions must be an object.")

    approve_values = block.get("approve")
    reject_values = block.get("reject")

    _require(isinstance(approve_values, list), f"{label}.approve must be a list.")
    _require(isinstance(reject_values, list), f"{label}.reject must be a list.")
    _require(
        all(isinstance(value, str) and value.strip() for value in approve_values + reject_values),
        f"{label} IDs must be non-empty strings.",
    )

    approve = {value.strip() for value in approve_values}
    reject = {value.strip() for value in reject_values}

    _require(
        len(approve) == len(approve_values),
        f"{label}.approve contains duplicate IDs.",
    )
    _require(
        len(reject) == len(reject_values),
        f"{label}.reject contains duplicate IDs.",
    )
    _require(
        approve.isdisjoint(reject),
        f"{label} approve and reject IDs overlap.",
    )
    return approve, reject


def _validate_curation(
    *,
    candidate: SchemeCandidate,
    reviewer: Any,
    row: dict[str, Any],
) -> None:
    for field_name in ("canonical_summary", "official_url"):
        value = row.get(field_name)
        _require(
            isinstance(value, str) and value.strip(),
            f"Candidate {candidate.id} curation requires {field_name}.",
        )

    probe = CandidateCuration(
        candidate=candidate,
        canonical_summary=row["canonical_summary"],
        canonical_objective=row.get("canonical_objective", ""),
        canonical_eligibility_text=row.get("canonical_eligibility_text", ""),
        official_url=row["official_url"],
        application_url=row.get("application_url", ""),
        canonical_support_types=row.get("canonical_support_types"),
        canonical_categories=row.get("canonical_categories"),
        canonical_benefits=row.get("canonical_benefits"),
        canonical_required_documents=row.get("canonical_required_documents"),
        canonical_application_steps=row.get("canonical_application_steps"),
        review_status=CandidateCuration.ReviewStatus.APPROVED,
        reviewed_by=reviewer,
        reviewed_at=timezone.now(),
    )

    try:
        probe.full_clean(
            exclude=["candidate"],
            validate_unique=False,
            validate_constraints=False,
        )
    except ValidationError as exc:
        raise CommandError(f"Candidate {candidate.id} has invalid curation: {exc}") from exc


def _validate_existing_resolution(
    *,
    candidate: SchemeCandidate,
    row: dict[str, Any],
    authority_name: str,
) -> None:
    try:
        resolution = candidate.resolution
    except CandidateResolution.DoesNotExist:
        return

    _require(
        resolution.classification == CandidateResolution.Classification.CANONICAL,
        f"Candidate {candidate.id} already has a conflicting resolution.",
    )
    _require(
        resolution.canonical_title.strip() == row["canonical_title"].strip(),
        f"Candidate {candidate.id} already has a different canonical title.",
    )
    _require(
        resolution.resolved_authority_id is not None,
        f"Candidate {candidate.id} has an incomplete existing resolution.",
    )
    _require(
        normalize_authority_name(resolution.resolved_authority.name)
        == normalize_authority_name(authority_name),
        f"Candidate {candidate.id} already has a different resolved authority.",
    )


def _validate_authority_conflicts(
    *,
    authority: Authority | None,
    row: dict[str, Any],
) -> None:
    if authority is None:
        return

    for field_name in (
        "authority_type",
        "ministry",
        "department",
        "state",
        "official_url",
    ):
        expected = row.get(field_name, "")
        actual = getattr(authority, field_name)

        if expected and actual and expected != actual:
            raise CommandError(
                f"Authority field conflict for {field_name}: "
                f"existing={actual!r}, manifest={expected!r}."
            )


def build_plan(
    *,
    manifest: dict[str, Any],
    reviewer: Any,
) -> PilotPlan:
    authority_row = manifest.get("authority")
    _require(isinstance(authority_row, dict), "Manifest requires an authority object.")

    authority_name = authority_row.get("canonical_name")
    _require(
        isinstance(authority_name, str) and authority_name.strip(),
        "Authority requires canonical_name.",
    )

    authority = find_authority_by_name(authority_name)
    _validate_authority_conflicts(authority=authority, row=authority_row)

    aliases = authority_row.get("aliases", [])
    _require(isinstance(aliases, list), "Authority aliases must be a list.")
    _require(
        all(isinstance(alias, str) and alias.strip() for alias in aliases),
        "Authority aliases must be non-empty strings.",
    )

    source_row = manifest.get("source_document")
    _require(isinstance(source_row, dict), "Manifest requires source_document.")

    expected_hash = source_row.get("content_hash")
    expected_source = source_row.get("source_name")
    expected_extractor = manifest.get("extractor_version")

    _require(
        isinstance(expected_hash, str) and expected_hash.strip(),
        "Source document requires content_hash.",
    )
    _require(
        isinstance(expected_source, str) and expected_source.strip(),
        "Source document requires source_name.",
    )
    _require(
        isinstance(expected_extractor, str) and expected_extractor.strip(),
        "Manifest requires extractor_version.",
    )

    candidate_rows = manifest["candidates"]
    _require(
        all(isinstance(row, dict) for row in candidate_rows),
        "Every candidate row must be an object.",
    )

    candidate_ids = [str(row.get("candidate_id", "")).strip() for row in candidate_rows]
    _require(all(candidate_ids), "Every candidate row requires candidate_id.")
    _require(
        len(candidate_ids) == len(set(candidate_ids)),
        "Manifest contains duplicate candidate IDs.",
    )

    queryset = (
        SchemeCandidate.objects.filter(id__in=candidate_ids)
        .select_related(
            "run__extraction__source_document__source",
            "resolution__resolved_authority",
        )
        .prefetch_related(
            "eligibility_rules",
            "benefit_items",
            "required_document_items",
            "application_steps",
            "evidence",
        )
    )
    by_id = {str(candidate.id): candidate for candidate in queryset}
    missing = sorted(set(candidate_ids) - set(by_id))
    _require(
        not missing,
        "Manifest candidate IDs not found: " + ", ".join(missing),
    )

    seen_child_ids: set[str] = set()
    plans: list[CandidatePlan] = []

    for row in candidate_rows:
        candidate_id = str(row["candidate_id"])
        candidate = by_id[candidate_id]

        _require(
            row.get("classification") == CandidateResolution.Classification.CANONICAL,
            f"Candidate {candidate_id} must use canonical classification.",
        )
        _require(
            isinstance(row.get("expected_title"), str) and candidate.title == row["expected_title"],
            f"Candidate {candidate_id} title does not match the manifest.",
        )
        _require(
            isinstance(row.get("canonical_title"), str) and row["canonical_title"].strip(),
            f"Candidate {candidate_id} requires canonical_title.",
        )
        _require(
            candidate.run.extractor_version == expected_extractor,
            f"Candidate {candidate_id} extractor version does not match.",
        )

        document = candidate.run.extraction.source_document
        _require(
            document.content_hash == expected_hash,
            f"Candidate {candidate_id} source content hash does not match.",
        )
        _require(
            document.source.name == expected_source,
            f"Candidate {candidate_id} source name does not match.",
        )
        _require(
            candidate.evidence.exists(),
            f"Candidate {candidate_id} has no evidence.",
        )
        _require(
            not CandidatePublication.objects.filter(candidate=candidate).exists(),
            f"Candidate {candidate_id} is already published.",
        )
        _require(
            candidate.review_status != SchemeCandidate.ReviewStatus.PUBLISHED,
            f"Candidate {candidate_id} is marked published.",
        )

        _validate_existing_resolution(
            candidate=candidate,
            row=row,
            authority_name=authority_name,
        )

        rule_objects = {str(rule.id): rule for rule in candidate.eligibility_rules.all()}
        approve_rules, reject_rules = _decision_sets(
            row.get("eligibility_rules"),
            label=f"Candidate {candidate_id} eligibility_rules",
        )
        decided_rule_ids = approve_rules | reject_rules

        _require(
            set(rule_objects) == decided_rule_ids,
            f"Candidate {candidate_id} rule decisions must cover every rule exactly once.",
        )

        for object_id in decided_rule_ids:
            _require(
                object_id not in seen_child_ids,
                f"A child object ID appears more than once: {object_id}",
            )
            seen_child_ids.add(object_id)

        structured_row = row.get("structured_reviews")
        _require(
            isinstance(structured_row, dict),
            f"Candidate {candidate_id} requires structured_reviews.",
        )

        structured_items: dict[str, dict[str, Any]] = {}

        for manifest_key, relation_name in STRUCTURED_SPECS.items():
            objects = {str(item.id): item for item in getattr(candidate, relation_name).all()}
            approve, reject = _decision_sets(
                structured_row.get(manifest_key),
                label=f"Candidate {candidate_id} {manifest_key}",
            )
            decided = approve | reject

            _require(
                set(objects) == decided,
                f"Candidate {candidate_id} {manifest_key} decisions "
                "must cover every item exactly once.",
            )

            for object_id in decided:
                _require(
                    object_id not in seen_child_ids,
                    f"A child object ID appears more than once: {object_id}",
                )
                seen_child_ids.add(object_id)

            structured_items[manifest_key] = {
                "objects": objects,
                "approve": approve,
                "reject": reject,
            }

        curation_row = row.get("curation")
        _require(
            isinstance(curation_row, dict),
            f"Candidate {candidate_id} requires curation.",
        )
        _validate_curation(
            candidate=candidate,
            reviewer=reviewer,
            row=curation_row,
        )

        plans.append(
            CandidatePlan(
                manifest_row=row,
                candidate=candidate,
                rules=rule_objects,
                structured_items=structured_items,
            )
        )

    return PilotPlan(
        manifest=manifest,
        reviewer=reviewer,
        authority=authority,
        candidates=plans,
    )


def _authority_for_apply(plan: PilotPlan) -> Authority:
    row = plan.manifest["authority"]
    name = row["canonical_name"].strip()
    authority = find_authority_by_name(name)

    if authority is None:
        authority = Authority.objects.create(
            name=name,
            authority_type=row.get("authority_type", "").strip(),
            ministry=row.get("ministry", "").strip(),
            department=row.get("department", "").strip(),
            state=row.get("state", "").strip(),
            official_url=row.get("official_url", "").strip(),
        )
    else:
        _validate_authority_conflicts(authority=authority, row=row)
        update_fields = []

        for field_name in (
            "authority_type",
            "ministry",
            "department",
            "state",
            "official_url",
        ):
            expected = row.get(field_name, "").strip()
            if expected and not getattr(authority, field_name):
                setattr(authority, field_name, expected)
                update_fields.append(field_name)

        if update_fields:
            update_fields.append("updated_at")
            authority.save(update_fields=update_fields)

    for alias in row.get("aliases", []):
        register_authority_alias(
            authority=authority,
            alias=alias,
            source=plan.manifest["manifest_key"],
            verified=True,
        )

    return authority


def apply_plan(plan: PilotPlan) -> None:
    manifest_key = plan.manifest["manifest_key"]
    schema_version = plan.manifest["schema_version"]

    with transaction.atomic():
        authority = _authority_for_apply(plan)

        for candidate_plan in plan.candidates:
            row = candidate_plan.manifest_row
            candidate = candidate_plan.candidate

            approve_rules, reject_rules = _decision_sets(
                row["eligibility_rules"],
                label=f"Candidate {candidate.id} eligibility_rules",
            )

            for rule_id in sorted(approve_rules):
                review_eligibility_rule(
                    rule=candidate_plan.rules[rule_id],
                    status=EligibilityRuleCandidate.ReviewStatus.APPROVED,
                    reviewer=plan.reviewer,
                    review_notes=f"Approved by pilot manifest {manifest_key}.",
                )

            for rule_id in sorted(reject_rules):
                review_eligibility_rule(
                    rule=candidate_plan.rules[rule_id],
                    status=EligibilityRuleCandidate.ReviewStatus.REJECTED,
                    reviewer=plan.reviewer,
                    review_notes=f"Rejected by pilot manifest {manifest_key}.",
                )

            for manifest_name, item_plan in candidate_plan.structured_items.items():
                for item_id in sorted(item_plan["approve"]):
                    item = item_plan["objects"][item_id]
                    review_structured_item(
                        item=item,
                        status=item.ReviewStatus.APPROVED,
                        reviewer=plan.reviewer,
                        review_notes=(
                            f"Approved by pilot manifest {manifest_key}: {manifest_name}."
                        ),
                    )

                for item_id in sorted(item_plan["reject"]):
                    item = item_plan["objects"][item_id]
                    review_structured_item(
                        item=item,
                        status=item.ReviewStatus.REJECTED,
                        reviewer=plan.reviewer,
                        review_notes=(
                            f"Rejected by pilot manifest {manifest_key}: {manifest_name}."
                        ),
                    )

            metadata = {
                "manifest_key": manifest_key,
                "manifest_schema_version": schema_version,
            }

            resolve_candidate(
                candidate=candidate,
                classification=CandidateResolution.Classification.CANONICAL,
                reviewer=plan.reviewer,
                canonical_title=row["canonical_title"],
                resolved_authority=authority,
                review_notes=f"Resolved by pilot manifest {manifest_key}.",
                metadata=metadata,
            )

            curation = row["curation"]
            curate_candidate(
                candidate=candidate,
                status=CandidateCuration.ReviewStatus.APPROVED,
                reviewer=plan.reviewer,
                canonical_summary=curation["canonical_summary"],
                canonical_objective=curation.get("canonical_objective", ""),
                canonical_eligibility_text=curation.get(
                    "canonical_eligibility_text",
                    "",
                ),
                official_url=curation["official_url"],
                application_url=curation.get("application_url", ""),
                canonical_support_types=curation.get("canonical_support_types"),
                canonical_categories=curation.get("canonical_categories"),
                canonical_benefits=curation.get("canonical_benefits"),
                canonical_required_documents=curation.get("canonical_required_documents"),
                canonical_application_steps=curation.get("canonical_application_steps"),
                review_notes=f"Curated by pilot manifest {manifest_key}.",
                metadata=metadata,
            )


class Command(BaseCommand):
    help = (
        "Validate or apply a reviewed pilot manifest. Dry-run is the default. "
        "This command never publishes schemes."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--manifest",
            default=str(DEFAULT_MANIFEST),
            help="Path to the pilot manifest JSON.",
        )
        parser.add_argument(
            "--reviewer-email",
            required=True,
            help="Reviewer or administrator email used for audit fields.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help=("Apply the validated review operations. Without this flag, no writes occur."),
        )

    def handle(self, *args, **options):
        path = Path(options["manifest"]).expanduser().resolve()
        manifest = _read_manifest(path)
        reviewer = _reviewer_by_email(options["reviewer_email"])
        plan = build_plan(manifest=manifest, reviewer=reviewer)

        mode = "APPLY" if options["apply"] else "DRY RUN"
        self.stdout.write(f"{mode}: {manifest['manifest_key']}")
        self.stdout.write(
            "authority: "
            f"{manifest['authority']['canonical_name']} "
            f"({'reuse' if plan.authority else 'create'})"
        )

        total_rules = 0
        total_items = 0

        for candidate_plan in plan.candidates:
            row = candidate_plan.manifest_row
            approve_rules, reject_rules = _decision_sets(
                row["eligibility_rules"],
                label="eligibility_rules",
            )
            item_count = sum(
                len(value["approve"]) + len(value["reject"])
                for value in candidate_plan.structured_items.values()
            )
            total_rules += len(approve_rules) + len(reject_rules)
            total_items += item_count

            self.stdout.write(
                f"- {row['pilot_key']}: {candidate_plan.candidate.id} "
                f"rules={len(approve_rules)} approve/"
                f"{len(reject_rules)} reject structured={item_count}"
            )

        self.stdout.write(
            f"validated candidates={len(plan.candidates)} "
            f"rules={total_rules} structured_items={total_items}"
        )

        if not options["apply"]:
            self.stdout.write(
                self.style.WARNING(
                    "No database writes performed. Run again with --apply "
                    "to apply the reviewed manifest."
                )
            )
            return

        try:
            apply_plan(plan)
        except ValidationError as exc:
            raise CommandError(f"Manifest apply failed: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS("Pilot review operations applied. No schemes were published.")
        )
