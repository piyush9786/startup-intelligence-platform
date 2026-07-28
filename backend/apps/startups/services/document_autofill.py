from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from apps.documents.services.extractors import (
    ExtractedSection,
    ExtractionError,
    ExtractionPayload,
    extract_document,
)

AUTOFILL_PARSER_VERSION = "startup-document-autofill-v1"
MAX_AUTOFILL_DOCUMENT_BYTES = 10 * 1024 * 1024
SUPPORTED_AUTOFILL_MIME_TYPES = {"application/pdf", "text/plain"}
DOCUMENT_TYPE_CHOICES = (
    ("auto", "Auto-detect"),
    ("incorporation_certificate", "Incorporation certificate"),
    ("udyam_registration", "Udyam registration"),
    ("pitch_deck", "Pitch deck / Executive summary"),
)

PITCH_DECK_SIGNALS = (
    re.compile(r"(?i)\bpitch deck\b"),
    re.compile(r"(?i)\bexecutive summary\b"),
    re.compile(r"(?i)\bbusiness model\b"),
    re.compile(r"(?i)\bproblem statement\b"),
    re.compile(r"(?i)\bmarket opportunity\b"),
)

FUNDING_REQ_PATTERN = re.compile(
    r"(?im)^\s*(?:funding (?:required|ask)|capital (?:required|needed)|seeking)"
    r"\s*[:\-]?\s*(?:INR|Rs\.?|\$)?\s*(?P<value>\d+[\d,.]*(?:\s*(?:Lakh|Crore|k|M|Mn|Million|Cr))?)",
)

TEAM_SIZE_PATTERN = re.compile(
    r"(?im)^\s*(?:team size|headcount|employees|full[\s-]time team)"
    r"\s*[:\-]\s*(?P<value>\d{1,4})",
)

SECTOR_PATTERN = re.compile(
    r"(?im)^\s*(?:sector|industry|domain)"
    r"\s*[:\-]\s*(?P<value>[^\n]{2,100})",
)

TECH_PATTERN = re.compile(
    r"(?im)^\s*(?:technologies|tech stack|key tech)"
    r"\s*[:\-]\s*(?P<value>[^\n]{2,120})",
)

MIME_BY_SUFFIX = {".pdf": "application/pdf", ".txt": "text/plain"}
CIN_PATTERN = re.compile(
    r"\b[LU]\d{5}[A-Z]{2}\d{4}(?:PLC|PTC|OPC|NPL|FTC)\d{6}\b",
    flags=re.IGNORECASE,
)
LLPIN_PATTERN = re.compile(r"\b[A-Z]{3}-\d{4}\b", flags=re.IGNORECASE)
UDYAM_PATTERN = re.compile(
    r"\bUDYAM-[A-Z]{2}-\d{2}-\d{7}\b",
    flags=re.IGNORECASE,
)

LEGAL_NAME_PATTERNS = (
    re.compile(
        r"(?im)^\s*(?:name of (?:the )?(?:company|enterprise)|enterprise name)"
        r"\s*[:\-]\s*(?P<value>[^\n]{2,180})"
    ),
    re.compile(
        r"(?is)\b(?:certify that|company named)\s+"
        r"(?P<value>[A-Z0-9][A-Z0-9&.,'()\- ]{2,180}?)"
        r"\s+(?:is|was)\s+incorporated\b"
    ),
)
DATE_PATTERNS = (
    re.compile(
        r"(?im)^\s*(?:date of incorporation|incorporation date|registered on)"
        r"\s*[:\-]\s*(?P<value>[^\n]{4,40})"
    ),
    re.compile(
        r"(?i)\bincorporated on\s+(?P<value>"
        r"\d{1,2}[/-]\d{1,2}[/-]\d{4}|"
        r"\d{4}-\d{1,2}-\d{1,2}|"
        r"\d{1,2}\s+[A-Za-z]+\s+\d{4})"
    ),
)
STATE_PATTERN = re.compile(
    r"(?im)^\s*state\s*[:\-]\s*(?P<value>[^\n|]{2,80})"
)
DISTRICT_PATTERN = re.compile(
    r"(?im)^\s*district\s*[:\-]\s*(?P<value>[^\n|]{2,80})"
)


