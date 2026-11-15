"""SPEC-v2 requirements extraction: more label wordings, explicit letter codes and the finding's title line."""

import re
from itertools import islice

from .extract import CASE, DASH, LETTERS, REQUIREMENT_LABEL, Fact, labelled_values, requirement_letters

LETTERS_V2 = {
    **LETTERS,
    "A": r"activities allowed|allowable activities|allowable costs? ?(?:and|/|or) ?activit",
    "B": r"allowable (?:activities ?(?:and|/|or) ?)?costs?|cost principles",
    "N": r"special tests?",
}
# Phrases that contain a requirement name but are not a compliance requirement.
NOT_A_REQUIREMENT = (
    r"uniform administrative requirements,? cost principles"
    r"|(?:sefa|statements?|close(?: and)?|clearinghouse|over financial|single audit)\s+reporting(?: package)?"
    r"|reporting (?:package|process)"
)
PAREN_CODE = r"\(([A-CE-JL-N])\.?\)"
LEAD_CODE = r"^\s*([A-CE-JL-N])\s?[.–—-]\s?(?=[A-Za-z])"
LABEL_V2 = (
    r"(?:compliance requirements?(?: code| affected| type)?(?:\(s\))?"
    r"|^[^\S\n]*(?:requirement|area|control category|description|(?:type of finding:[^\S\n]*)?compliance))"
    r"[^\S\n]*[:–—-][^\S\n]*(?P<value>[^\n]*)"
)
TITLE_LINES = 3
TITLE_PART_MAX = 120
NOT_TITLE = (
    r"[^\S\n]*(?:criteria|condition|cause|effect|context|recommendation|questioned|federal|program|assistance"
    r"|aln|cfda|grantor|pass|award|information)"
)


def letters_v2(value: str, lead_code: bool = True) -> str:
    """Explicit letter codes win. Otherwise names, after removing phrases that only look like requirements."""
    codes = set(re.findall(PAREN_CODE, value))
    if lead_code:
        codes.update(re.findall(LEAD_CODE, value))
    if codes:
        return "".join(letter for letter in LETTERS if letter in codes)
    return requirement_letters(re.sub(NOT_A_REQUIREMENT, " ", value, flags=CASE), LETTERS_V2)


def _title_letters(line: str) -> str:
    """Letters from the first dash part of a title line that names a requirement, if that part is title-sized."""
    for part in re.split(DASH, line):
        found = letters_v2(part, lead_code=False)
        if found:
            return found if len(part.strip()) <= TITLE_PART_MAX else ""
    return ""


def _title(text: str) -> Fact | None:
    for match in islice(re.finditer(r"[^\n]*\S[^\n]*", text), TITLE_LINES):
        line = match.group()
        found = "" if re.match(NOT_TITLE, line, CASE) else _title_letters(line)
        if found:
            return Fact("requirements", found, match.start(), match.end(), line)
    return None


def requirements_v2(text: str) -> Fact | None:
    for pattern in (REQUIREMENT_LABEL, LABEL_V2):
        for value, start, end in labelled_values(pattern, text):
            found = letters_v2(value)
            if found:
                return Fact("requirements", found, start, end, text[start:end])
    return _title(text)
