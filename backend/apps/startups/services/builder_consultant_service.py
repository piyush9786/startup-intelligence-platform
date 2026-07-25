"""
AI Startup Consultant Master Strategy & Reasoning Engine.
Provides dynamic, reasoning-based AI plan generation using LLM providers
with intelligent sector-aware reasoning fallback.
"""

from __future__ import annotations

import logging
from typing import Any

from apps.startups.models import StartupProfile
from apps.startups.services.llm_provider import (
    LLMProviderError,
    get_startup_advisor_llm_provider,
)

logger = logging.getLogger(__name__)


def _generate_startup_title(idea: str, sector: str) -> str:
    """Generates an intuitive AI brand title for the startup idea."""
    idea_lower = idea.lower()
    sector_lower = sector.lower()

    if any(
        k in sector_lower or k in idea_lower
        for k in ["drone", "vaccine", "health", "med", "doctor"]
    ):
        return "AeroMed Express AI"
    elif any(
        k in sector_lower or k in idea_lower for k in ["agri", "cold", "farm", "crop", "mandi"]
    ):
        return "AgriVault Logistics"
    elif any(k in sector_lower or k in idea_lower for k in ["ev", "battery", "swap", "clean"]):
        return "SwapVolt Mobility"
    elif any(k in sector_lower or k in idea_lower for k in ["d2c", "snack", "organic", "food"]):
        return "Naturals D2C Organics"
    elif any(
        k in sector_lower or k in idea_lower for k in ["invoice", "gst", "saas", "fintech", "tax"]
    ):
        return "FinRec AI Automation"
    else:
        words = [w.capitalize() for w in idea.split()[:2] if len(w) > 2]
        prefix = "".join(words) if words else "Venture"
        return f"{prefix} Tech"


def _sanitize_scheme_suggestions(
    raw_schemes: Any,
) -> list[dict[str, Any]]:
    """
    Convert model or fallback scheme output into explicitly unverified ideas.

    Benefit amounts, match percentages and eligibility conclusions are removed
    until the suggestion is connected to a verified SchemeVersion and a
    deterministic eligibility assessment.
    """
    if not isinstance(raw_schemes, list):
        return []

    suggestions: list[dict[str, Any]] = []

    for item in raw_schemes:
        if not isinstance(item, dict):
            continue

        name = str(item.get("name") or item.get("scheme_name") or "").strip()

        if not name:
            continue

        suggestions.append(
            {
                "name": name,
                "support": ("Current support terms must be verified on the official scheme page."),
                "reason": (
                    "Potential scheme to investigate based on the startup "
                    "sector. Eligibility, availability and benefit amounts "
                    "were not assessed."
                ),
                "is_verified": False,
                "source_url": None,
            }
        )

    return suggestions