class StartupDocumentAutofillError(ValueError):
    """Raised when an uploaded founder document cannot be parsed safely."""


def normalize_autofill_mime_type(filename: str, content_type: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix in MIME_BY_SUFFIX:
        return MIME_BY_SUFFIX[suffix]

    normalized = (content_type or "").split(";", 1)[0].strip().lower()
    if normalized in SUPPORTED_AUTOFILL_MIME_TYPES:
        return normalized
    return ""


def _find_match(
    sections: list[ExtractedSection],
    patterns: tuple[re.Pattern[str], ...],
):
    for section in sections:
        for pattern in patterns:
            match = pattern.search(section.text)
            if match:
                return section, match
    return None


def _find_identifier(
    sections: list[ExtractedSection],
    pattern: re.Pattern[str],
):
    for section in sections:
        match = pattern.search(section.text)
        if match:
            return section, match
    return None


def _evidence(located, radius: int = 110) -> dict[str, Any]:
    section, match = located
    start = max(0, match.start() - radius)
    end = min(len(section.text), match.end() + radius)
    excerpt = re.sub(r"\s+", " ", section.text[start:end]).strip()
    return {
        "text": excerpt[:320],
        "page_number": section.page_number,
        "heading": section.heading,
    }


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip(" \t\r\n:;,.|-")[:255]


def _parse_date(value: str) -> str | None:
    cleaned = _clean(value)
    cleaned = re.split(
        r"\s{2,}|\b(?:cin|udyam|state|district|address)\b\s*[:\-]",
        cleaned,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip()
    for date_format in (
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d %B %Y",
        "%d %b %Y",
    ):
        try:
            return datetime.strptime(cleaned, date_format).date().isoformat()
        except ValueError:
            continue
    return None


def _startup_name(legal_name: str) -> str:
    suffix = re.compile(
        r"\s+(?:PRIVATE LIMITED|PVT\.?\s+LTD\.?|LIMITED|LTD\.?|"
        r"LIMITED LIABILITY PARTNERSHIP|LLP|OPC PRIVATE LIMITED)$",
        flags=re.IGNORECASE,
    )
    return suffix.sub("", legal_name).strip(" ,.-") or legal_name


def _incorporation_type(text: str, legal_name: str) -> str | None:
    combined = f"{legal_name}\n{text}".upper()
    if "SECTION 8" in combined:
        return "section_8"
    if "LIMITED LIABILITY PARTNERSHIP" in combined or re.search(
        r"\bLLP\b",
        combined,
    ):
        return "llp"
    if (
        "PRIVATE LIMITED" in combined
        or "PVT LTD" in combined
        or "ONE PERSON COMPANY" in combined
    ):
        return "private_limited"
    return None


def _detect_type(payload: ExtractionPayload):
    udyam = _find_identifier(payload.sections, UDYAM_PATTERN)
    if udyam:
        return "udyam_registration", 99, _evidence(udyam)

    udyam_heading = _find_match(
        payload.sections,
        (
            re.compile(r"(?i)\budyam registration certificate\b"),
            re.compile(r"(?i)\budyam registration number\b"),
        ),
    )
    if udyam_heading:
        return "udyam_registration", 96, _evidence(udyam_heading)

    incorporation = _find_match(
        payload.sections,
        (
            re.compile(r"(?i)\bcertificate of incorporation\b"),
            re.compile(r"(?i)\bcorporate identity number\b"),
            re.compile(r"(?i)\bcompanies act\b"),
        ),
    )
    cin = _find_identifier(payload.sections, CIN_PATTERN)
    if incorporation or cin:
        located = incorporation or cin
        return "incorporation_certificate", 95, _evidence(located)

    pitch_match = _find_match(payload.sections, PITCH_DECK_SIGNALS)
    if pitch_match:
        return "pitch_deck", 90, _evidence(pitch_match)

    return "unknown", 0, None


def _add(
    suggestions: list[dict[str, Any]],
    *,
    field: str,
    value: Any,
    confidence: int,
    reason: str,
    evidence: dict[str, Any],
) -> None:
    if value in (None, "", []):
        return
    if any(item["field"] == field for item in suggestions):
        return
    suggestions.append(
        {
            "field": field,
            "value": value,
            "confidence": max(0, min(100, confidence)),
            "reason": reason,
            "evidence": evidence,
        }
    )


def _extract_suggestions(
    payload: ExtractionPayload,
    document_type: str,
) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    legal_match = _find_match(payload.sections, LEGAL_NAME_PATTERNS)
    legal_name = ""

    if legal_match:
        legal_name = _clean(legal_match[1].group("value"))
        evidence = _evidence(legal_match)
        _add(
            suggestions,
            field="legal_name",
            value=legal_name,
            confidence=96,
            reason="The document explicitly labels the registered enterprise name.",
            evidence=evidence,
        )
        _add(
            suggestions,
            field="startup_name",
            value=_startup_name(legal_name),
            confidence=86,
            reason="This name is derived from the registered legal name.",
            evidence=evidence,
        )

    date_match = _find_match(payload.sections, DATE_PATTERNS)
    if date_match:
        parsed = _parse_date(date_match[1].group("value"))
        if parsed:
            _add(
                suggestions,
                field="incorporation_date",
                value=parsed,
                confidence=94,
                reason="The document explicitly states the incorporation date.",
                evidence=_evidence(date_match),
            )

    registrations: list[str] = []
    registration_evidence = None
    for pattern in (CIN_PATTERN, LLPIN_PATTERN, UDYAM_PATTERN):
        located = _find_identifier(payload.sections, pattern)
        if located:
            registrations.append(located[1].group(0).upper())
            registration_evidence = registration_evidence or _evidence(located)

    udyam = _find_identifier(payload.sections, UDYAM_PATTERN)
    if udyam:
        _add(
            suggestions,
            field="udyam_registered",
            value=True,
            confidence=99,
            reason="A valid-format Udyam registration number appears in the document.",
            evidence=_evidence(udyam),
        )

    if registrations and registration_evidence:
        _add(
            suggestions,
            field="regulatory_registrations",
            value=registrations,
            confidence=98,
            reason="These registration identifiers are printed in the document.",
            evidence=registration_evidence,
        )

    if document_type == "incorporation_certificate":
        value = _incorporation_type(payload.combined_text, legal_name)
        located = legal_match or _find_match(
            payload.sections,
            (
                re.compile(r"(?i)\bprivate limited\b"),
                re.compile(r"(?i)\blimited liability partnership\b"),
                re.compile(r"(?i)\bsection 8\b"),
            ),
        )
        if value and located:
            _add(
                suggestions,
                field="incorporation_type",
                value=value,
                confidence=91,
                reason="The legal form appears in the enterprise name or certificate.",
                evidence=_evidence(located),
            )

    if document_type == "udyam_registration":
        state_match = _find_match(payload.sections, (STATE_PATTERN,))
        if state_match:
            _add(
                suggestions,
                field="state",
                value=_clean(state_match[1].group("value")),
                confidence=88,
                reason="The registered address identifies the state.",
                evidence=_evidence(state_match),
            )

        district_match = _find_match(payload.sections, (DISTRICT_PATTERN,))
        if district_match:
            _add(
                suggestions,
                field="district",
                value=_clean(district_match[1].group("value")),
                confidence=88,
                reason="The registered address identifies the district.",
                evidence=_evidence(district_match),
            )

    sector_match = _find_match(payload.sections, (SECTOR_PATTERN,))
    if sector_match:
        sectors_raw = _clean(sector_match[1].group("value"))
        sectors_list = [s.strip() for s in sectors_raw.split(",") if s.strip()]
        _add(
            suggestions,
            field="sectors",
            value=sectors_list,
            confidence=85,
            reason="Industry sector explicitly labeled in document.",
            evidence=_evidence(sector_match),
        )

    tech_match = _find_match(payload.sections, (TECH_PATTERN,))
    if tech_match:
        tech_raw = _clean(tech_match[1].group("value"))
        tech_list = [t.strip() for t in tech_raw.split(",") if t.strip()]
        _add(
            suggestions,
            field="technologies",
            value=tech_list,
            confidence=85,
            reason="Technologies labeled in document text.",
            evidence=_evidence(tech_match),
        )

    funding_match = _find_match(payload.sections, (FUNDING_REQ_PATTERN,))
    if funding_match:
        _add(
            suggestions,
            field="funding_required",
            value=_clean(funding_match[1].group("value")),
            confidence=82,
            reason="Funding requirement ask identified in document.",
            evidence=_evidence(funding_match),
        )

    team_match = _find_match(payload.sections, (TEAM_SIZE_PATTERN,))
    if team_match:
        try:
            team_val = int(_clean(team_match[1].group("value")))
            _add(
                suggestions,
                field="team_size",
                value=team_val,
                confidence=88,
                reason="Team headcount identified in document.",
                evidence=_evidence(team_match),
            )
        except ValueError:
            pass

    order = {
        "startup_name": 0,
        "legal_name": 1,
        "incorporation_type": 2,
        "incorporation_date": 3,
        "udyam_registered": 4,
        "state": 5,
        "district": 6,
        "regulatory_registrations": 7,
    }
    return sorted(suggestions, key=lambda item: order.get(item["field"], 100))


def build_startup_profile_autofill(
    *,
    content: bytes,
    filename: str,
    mime_type: str,
    document_type_hint: str = "auto",
) -> dict[str, Any]:
    if not content:
        raise StartupDocumentAutofillError("The uploaded document is empty.")
    if mime_type not in SUPPORTED_AUTOFILL_MIME_TYPES:
        raise StartupDocumentAutofillError(
            "Only text-based PDF and plain-text documents are supported."
        )

    try:
        payload = extract_document(content, mime_type)
    except ExtractionError as exc:
        raise StartupDocumentAutofillError(
            "The document text could not be extracted. "
            "Scanned PDFs may require OCR before upload."
        ) from exc

    detected, confidence, evidence = _detect_type(payload)
    warnings: list[str] = []
    document_type = detected
    source = "detected"

    if document_type_hint != "auto":
        if detected == "unknown":
            document_type = document_type_hint
            confidence = 55
            source = "founder_hint"
        elif detected != document_type_hint:
            warnings.append(
                "The selected document type does not match the detected text."
            )

    if document_type == "unknown":
        warnings.append(
            "The document type could not be confirmed. Review every suggestion."
        )

    empty_pages = payload.metadata.get("empty_pages") or []
    if empty_pages:
        warnings.append(
            "Some PDF pages contained no extractable text: "
            + ", ".join(str(page) for page in empty_pages[:10])
            + "."
        )

    suggestions = _extract_suggestions(payload, document_type)
    if not suggestions:
        warnings.append(
            "No supported startup-profile fields were found in the document."
        )

    return {
        "parser_version": AUTOFILL_PARSER_VERSION,
        "requires_confirmation": True,
        "document": {
            "filename": filename,
            "mime_type": mime_type,
            "sha256": hashlib.sha256(content).hexdigest(),
            "detected_title": payload.title,
            "page_count": payload.page_count,
        },
        "document_type": {
            "value": document_type,
            "confidence": confidence,
            "source": source,
            "evidence": evidence,
        },
        "suggestions": suggestions,
        "warnings": warnings,
    }
