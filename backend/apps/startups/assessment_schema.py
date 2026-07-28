from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

DIRECT_PROFILE_FIELDS = (
    "startup_name",
    "legal_name",
    "description",
    "incorporation_type",
    "incorporation_date",
    "state",
    "district",
    "stage",
    "sectors",
    "technologies",
    "founder_categories",
    "founder_gender",
    "dpiit_recognized",
    "udyam_registered",
    "annual_turnover",
    "revenue_stage",
    "funding_required",
    "funding_purpose",
    "team_size",
)

PROFILE_DATA_FIELDS = (
    "founder_role",
    "founder_experience_years",
    "founder_education",
    "number_of_founders",
    "business_model",
    "customer_status",
    "target_customer",
    "traction_summary",
    "monthly_revenue",
    "funding_stage",
    "capital_raised",
    "runway_months",
    "preferred_funding_type",
    "team_roles",
    "skills_needs",
    "incubator_affiliation",
    "mentor_access",
    "cloud_credits",
    "certification_needs",
    "compliance_support_needs",
    "resource_needs",
    "entity_types",
    "regulatory_registrations",
    "contact_email",
    "website",
)

ASSESSMENT_PROGRESS_FIELDS = (
    "startup_name",
    "legal_name",
    "description",
    "founder_role",
    "founder_categories",
    "incorporation_type",
    "incorporation_date",
    "state",
    "district",
    "stage",
    "sectors",
    "business_model",
    "customer_status",
    "revenue_stage",
    "annual_turnover",
    "team_size",
    "number_of_founders",
    "funding_required",
    "funding_purpose",
    "preferred_funding_type",
    "skills_needs",
    "certification_needs",
    "compliance_support_needs",
)


def json_ready(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [json_ready(item) for item in value]
    return value


def startup_profile_to_assessment_data(startup_profile: Any) -> dict[str, Any]:
    data = {
        field_name: json_ready(getattr(startup_profile, field_name))
        for field_name in DIRECT_PROFILE_FIELDS
    }
    profile_data = startup_profile.profile_data
    if isinstance(profile_data, dict):
        data.update(json_ready(profile_data))
    return data


def value_is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, frozenset, dict)):
        return bool(value)
    return True


def assessment_completion_percent(data: Any) -> int:
    if not isinstance(data, dict):
        return 0
    completed = sum(
        value_is_present(data.get(field_name)) for field_name in ASSESSMENT_PROGRESS_FIELDS
    )
    return round(completed / len(ASSESSMENT_PROGRESS_FIELDS) * 100)