def _generate_sector_context_intelligence(
    idea: str, sector: str, stage: str, funding: str
) -> dict[str, Any]:
    """
    Synthesizes rich, reasoning-backed startup analysis, AI title, business plan modules,
    scheme matches, and roadmaps tailored to the founder's specific idea concept.
    """
    idea_lower = idea.lower()
    sector_lower = sector.lower()
    startup_title = _generate_startup_title(idea, sector)

    # Sector-Specific Reasoning & Scheme Mapping
    if any(
        k in sector_lower or k in idea_lower for k in ["health", "bio", "med", "clinic", "drone"]
    ):
        sector_category = "HealthTech & BioTech"
        schemes = [
            {
                "name": "BIRAC Biotechnology Ignition Grant (BIG)",
                "support": "Up to ₹50 Lakhs Non-Dilutive Grant",
                "reason": (
                    f"Perfect fit for {sector_category} ventures developing "
                    f"proof-of-concept for '{idea}'."
                ),
            },
            {
                "name": "Startup India Seed Fund Scheme (SISFS)",
                "support": "Up to ₹20 Lakhs Grant + ₹50 Lakhs Debt",
                "reason": "Covers clinical trials, prototype development, and pilot testing.",
            },
            {
                "name": "DPIIT 80-IAC 3-Year Income Tax Exemption",
                "support": "100% Tax Exemption for 3 Years",
                "reason": "Exempts corporate profits from tax during commercial rollout.",
            },
        ]
        interview_persona = "Hospital Directors, Senior Clinicians, and Rural Health Officers"
        experiment_pilot = (
            "Run 10-patient clinical pilot with partner teleclinic or district hospital."
        )
        monetization = "Per-delivery/consultation fee + annual health system SaaS license."
    elif any(
        k in sector_lower or k in idea_lower for k in ["agri", "farm", "crop", "mandi", "food"]
    ):
        sector_category = "AgriTech & Supply Chain"
        schemes = [
            {
                "name": "RKVY-RAFTAAR Agri-Entrepreneurship Grant",
                "support": "Up to ₹25 Lakhs Seed Grant",
                "reason": f"Dedicated Ministry of Agriculture grant for '{idea}'.",
            },
            {
                "name": "Startup India Seed Fund Scheme (SISFS)",
                "support": "Up to ₹20 Lakhs Prototype Grant",
                "reason": "Provides early capital for farm-level pilot testing.",
            },
            {
                "name": "Credit Guarantee Scheme for Startups (CGSS)",
                "support": "Up to ₹10 Crore Collateral-Free Loans",
                "reason": ("Secures bank credit for cold storage or supply chain equipment."),
            },
        ]
        interview_persona = "Farmer Producer Organizations (FPOs), mandi traders, and agronomists"
        experiment_pilot = "Deploy 2 micro-cold-storage units with 5 local FPOs for 30 days."
        monetization = "5% supply-chain transaction margin + monthly equipment lease fee."
    elif any(k in sector_lower or k in idea_lower for k in ["ev", "battery", "clean", "energy"]):
        sector_category = "CleanTech & EV Mobility"
        schemes = [
            {
                "name": "FAME-II & PLI Auto Innovation Scheme",
                "support": "Capital Subsidy & Battery Incentive",
                "reason": (f"Incentive support for clean mobility platforms targeting '{idea}'."),
            },
            {
                "name": "Startup India Seed Fund Scheme (SISFS)",
                "support": "Up to ₹20 Lakhs Grant + ₹50 Lakhs Debt",
                "reason": "Funds battery swapping station fabrication and safety testing.",
            },
            {
                "name": "CGSS Collateral-Free Bank Guarantee",
                "support": "Up to ₹10 Crore Credit Guarantee",
                "reason": "Backs debt financing for battery fleet procurement.",
            },
        ]
        interview_persona = "Delivery fleet managers (Zomato/Swiggy) and 3W auto drivers"
        experiment_pilot = "Set up 1 trial battery swap kiosk serving 15 delivery drivers."
        monetization = "Pay-per-swap fee + monthly battery subscription plan."
    elif any(k in sector_lower or k in idea_lower for k in ["d2c", "consumer", "snack", "brand"]):
        sector_category = "D2C & Consumer Goods"
        schemes = [
            {
                "name": "Startup India Seed Fund Scheme (SISFS)",
                "support": "Up to ₹20 Lakhs Grant",
                "reason": f"Supports initial product batch manufacturing for '{idea}'.",
            },
            {
                "name": "MSME Innovative Scheme (Incubation)",
                "support": "Up to ₹15 Lakhs Grant",
                "reason": "Funds product design, testing, and brand incubation.",
            },
            {
                "name": "DPIIT Recognition & Tax Exemption",
                "support": "Fast-Track IPR & 80-IAC Tax Exemption",
                "reason": "Provides 80% rebate on trademark/patent filing fees.",
            },
        ]
        interview_persona = "Health-conscious urban consumers and specialty grocery buyers"
        experiment_pilot = "Produce 200 sample snack boxes and run Instagram D2C campaign."
        monetization = "Direct e-commerce sales (65% gross margin) + monthly subscription."
    else:
        sector_category = "B2B AI & DeepTech SaaS"
        schemes = [
            {
                "name": "SAMRIDH MeitY Accelerator Scheme",
                "support": "Up to ₹40 Lakhs Matching Grant",
                "reason": f"MeitY scheme for scaling B2B software & AI platforms like '{idea}'.",
            },
            {
                "name": "Startup India Seed Fund Scheme (SISFS)",
                "support": "Up to ₹20 Lakhs Grant",
                "reason": (
                    "Funds cloud infrastructure, AI model training, and pilot integrations."
                ),
            },
            {
                "name": "DPIIT 80-IAC 3-Year Income Tax Holiday",
                "support": "100% Tax Exemption for 3 Consecutive Years",
                "reason": "Eliminates tax burden on recurring software profit margins.",
            },
        ]
        interview_persona = "CTOs, Finance Directors, and SMB Business Owners"
        experiment_pilot = "Launch interactive prototype & secure 3 paid design partner pilots."
        monetization = "Tiered SaaS monthly subscription (Starter ₹4,999/mo, Pro ₹19,999/mo)."

    # 1. AI Reasoning & General Idea Understanding
    idea_understanding = {
        "generated_title": startup_title,
        "core_concept": (
            f"{startup_title} is an innovative {sector_category} startup built to address '{idea}'."
        ),
        "market_opportunity": (
            f"India is experiencing rapid digital infrastructure growth in {sector_category}. "
            f"Solving '{idea}' addresses an urgent market gap with strong scalability potential."
        ),
        "value_proposition": (
            f"A hypothesis that a focused digital workflow could reduce friction "
            f"for customers dealing with '{idea}'."
        ),
        "target_audience": interview_persona,
        "competitive_edge": (
            f"First-mover technology advantage and deep compliance alignment for '{idea}'."
        ),
    }

    # 2. Complete Executive Plan
    business_plan = {
        "problem": {
            "problem_statement": (
                f"Target customers face severe manual complexity and cost delays "
                f"when dealing with '{idea}'."
            ),
            "who_has_this_problem": f"{interview_persona} operating in {sector}.",
            "current_alternatives": (
                "Fragmented spreadsheets and expensive legacy paper processes."
            ),
            "why_now": (
                f"Rapid adoption of digital infrastructure and demand for automated "
                f"{sector_category} solutions in India."
            ),
            "evidence_of_problem": (
                f"Treat the severity and frequency of the problem around "
                f"'{idea}' as an unvalidated hypothesis requiring customer evidence."
            ),
        },
        "customer": {
            "primary_customer_segment": f"{interview_persona} seeking solutions for '{idea}'.",
            "customer_profile": (
                f"Tech-forward decision-makers with dedicated budgets in {sector}."
            ),
            "customer_pain_intensity": (
                "Unvalidated hypothesis. Measure frequency, urgency and existing "
                "spend during customer interviews."
            ),
            "customer_willingness_to_pay": (
                f"Willingness to pay must be tested before treating the "
                f"{funding} target as commercially supported."
            ),
            "reach_channels": "Direct B2B LinkedIn outreach, industry groups, and targeted SEO.",
        },
        "interviews": {
            "interview_goal": f"Validate willingness-to-pay and feature priorities for '{idea}'.",
            "target_interviewees": f"15 decision-makers matching {interview_persona}.",
            "key_questions": (
                "1) How do you solve this today? 2) Cost of manual errors? "
                "3) What outcome would justify paying for a new solution?"
            ),
            "success_criteria": "At least 10 of 15 interviewees request a pilot demo.",
            "recruitment_approach": "Warm network introductions and direct founder outreach.",
        },
        "validation": {
            "core_hypothesis": (
                f"Customers may adopt a solution for '{idea}' when measured "
                "outcomes are materially better than their current alternative."
            ),
            "experiment_1": "1-Page Landing Page: Target 100 waitlist signups in 14 days.",
            "experiment_2": experiment_pilot,
            "minimum_evidence": "3 signed pilot letters of intent (LOIs) or paid deposits.",
        },
        "business_model": {
            "revenue_model": monetization,
            "value_proposition": (
                f"Reducing measurable workflow friction for customers dealing "
                f"with '{idea}', subject to pilot validation."
            ),
            "key_activities": "Product development, pilot onboarding, and grant compliance.",
            "key_resources": "Proprietary software IP, domain expertise, and seed capital.",
            "cost_structure": "Engineering salaries, cloud infrastructure, and legal compliance.",
            "unit_economics": (
                "Model gross margin, acquisition cost and customer lifetime value "
                "after collecting real pilot and sales data."
            ),
        },
        "pricing": {
            "pricing_model": "Tiered recurring pricing model tailored to usage volume.",
            "price_point": "Starter: ₹4,999/month | Pro: ₹19,999/month | Enterprise: Custom.",
            "pricing_basis": "Based on processed volume, active seats, or transaction milestones.",
            "competitive_positioning": (
                "Benchmark pricing and switching costs against verified alternatives "
                "before selecting a final position."
            ),
            "early_customer_offer": "50% lifetime discount for first 10 founding partners.",
        },
    }

    execution_roadmap = [
        {
            "phase": "Month 1-3",
            "milestone": f"Customer Validation & 15 Interviews for '{idea}'",
            "status": "In Progress",
        },
        {
            "phase": "Month 4-6",
            "milestone": f"MVP Prototype Launch & {experiment_pilot}",
            "status": "Upcoming",
        },
        {
            "phase": "Month 7-9",
            "milestone": f"DPIIT Recognition & {schemes[0]['name']} Application",
            "status": "Upcoming",
        },
        {
            "phase": "Month 10-12",
            "milestone": "Commercial Scale & ₹10L Monthly Recurring Revenue",
            "status": "Upcoming",
        },
    ]

    consultant_recommendations = {
        "executive_advice": (
            f"Your venture '{startup_title}' has strong market potential in {sector_category}. "
            f"Focus initially on securing 3 pilot commitments from {interview_persona} "
            "before building complex custom code."
        ),
        "risks_to_watch": [
            "Customer inertia preferring comfortable manual workarounds.",
            "Premature scaling before confirming product-market fit.",
            "Delayed GSTIN or DPIIT registration blocking seed grant disbursements.",
        ],
        "next_best_action": (
            "Review the official eligibility rules and current application "
            f"status for {schemes[0]['name']} before taking any application action."
        ),
    }

    return {
        "generated_title": startup_title,
        "concept": idea,
        "sector": sector,
        "stage": stage,
        "funding_required": funding,
        "idea_understanding": idea_understanding,
        "business_plan": business_plan,
        "recommended_schemes": _sanitize_scheme_suggestions(schemes),
        "execution_roadmap": execution_roadmap,
        "consultant_recommendations": consultant_recommendations,
        "is_suggestion": True,
        "trust_level": "suggested_hypothesis",
        "trust_notice": (
            "AI-Drafted Proposal. Verify all market statistics, grant "
            "matches, and regulatory claims with authoritative records "
            "before submitting."
        ),
        "generated_by": "ai-startup-consultant-reasoning-v3",
    }


