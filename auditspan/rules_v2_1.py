"""SPEC-v2.1: fixes found by review after the blind hold-out. Not blind. Frozen v2 is kept unchanged beside it."""

import re
from itertools import islice

from .extract import (
    CASE,
    DASH,
    REQUIREMENT_LABEL,
    Fact,
    costs_answer,
    labelled_values,
    questioned_costs,
    repeat,
    repeat_answer,
    severity,
)
from .requirements_v2 import LABEL_V2, TITLE_LINES, TITLE_PART_MAX, letters_v2

EXPLICIT_REPEAT = r"^(yes|no)\b"
NONE_OF = r"^\s*(?:none|no)\s+of\b"
# Submitting the audit itself is not the Reporting compliance requirement.
AUDIT_FILING = r"reporting deadline[^\n]*single audit|audit reporting"
BODY_HEADING = (
    r"[^\S\n]*(?:criteria|condition|cause|effect|context|recommendation|questioned|statement of condition"
    r"|views? of responsible)"
)
PROGRAM_LINE = r"[^\S\n]*(?:federal|program|assistance|aln|cfda|grantor|pass|award|information)"


def repeat_answer_v2_1(value: str) -> bool | None:
    """An explicit yes or no wins, so "Yes, ... has not been corrected" is a repeat."""
    explicit = re.match(EXPLICIT_REPEAT, value, CASE)
    return explicit.group(1).lower() == "yes" if explicit else repeat_answer(value)


def costs_answer_v2_1(value: str) -> bool | None:
    """ "None of the $50,000 was allowable" questions the amount, so it is not a no-costs answer."""
    return costs_answer(re.sub(NONE_OF, "", value, count=1, flags=CASE))


def letters_v2_1(value: str, lead_code: bool = True) -> str:
    return letters_v2(re.sub(AUDIT_FILING, " ", value, flags=CASE), lead_code)


def _title_letters(line: str) -> str:
    for part in re.split(DASH, line):
        found = letters_v2_1(part, lead_code=False)
        if found:
            return found if len(part.strip()) <= TITLE_PART_MAX else ""
    return ""


def _title(text: str) -> Fact | None:
    """Like v2, but the scan stops at the first body-section heading (criteria and the like)."""
    for match in islice(re.finditer(r"[^\n]*\S[^\n]*", text), TITLE_LINES):
        line = match.group()
        if re.match(BODY_HEADING, line, CASE):
            return None
        found = "" if re.match(PROGRAM_LINE, line, CASE) else _title_letters(line)
        if found:
            return Fact("requirements", found, match.start(), match.end(), line)
    return None


def requirements_v2_1(text: str) -> Fact | None:
    for pattern in (REQUIREMENT_LABEL, LABEL_V2):
        for value, start, end in labelled_values(pattern, text):
            found = letters_v2_1(value)
            if found:
                return Fact("requirements", found, start, end, text[start:end])
    return _title(text)


def extract_v2_1(text: str) -> dict[str, Fact | None]:
    return {
        "severity": severity(text),
        "repeat": repeat(text, repeat_answer_v2_1),
        "questioned_costs": questioned_costs(text, costs_answer_v2_1),
        "requirements": requirements_v2_1(text),
    }
