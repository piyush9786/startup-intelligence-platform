from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol


class ChunkLike(Protocol):
    id: Any
    chunk_index: int
    heading: str
    page_number: int | None
    text: str


TITLE_SIGNALS = (
    "scheme",
    "fund",
    "grant",
    "loan",
    "credit guarantee",
    "guarantee scheme",
    "programme",
    "program",
    "mission",
    "initiative",
    "benefit",
    "recognition",
    "registration",
    "certificate",
    "tax exemption",
    "subsidy",
    "challenge",
    "award",
    "incubator",
    "accelerator",
    "support",
    "assistance",
)
GENERIC_HEADINGS = {
    "about",
    "application",
    "application process",
    "benefit",
    "benefits",
    "contact",
    "documents",
    "documents required",
    "eligibility",
    "eligibility criteria",
    "features",
    "financial support",
    "how to apply",
    "introduction",
    "objective",
    "objectives",
    "overview",
    "process",
    "required documents",
    "scope",
}
SECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "eligibility",
        re.compile(
            r"\b(?:eligib|who can apply|applicant criteria|qualif)",
            re.IGNORECASE,
        ),
    ),
    (
        "benefit",
        re.compile(
            r"\b(?:benefit|financial support|funding support|"
            r"assistance|grant amount|loan amount|incentive)",
            re.IGNORECASE,
        ),
    ),
    (
        "application",
        re.compile(
            r"\b(?:how to apply|application process|procedure|apply online)",
            re.IGNORECASE,
        ),
    ),
    (
        "document",
        re.compile(
            r"\b(?:documents? required|required documents?|documentation|"
            r"enclosures?)",
            re.IGNORECASE,
        ),
    ),
    (
        "objective",
        re.compile(r"\b(?:objective|purpose|aims?|overview)", re.IGNORECASE),
    ),
    (
        "authority",
        re.compile(
            r"\b(?:implementing agency|nodal agency|ministry|department|authority)",
            re.IGNORECASE,
        ),
    ),
)
URL_PATTERN = re.compile(r"https?://[^\s<>\]\[)('\\\"]+", re.IGNORECASE)
AMOUNT_PATTERN = re.compile(
    r"(?:₹|rs\.?|inr)\s*"
    r"(?P<number>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>crores?|cr\.?|lakhs?|lacs?|thousands?|million|billion)?",
    re.IGNORECASE,
)
LIST_PREFIX_PATTERN = re.compile(r"^\s*(?:[-•▪◦*]|\(?\d{1,3}[.)]|[a-zA-Z][.)])\s+")


@dataclass(frozen=True)
class ParsedAmount:
    value: Decimal
    raw: str


@dataclass
class CandidateBlock:
    title: str
    chunks: list[ChunkLike] = field(default_factory=list)
    start_page: int | None = None
    end_page: int | None = None
    score: int = 0

    @property
    def raw_text(self) -> str:
        return "\n\n".join(chunk.text.strip() for chunk in self.chunks if chunk.text)


@dataclass(frozen=True)
class ParsedRule:
    field_name: str
    operator: str
    value: Any
    unit: str
    human_text: str
    confidence: Decimal