def _normalize_llm_payload(
    payload: dict[str, Any], idea: str, sector: str, stage: str, funding: str
) -> dict[str, Any]:
    """Ensures LLM output conforms to the standard API contract."""
    fallback = _generate_sector_context_intelligence(idea, sector, stage, funding)

    startup_title = payload.get("generated_title") or _generate_startup_title(idea, sector)

    idea_understanding = payload.get("idea_understanding") or {
        "generated_title": startup_title,
        "core_concept": str(payload.get("context") or idea),
        "market_opportunity": str(
            payload.get("market_potential") or fallback["idea_understanding"]["market_opportunity"]
        ),
        "value_proposition": str(
            payload.get("value_proposition") or fallback["idea_understanding"]["value_proposition"]
        ),
        "target_audience": str(
            payload.get("target_audience") or fallback["idea_understanding"]["target_audience"]
        ),
        "competitive_edge": "AI-driven first mover advantage.",
    }

    business_plan = payload.get("business_plan") or fallback["business_plan"]
    recommended_schemes = _sanitize_scheme_suggestions(
        payload.get("recommended_schemes") or fallback["recommended_schemes"]
    )
    raw_roadmap = payload.get("execution_roadmap") or payload.get("roadmap") or []

    execution_roadmap = []
    if isinstance(raw_roadmap, list):
        for item in raw_roadmap:
            if isinstance(item, dict):
                execution_roadmap.append(
                    {
                        "phase": item.get("phase") or item.get("quarter") or "Phase",
                        "milestone": item.get("milestone") or str(item.get("activities", "")),
                        "status": "Upcoming",
                    }
                )

    if not execution_roadmap:
        execution_roadmap = fallback["execution_roadmap"]

    consultant_recommendations = (
        payload.get("consultant_recommendations") or fallback["consultant_recommendations"]
    )

    return {
        "generated_title": startup_title,
        "concept": idea,
        "sector": sector,
        "stage": stage,
        "funding_required": funding,
        "idea_understanding": idea_understanding,
        "business_plan": business_plan,
        "recommended_schemes": recommended_schemes,
        "execution_roadmap": execution_roadmap,
        "consultant_recommendations": consultant_recommendations,
        "is_suggestion": True,
        "trust_level": "suggested_hypothesis",
        "trust_notice": (
            "AI-Drafted Proposal. Verify all market statistics, grant "
            "matches, and regulatory claims with authoritative records "
            "before submitting."
        ),
        "generated_by": "ai-startup-consultant-llm-v3",
    }


