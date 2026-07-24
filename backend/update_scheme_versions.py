import os
import django
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import transaction
from apps.knowledge.models import ExternalSchemeRecord
from apps.schemes.models import Scheme, SchemeVersion

def update_scheme_versions():
    records = ExternalSchemeRecord.objects.filter(
        review_status=ExternalSchemeRecord.ReviewStatus.VERIFIED,
        matched_scheme__isnull=False
    )
    
    updated_count = 0
    with transaction.atomic():
        for r in records:
            scheme = r.matched_scheme
            # The script created a single SchemeVersion per scheme.
            sv = scheme.current_version
            if not sv:
                # If there's no current_version set, try to get the latest one
                sv = scheme.verified_scheme_versions.order_by("-version_number").first()
            if not sv:
                continue

            # Update eligible stages
            if r.startup_stage and isinstance(r.startup_stage, list):
                sv.eligible_stages = r.startup_stage

            # Update eligible sectors
            if r.industry and isinstance(r.industry, list):
                sv.eligible_sectors = r.industry

            # Update required documents
            if r.documents_required and isinstance(r.documents_required, list):
                sv.required_documents = r.documents_required

            # Construct founder categories
            founder_cats = []
            if str(r.women_eligible).strip().lower() in ["yes", "true", "1", "mandatory"]:
                founder_cats.append("Women Entrepreneurs")
            if str(r.sc_st_eligible).strip().lower() in ["yes", "true", "1", "mandatory"]:
                founder_cats.append("SC/ST Founders")
            if founder_cats:
                sv.founder_categories = founder_cats
            
            # Construct benefits list
            benefits = sv.benefits or []
            if r.funding_amount:
                b_str = f"Funding: {r.funding_amount.strip()}"
                if b_str not in benefits:
                    benefits.append(b_str)
            if r.tax_benefits and r.tax_benefits.strip().lower() != "no direct tax benefit":
                b_str = f"Tax Benefit: {r.tax_benefits.strip()}"
                if b_str not in benefits:
                    benefits.append(b_str)
            sv.benefits = benefits
            
            # Construct restrictions
            restrictions = sv.restrictions or []
            if r.startup_age_limit:
                r_str = f"Age Limit: {r.startup_age_limit.strip()}"
                if r_str not in restrictions:
                    restrictions.append(r_str)
            if r.revenue_criteria:
                r_str = f"Revenue Criteria: {r.revenue_criteria.strip()}"
                if r_str not in restrictions:
                    restrictions.append(r_str)
            if str(r.dpiit_required).strip().lower() in ["yes", "true", "1", "mandatory"]:
                r_str = "DPIIT Recognition Required"
                if r_str not in restrictions:
                    restrictions.append(r_str)
            sv.restrictions = restrictions

            # Application process -> application steps
            if r.application_process:
                # If there's already steps, avoid duplicates
                existing_instructions = [step.get("instruction") for step in sv.application_steps]
                if r.application_process.strip() not in existing_instructions:
                    sv.application_steps.append({
                        "step_number": len(sv.application_steps) + 1,
                        "instruction": r.application_process.strip(),
                        "url": r.official_application_url or ""
                    })

            sv.save()
            updated_count += 1
            
    print(f"Updated {updated_count} SchemeVersions with detailed fields.")

if __name__ == "__main__":
    update_scheme_versions()