def normalize_line(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip(" -–—:;\t")


def first_meaningful_line(value: str) -> str:
    for raw_line in (value or "").splitlines():
        line = normalize_line(raw_line)
        if 3 <= len(line) <= 220:
            return line
    return ""


def _clean_title(value: str) -> str:
    value = normalize_line(value)
    value = re.sub(
        r"^page\s+\d+\s+of\s+\d+\s*",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(r"^[•▪◦*]+\s*", "", value)
    value = re.sub(
        (
            r"^\s*(?:(?:scheme|item)\s*(?:no\.?|number)?\s*)?"
            r"(?:\d{1,3}(?:\.\d+)?[.)-]?\s+|"
            r"[ivxlcdm]+[.)]\s+)"
        ),
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"^(?:name of (?:the )?scheme|scheme name)\s*:\s*",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        (
            r"^\[(?:grant|loan|credit|fund|programme|program|"
            r"scheme)[^\]]*\]\s*"
        ),
        "",
        value,
        flags=re.IGNORECASE,
    )

    prose_suffix = re.match(
        (
            r"^(?P<title>.+?\b(?:scheme|programme|program|fund|"
            r"mission|initiative|yojana|labs?))\s+"
            r"(?:supports?|helps?|provides?|offers?|aims?|gives?|is)\b"
        ),
        value,
        flags=re.IGNORECASE,
    )
    if prose_suffix:
        value = prose_suffix.group("title")

    return value.strip().strip(" \"'“”‘’")[:500]


def _strip_visual_symbols(value: str) -> str:
    value = normalize_line(value)
    value = re.sub(r"^[^A-Za-z0-9₹]+", "", value)
    return normalize_line(value)


def _is_page_marker(value: str) -> bool:
    return bool(
        re.fullmatch(
            r"(?:page\s*)?\d+(?:\s+of\s+\d+)?",
            normalize_line(value),
            flags=re.IGNORECASE,
        )
    )


def _is_non_detail_page(value: str) -> bool:
    lowered = normalize_line(value[:8000]).casefold()

    signals = (
        "master summary table",
        "structured reference for all 65+ central government schemes",
        "decision tree - find your scheme",
        "decision tree – find your scheme",
        "these schemes have broader eligibility",
        "schemes and programs",
        "engagements with central ministries and cpsus",
        "part a - startup-specific schemes",
        "part a – startup-specific schemes",
    )

    if any(signal in lowered for signal in signals):
        return True

    if "startup india initiative" in lowered and "contents" in lowered:
        return True

    return False


def _is_publication_title(value: str) -> bool:
    title = normalize_line(value)
    lowered = title.casefold()

    if not lowered:
        return False

    exact = {
        "about - compendium of startup specific schemes",
        "about - compendium of startup specific schemes/",
        "contents",
        "exclusive benefits for startups",
        "exclusive benefits for ‘startups’",
        "government schemes and incentives",
        "initiative description",
        "initiatives",
        "part b - startup-relevant schemes",
        "schemes",
        "schemes and programs",
        "startup india initiative 2",
        "states / uts link to initiatives",
        "structured reference for all 65+ central government schemes",
        "table of contents",
        "undertaking schemes",
    }
    if lowered in exact:
        return True

    starts = (
        "master summary table",
        "decision tree - find your scheme",
        "decision tree – find your scheme",
        "these schemes have broader eligibility",
        "startup india initiative",
        "engagements with central ministries",
    )
    if lowered.startswith(starts):
        return True

    if re.match(
        r"^(?:part|chapter|section)\s+[a-z0-9ivxlcdm]+(?:\b|[-:])",
        lowered,
    ):
        return True

    number_tokens = re.findall(r"\b\d+(?:\.\d+)?\b", lowered)
    if len(number_tokens) >= 2 and len(title.split()) > 12:
        return True

    publication_words = (
        "playbook",
        "compendium",
        "handbook",
        "directory",
        "catalogue",
        "catalog",
    )
    ecosystem_words = (
        "government",
        "startup",
        "startups",
        "scheme",
        "schemes",
        "initiative",
        "initiatives",
    )

    return any(word in lowered for word in publication_words) and any(
        word in lowered for word in ecosystem_words
    )


def _match_section_heading(value: str) -> tuple[str, str] | None:
    line = _strip_visual_symbols(value)

    if not line or len(line) > 220 or line.endswith("."):
        return None

    labels: tuple[tuple[str, tuple[str, ...]], ...] = (
        (
            "eligibility",
            (
                "eligibility",
                "eligibility criteria",
                "eligibility conditions",
                "eligible applicants",
                "eligible entities",
                "eligible startups",
                "eligible beneficiaries",
                "target beneficiary",
                "target beneficiaries",
                "who can apply",
                "applicant criteria",
                "qualifications",
            ),
        ),
        (
            "benefit",
            (
                "benefit",
                "benefits",
                "what do you get",
                "financial assistance",
                "financial support",
                "funding assistance",
                "funding support",
                "grant amount",
                "loan amount",
                "incentive",
                "incentives",
                "support offered",
                "support provided",
                "nature of assistance",
            ),
        ),
        (
            "application",
            (
                "how to apply",
                "application process",
                "application procedure",
                "application link",
                "procedure for application",
                "mode of application",
                "link to application",
                "key link",
                "key links",
                "official link",
                "official links",
            ),
        ),
        (
            "document",
            (
                "document required",
                "documents required",
                "required document",
                "required documents",
                "documentation",
                "enclosure",
                "enclosures",
                "supporting document",
                "supporting documents",
                "documents to submit",
            ),
        ),
        (
            "objective",
            (
                "what is this",
                "brief",
                "objective",
                "objectives",
                "purpose",
                "overview",
                "about the scheme",
                "scheme description",
                "description",
            ),
        ),
        (
            "authority",
            (
                "implementing agency",
                "nodal agency",
                "implementing organization",
            ),
        ),
        (
            "summary",
            ("best suited for",),
        ),
    )

    for section, section_labels in labels:
        for label in section_labels:
            exact = re.fullmatch(
                rf"{re.escape(label)}\s*\??",
                line,
                flags=re.IGNORECASE,
            )
            if exact:
                return section, ""

            inline = re.match(
                rf"^{re.escape(label)}\s*(?::|[-–—])\s*(.+)$",
                line,
                flags=re.IGNORECASE,
            )
            if inline:
                return section, normalize_line(inline.group(1))

    return None


def _is_sentence_like(value: str) -> bool:
    title = normalize_line(value)
    lowered = title.casefold()
    words = title.split()

    if not title:
        return True

    if title[0].islower():
        return True

    if title.endswith((".", "?", "!", ",", ";", ":")):
        return True

    if len(words) > 18:
        return True

    if re.search(r"https?://|www\.", lowered):
        return True

    if lowered.startswith(
        (
            "brief:",
            "eligibility:",
            "benefit:",
            "benefits:",
            "link to application",
            "the scheme ",
            "the facility ",
            "this scheme ",
            "all coir ",
            "organizations can ",
            "institutions, ",
            "stakeholders, ",
            "providing ",
            "availing ",
            "rights and obligations",
            "government schemes, programmes",
        )
    ):
        return True

    sentence_phrases = (
        " supports startups",
        " supports student",
        " helps ",
        " provides ",
        " offers ",
        " can apply",
        " need to ",
        " is a government ",
        " are required to ",
        " is eligible ",
        " are eligible ",
        " has been ",
        " was launched ",
        " should normally ",
        " must be ",
        " can access ",
        " is essential",
        " applications need ",
        " winners of ",
        " were invited ",
        " so india ",
        " so the ",
    )

    return any(phrase in lowered for phrase in sentence_phrases)


def _has_title_signal(value: str) -> bool:
    lowered = normalize_line(value).casefold()

    extra_signals = (
        "atal tinkering",
        "bionest",
        "idex",
        "innovation square",
        "labs",
        "mudra",
        "nidhi",
        "prism",
        "samridh",
        "stand-up india",
        "tide",
        "yojana",
        "venture capital",
        "seed support",
        "technology development",
    )

    return any(signal in lowered for signal in TITLE_SIGNALS + extra_signals)


def looks_like_title(value: str) -> bool:
    title = _clean_title(value)
    lowered = title.casefold()
    words = title.split()

    if not title:
        return False

    if lowered in GENERIC_HEADINGS:
        return False

    if lowered in {
        "grant-in-aid",
        "incubators",
        "initiative",
        "initiatives",
        "mission",
        "programme",
        "program",
        "scheme",
        "schemes",
        "support varies",
        "vc fund-of funds",
    }:
        return False

    if _is_publication_title(title):
        return False

    if _match_section_heading(title):
        return False

    if _is_sentence_like(title):
        return False

    if len(title) < 5 or len(title) > 170:
        return False

    if len(words) < 2 or len(words) > 18:
        return False

    if not _has_title_signal(title):
        return False

    return True


def _is_title_continuation(value: str) -> bool:
    line = normalize_line(value)

    if not line or len(line) > 100:
        return False

    if _is_publication_title(line) or _match_section_heading(line):
        return False

    if line.endswith((".", "?", "!", ";", ":")):
        return False

    lowered = line.casefold()

    if lowered.startswith(
        (
            "brief",
            "eligib",
            "benefit",
            "application",
            "objective",
            "documents",
            "ministry",
            "department",
            "authority",
        )
    ):
        return False

    return not _is_sentence_like(line)


def title_from_chunk(chunk: ChunkLike) -> str:
    if _is_non_detail_page(chunk.text or ""):
        return ""

    heading = _clean_title(chunk.heading)
    generated_page_heading = bool(
        re.fullmatch(
            r"page\s+\d+(?:\s+of\s+\d+)?",
            heading,
            flags=re.IGNORECASE,
        )
    )

    if heading and not generated_page_heading and looks_like_title(heading):
        return heading

    lines: list[str] = []

    for raw_line in (chunk.text or "").splitlines():
        line = normalize_line(raw_line)

        if not line or _is_page_marker(line):
            continue

        if _is_publication_title(line):
            continue

        if not _strip_visual_symbols(line):
            continue

        lines.append(line)

        if len(lines) >= 18:
            break

    for index, raw_line in enumerate(lines):
        base = _clean_title(raw_line)

        if not base or _match_section_heading(base):
            continue

        candidates = [base]
        combined = base

        for offset in (1, 2):
            next_index = index + offset
            if next_index >= len(lines):
                break

            next_line = _strip_visual_symbols(lines[next_index])

            if not _is_title_continuation(next_line):
                break

            combined = _clean_title(f"{combined} {next_line}")
            candidates.append(combined)

        for candidate in reversed(candidates):
            if looks_like_title(candidate):
                return candidate

    return ""


def candidate_score(title: str, text: str) -> int:
    combined = f"{title}\n{text}".casefold()
    score = 2 if looks_like_title(title) else 0

    if len(text.split()) >= 25:
        score += 1

    signals = (
        (r"\beligib|who can apply|applicant", 1),
        (
            r"\bbenefit|financial assistance|financial support|"
            r"funding|grant|loan|incentive|₹|\binr\b|\brs\.",
            1,
        ),
        (
            r"\bhow to apply|application process|application link|"
            r"documents? required",
            1,
        ),
        (
            r"\bministry|department|implementing agency|authority",
            1,
        ),
    )

    for pattern, weight in signals:
        if re.search(pattern, combined, flags=re.IGNORECASE):
            score += weight

    return score


def _candidate_has_substance(block: CandidateBlock) -> bool:
    text = block.raw_text
    lowered = text.casefold()

    if len(text.split()) < 15:
        return False

    content_signals = (
        "eligib",
        "applicant",
        "benefit",
        "financial assistance",
        "financial support",
        "funding",
        "grant",
        "loan",
        "incentive",
        "how to apply",
        "application",
        "ministry",
        "department",
        "implementing agency",
        "₹",
        "inr ",
        "rs.",
    )

    return sum(signal in lowered for signal in content_signals) >= 2


def segment_candidates(
    chunks: Iterable[ChunkLike],
    *,
    min_score: int = 4,
    max_block_chars: int = 30000,
) -> list[CandidateBlock]:
    ordered = sorted(
        chunks,
        key=lambda item: item.chunk_index,
    )

    first_chunk_by_page: dict[int, int] = {}
    skipped_pages: set[int] = set()

    for chunk in ordered:
        if chunk.page_number is None:
            continue

        first_chunk_by_page.setdefault(
            chunk.page_number,
            chunk.chunk_index,
        )

    for chunk in ordered:
        if (
            chunk.page_number is not None
            and first_chunk_by_page.get(chunk.page_number) == chunk.chunk_index
            and _is_non_detail_page(chunk.text or "")
        ):
            skipped_pages.add(chunk.page_number)

    blocks: list[CandidateBlock] = []
    current: CandidateBlock | None = None
    seen: set[tuple[str, int | None]] = set()

    def flush() -> None:
        nonlocal current

        if current is None or not current.chunks:
            current = None
            return

        current.score = candidate_score(
            current.title,
            current.raw_text,
        )

        signature = (
            normalize_line(current.title).casefold(),
            current.start_page,
        )

        if (
            current.score >= min_score
            and _candidate_has_substance(current)
            and signature not in seen
        ):
            seen.add(signature)
            blocks.append(current)

        current = None

    for chunk in ordered:
        if chunk.page_number is not None and chunk.page_number in skipped_pages:
            if current is not None and current.end_page != chunk.page_number:
                flush()
            continue

        can_start_boundary = (
            chunk.page_number is None
            or first_chunk_by_page.get(chunk.page_number) == chunk.chunk_index
        )

        detected_title = title_from_chunk(chunk) if can_start_boundary else ""

        if detected_title:
            repeated_title = bool(
                current is not None
                and normalize_line(current.title).casefold()
                == normalize_line(detected_title).casefold()
            )

            if current is not None and current.chunks and not repeated_title:
                flush()

            if current is None:
                current = CandidateBlock(
                    title=detected_title,
                    start_page=chunk.page_number,
                    end_page=chunk.page_number,
                )

        elif current is None:
            continue

        if current is None:
            continue

        current.chunks.append(chunk)

        if current.start_page is None:
            current.start_page = chunk.page_number

        if chunk.page_number is not None:
            current.end_page = chunk.page_number

        if len(current.raw_text) >= max_block_chars:
            flush()

    flush()
    return blocks


def _infer_line_section(value: str) -> str:
    lowered = normalize_line(value).casefold()

    if re.search(
        r"\beligib|who can apply|applicant|must be|should be",
        lowered,
    ):
        return "eligibility"

    if re.search(
        (
            r"\bbenefit|financial assistance|financial support|"
            r"funding|grant|loan|incentive|interest subvention|"
            r"₹|\binr\b|\brs\."
        ),
        lowered,
    ):
        return "benefit"

    if re.search(
        r"\bapply|application|portal|https?://|www\.",
        lowered,
    ):
        return "application"

    if re.search(
        r"\bdocuments? required|required documents?|enclosures?",
        lowered,
    ):
        return "document"

    if re.search(
        r"\bministry|department|implementing agency|nodal agency",
        lowered,
    ):
        return "authority"

    return "summary"


def split_block_sections(
    block: CandidateBlock,
) -> tuple[
    dict[str, list[str]],
    dict[str, list[ChunkLike]],
]:
    values: dict[str, list[str]] = {
        "summary": [],
        "objective": [],
        "eligibility": [],
        "benefit": [],
        "application": [],
        "document": [],
        "authority": [],
    }
    evidence: dict[str, list[ChunkLike]] = {key: [] for key in values}

    normalized_title = normalize_line(block.title).casefold()

    for chunk in block.chunks:
        per_section: dict[str, list[str]] = {key: [] for key in values}
        heading = normalize_line(chunk.heading)
        current_section = "summary"

        if heading and not re.fullmatch(
            r"page\s+\d+(?:\s+of\s+\d+)?",
            heading,
            flags=re.IGNORECASE,
        ):
            heading_match = _match_section_heading(heading)
            if heading_match:
                current_section = heading_match[0]

        lines = [
            normalize_line(raw_line)
            for raw_line in (chunk.text or "").splitlines()
            if normalize_line(raw_line)
        ]

        index = 0
        title_scan_open = True
        title_accumulator = ""

        while index < len(lines):
            line = lines[index]

            if _is_page_marker(line) or _is_publication_title(line):
                index += 1
                continue

            stripped = _strip_visual_symbols(line)
            if not stripped:
                index += 1
                continue

            if title_scan_open:
                cleaned = _clean_title(stripped)
                proposed = normalize_line(f"{title_accumulator} {cleaned}").casefold()

                if proposed and normalized_title.startswith(proposed):
                    title_accumulator = normalize_line(f"{title_accumulator} {cleaned}")
                    index += 1
                    if proposed == normalized_title:
                        title_scan_open = False
                    continue

                title_scan_open = False

            section_match: tuple[str, str] | None = None
            consumed = 1

            for width in (1, 2, 3):
                window = lines[index : index + width]
                if len(window) != width:
                    break

                probe_parts = [_strip_visual_symbols(item) for item in window]
                probe_parts = [item for item in probe_parts if item]

                if not probe_parts:
                    continue

                probe = " ".join(probe_parts)
                match = _match_section_heading(probe)

                if match:
                    section_match = match
                    consumed = width
                    break

            if section_match:
                current_section, remainder = section_match
                if remainder:
                    per_section[current_section].append(remainder)
                index += consumed
                continue

            target_section = current_section

            if current_section == "summary":
                inferred = _infer_line_section(stripped)
                if inferred != "summary":
                    target_section = inferred

            per_section[target_section].append(stripped)
            index += 1

        for section, section_lines in per_section.items():
            text = "\n".join(section_lines).strip()

            if not text:
                continue

            values[section].append(text)

            if chunk not in evidence[section]:
                evidence[section].append(chunk)

    return values, evidence


def classify_section(heading: str, text: str) -> str:
    probe = normalize_line(heading) or first_meaningful_line(text)
    for section_name, pattern in SECTION_PATTERNS:
        if pattern.search(probe):
            return section_name
    return "summary"


def split_items(value: str, *, minimum_length: int = 4) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for raw_line in (value or "").splitlines():
        line = LIST_PREFIX_PATTERN.sub("", raw_line).strip()
        line = normalize_line(line)
        if len(line) < minimum_length:
            continue
        key = line.casefold()
        if key in seen:
            continue
        seen.add(key)
        items.append(line)
    return items


def extract_urls(value: str) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for match in URL_PATTERN.finditer(value or ""):
        url = match.group(0).rstrip(".,;:")
        if url not in seen:
            seen.add(url)
            output.append(url)
    return output


def parse_amounts(value: str) -> list[ParsedAmount]:
    amounts: list[ParsedAmount] = []
    multipliers = {
        "crore": Decimal("10000000"),
        "crores": Decimal("10000000"),
        "cr": Decimal("10000000"),
        "cr.": Decimal("10000000"),
        "lakh": Decimal("100000"),
        "lakhs": Decimal("100000"),
        "lac": Decimal("100000"),
        "lacs": Decimal("100000"),
        "thousand": Decimal("1000"),
        "thousands": Decimal("1000"),
        "million": Decimal("1000000"),
        "billion": Decimal("1000000000"),
    }
    for match in AMOUNT_PATTERN.finditer(value or ""):
        number = Decimal(match.group("number"))
        unit = (match.group("unit") or "").lower()
        amounts.append(
            ParsedAmount(
                value=number * multipliers.get(unit, Decimal("1")),
                raw=match.group(0),
            )
        )
    return amounts


def detect_kind(title: str, text: str = "") -> str:
    combined = f"{title} {text[:1000]}".lower()
    ordered = (
        ("guarantee", ("credit guarantee", "guarantee scheme")),
        ("loan", ("loan", "debt")),
        ("grant", ("grant",)),
        ("fund", ("fund", "seed fund")),
        ("recognition", ("recognition",)),
        ("registration", ("registration",)),
        ("certificate", ("certificate", "certification")),
        ("incubator", ("incubator", "accelerator")),
        ("benefit", ("benefit", "tax exemption")),
        ("policy", ("policy",)),
        ("program", ("programme", "program", "mission", "initiative")),
        ("scheme", ("scheme",)),
    )
    for kind, signals in ordered:
        if any(signal in combined for signal in signals):
            return kind
    return "unknown"


def detect_authority(value: str) -> tuple[str, str]:
    ministry = ""
    authority = ""
    patterns = (
        re.compile(r"\b(Ministry of [A-Z][^\n.;]{3,150})"),
        re.compile(r"\b(Department of [A-Z][^\n.;]{3,150})"),
        re.compile(r"\b([A-Z][A-Za-z &()-]{3,100} Authority)\b"),
    )
    for pattern in patterns:
        match = pattern.search(value or "")
        if not match:
            continue
        found = normalize_line(match.group(1))[:500]
        if found.startswith("Ministry of"):
            ministry = found
        elif not authority:
            authority = found
    return authority, ministry


def parse_rules(value: str) -> list[ParsedRule]:
    text = value or ""
    rules: list[ParsedRule] = []

    def add(
        field_name: str,
        operator: str,
        parsed_value: Any,
        unit: str,
        human_text: str,
        confidence: str,
    ) -> None:
        signature = (
            field_name,
            operator,
            str(parsed_value),
            normalize_line(human_text).casefold(),
        )
        if any(
            (
                item.field_name,
                item.operator,
                str(item.value),
                item.human_text.casefold(),
            )
            == signature
            for item in rules
        ):
            return

        rules.append(
            ParsedRule(
                field_name=field_name,
                operator=operator,
                value=parsed_value,
                unit=unit,
                human_text=normalize_line(human_text),
                confidence=Decimal(confidence),
            )
        )

    entity_patterns = (
        ("startup", r"\bstart[ -]?ups?\b"),
        ("MSME", r"\bmsmes?\b|micro,? small and medium"),
        (
            "alternative_investment_fund",
            r"\balternative investment funds?\b|\baifs?\b",
        ),
        ("incubator", r"\bincubators?\b|bioincubators?"),
        ("accelerator", r"\baccelerators?\b"),
        ("individual_innovator", r"\bindividual innovators?\b"),
        ("company", r"\bcompanies?\b|\bindian company\b"),
        ("section_8_entity", r"\bsection 8\b"),
        ("NBFC", r"\bnbfcs?\b|non[ -]?banking financial"),
        (
            "bank_or_financial_institution",
            r"\bbanks?\b|financial institutions?",
        ),
        (
            "educational_institution",
            r"educational institutes?|academic institutions?",
        ),
        ("researcher", r"\bresearchers?\b"),
        ("student", r"\bstudents?\b"),
        ("entrepreneur", r"\bentrepreneurs?\b"),
    )

    sector_patterns = (
        ("biotechnology", r"\bbiotech(?:nology)?\b|life sciences?"),
        ("healthcare", r"\bhealthcare\b|med[ -]?tech|diagnostics?"),
        ("agriculture", r"\bagri(?:culture)?[ -]?tech\b|agriculture"),
        ("telecommunications", r"telecom|digital communication"),
        ("software", r"software product|information technology"),
        ("defence", r"defen[cs]e"),
        ("space", r"\bspace\b|antariksh"),
        ("food_processing", r"food processing"),
        ("fisheries", r"fisheries"),
        ("livestock", r"livestock|animal husbandry|dairy"),
    )

    for sentence in re.split(r"(?<=[.;])\s+|\n+", text):
        sentence = normalize_line(sentence)
        if not sentence:
            continue

        lowered = sentence.casefold()

        if "dpiit" in lowered and any(
            term in lowered
            for term in (
                "recognised",
                "recognized",
                "recognition",
            )
        ):
            add(
                "dpiit_recognized",
                "eq",
                True,
                "boolean",
                sentence,
                "0.95",
            )

        if any(
            phrase in lowered
            for phrase in (
                "incorporated in india",
                "registered in india",
                "indian company",
                "indian startup",
                "headquarter in india",
                "headquartered in india",
            )
        ):
            add(
                "country_of_incorporation",
                "eq",
                "India",
                "country",
                sentence,
                "0.82",
            )

        age_match = re.search(
            (
                r"(?:not more than|within|up to|less than|maximum)\s+"
                r"(?P<years>\d+(?:\.\d+)?)\s+years?"
            ),
            lowered,
        )
        if age_match:
            months = int(Decimal(age_match.group("years")) * 12)
            add(
                "startup_age_months",
                "lte",
                months,
                "months",
                sentence,
                "0.86",
            )

        turnover_match = re.search(
            (
                r"turnover[^.;]{0,80}?"
                r"(?:not exceed|not exceeding|up to|less than)\s*"
                r"(?:₹|rs\.?|inr)?\s*(?P<number>\d+(?:\.\d+)?)\s*"
                r"(?P<unit>crores?|cr\.?|lakhs?|lacs?)"
            ),
            lowered,
        )
        if turnover_match:
            parsed = parse_amounts(
                f"INR {turnover_match.group('number')} {turnover_match.group('unit')}"
            )
            if parsed:
                add(
                    "annual_turnover_inr",
                    "lte",
                    str(parsed[0].value),
                    "INR",
                    sentence,
                    "0.88",
                )

        shareholding_match = re.search(
            (
                r"(?:shareholding|equity|stakes?)[^.;]{0,80}?"
                r"(?:at least|minimum|not less than|over|more than)\s*"
                r"(?P<percent>\d+(?:\.\d+)?)\s*%"
            ),
            lowered,
        )
        if shareholding_match:
            add(
                "eligible_shareholding_percent",
                "gte",
                shareholding_match.group("percent"),
                "percent",
                sentence,
                "0.84",
            )

        if "not formed by splitting" in lowered or "not formed by reconstruction" in lowered:
            add(
                "not_formed_by_reconstruction",
                "eq",
                True,
                "boolean",
                sentence,
                "0.88",
            )

        if "sebi" in lowered and re.search(r"register(?:ed|ation)", lowered):
            add(
                "regulatory_registration",
                "contains",
                "SEBI",
                "registration",
                sentence,
                "0.82",
            )

        if "rbi" in lowered and re.search(r"register(?:ed|ation)", lowered):
            add(
                "regulatory_registration",
                "contains",
                "RBI",
                "registration",
                sentence,
                "0.82",
            )

        for entity_type, pattern in entity_patterns:
            if re.search(pattern, lowered):
                add(
                    "eligible_entity_type",
                    "contains",
                    entity_type,
                    "entity_type",
                    sentence,
                    "0.72",
                )

        for sector, pattern in sector_patterns:
            if re.search(pattern, lowered):
                add(
                    "eligible_sector",
                    "contains",
                    sector,
                    "sector",
                    sentence,
                    "0.68",
                )

        location_tiers = sorted(
            {
                match.group(1).upper().replace("-", " ")
                for match in re.finditer(
                    r"\btier[ -]?(ii|iii)\b",
                    lowered,
                    flags=re.IGNORECASE,
                )
            }
        )
        for tier in location_tiers:
            add(
                "eligible_location_tier",
                "contains",
                f"Tier {tier}",
                "location_tier",
                sentence,
                "0.72",
            )

        stage_patterns = (
            ("ideation", r"\bideation\b"),
            ("early_stage", r"early[ -]?stage|pre[ -]?seed"),
            ("seed", r"\bseed[ -]?stage\b"),
            ("prototype", r"\bprototype\b|proof of concept|\bpoc\b"),
            ("commercialisation", r"commerciali[sz]ation"),
            ("scaling", r"\bscal(?:e|ing)\b|growth[ -]?stage"),
        )
        for stage, pattern in stage_patterns:
            if re.search(pattern, lowered):
                add(
                    "eligible_startup_stage",
                    "contains",
                    stage,
                    "startup_stage",
                    sentence,
                    "0.66",
                )

    return rules


def stable_candidate_key(title: str, start_page: int | None, raw_text: str) -> str:
    payload = f"{normalize_line(title).casefold()}|{start_page}|{raw_text[:1000]}"
    return hashlib.sha256(payload.encode("utf-8", errors="replace")).hexdigest()