def generate_master_startup_consultant_package(
    *,
    idea_description: str,
    sector: str = "Technology / General",
    stage: str = "Idea / Prototype",
    funding_required: str = "₹25 Lakhs",
    profile: StartupProfile | None = None,
) -> dict[str, Any]:
    """
    Generates a full Reasoning AI Consultant Master Package tailored to the founder's idea.
    Attempts LLM provider generation if available, with intelligent reasoning fallback.
    """
    idea = idea_description.strip()

    # Try LLM provider if configured
    try:
        provider = get_startup_advisor_llm_provider()
        prompt_messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert Indian Startup Consultant AI reasoning model. "
                    "Analyze the founder's concept and generate a startup title, "
                    "general understanding & market opportunity analysis, executive plan, "
                    "potential Indian government schemes, a 12-month execution roadmap, "
                    "and advice. Treat all market, financial and scheme statements as "
                    "unverified hypotheses. Do not claim eligibility, match percentages, "
                    "benefit amounts or regulatory approval."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Concept: {idea}\nSector: {sector}\nStage: {stage}\n"
                    f"Funding Target: {funding_required}"
                ),
            },
        ]
        res = provider.generate(messages=prompt_messages, response_schema={})
        if res and res.payload:
            return _normalize_llm_payload(res.payload, idea, sector, stage, funding_required)
    except (LLMProviderError, Exception) as err:
        logger.info(
            "LLM Provider unavailable for consultant package, using reasoning engine: %s", err
        )

    return _generate_sector_context_intelligence(idea, sector, stage, funding_required)
