"""Rule-based extraction of cited facts from Single Audit finding text."""

import re
from dataclasses import dataclass

FIELDS = ("severity", "repeat", "questioned_costs", "requirements")

CASE = re.IGNORECASE
LINES = re.IGNORECASE | re.MULTILINE

MAX_VALUE = 150
LETTERS = {
    "A": r"activities allowed|allowable activities",
    "B": r"allowable costs?|cost principles",
    "C": r"cash management",
    "E": r"eligibility",
    "F": r"equipment|real property",
    "G": r"matching|level of effort|earmarking",
    "H": r"period of (?:performance|availability)",
    "I": r"procurement|suspension|debarment",
    "J": r"program income",
    "L": r"reporting",
    "M": r"subrecipient monitoring",
    "N": r"special tests",
}
# SPEC-v2: singular "special test", and the Single Audit "reporting package" is not the Reporting requirement.
LETTERS_V2 = {**LETTERS, "L": r"reporting(?! package)", "N": r"special tests?"}
TAIL = r"[^\S\n]*[:–—-]?[^\S\n]*(?P<value>[^\n]*)"
NEXT_LINE = r"\n\s*(\S[^\n]*)"
SEVERITY = r"\b(?:material weakness|significant deficiency)\b"
BEFORE = [
    r"(?:\[\s*\]|☐|□)\s*$",
    r"\b(?:not|no|nor)\b[^.\n]{0,30}$",
    r"(?:\bor|\band/or)\s+(?:an?\s+)?$",
]
AFTER = [
    r"^\s+(?:or|and/or)\s+(?:an?\s+)?(?:material|significant)\b",
    r"^\s+is\s+a\s+deficiency",
    r"^[^.\n]{0,40}\bover financial reporting\b",
]
REPEAT_LABEL = (
    r"^[^\S\n]*(?:identification (?:as|of)[^:\n–]*?repeat[^:\n–]*(?=[:–])"
    r"|repeat finding(?: from (?:the )?prior (?:year\(s\)|years?|audits?))?\??"
    r"|prior[- ]year finding(?: number)?)" + TAIL
)
REPEAT_NO = r"^(?:no\b|n/a|none|new\b)|^[^.]*\bnot\b"
REPEAT_YES = (
    r"^(?:yes\b|this (?:finding )?(?:is|was) a repeat|repeat (?:finding )?of|(?:a )?similar|see\b"
    r"|(?:finding )?(?:no\.? ?)?\d{4}-\d{3})"
)
NOT_REPEAT_SENTENCE = r"\bnot a repeat(?: finding)?\b"
REPEAT_SENTENCE = r"\bthis (?:finding )?(?:is|was) a repeat\b|\bis a repeat of\b|\brepeat finding of \d{4}-\d{3}"
QUESTIONED_LABEL = r"^[^\S\n]*(?:known |total |likely )?questioned costs?(?: amount)?" + TAIL
BELOW_THRESHOLD = r"\b(?:threshold|below|under|less than)\b"
NO_COSTS = r"^(?:none|n/?a\b|not applicable|no\b|\$\s*0(?:\.00)?(?![\d.,])|0(?![\d.,])|\$\s*-)"
AMOUNT = r"\$\s*(\d[\d,]*(?:\.\d+)?)"
NO_COSTS_SENTENCE = r"\b(?:there (?:were|are|was|is) no|no) (?:known )?questioned costs?\b"
REQUIREMENT_LABEL = r"^[^\S\n]*(?:type of )?compliance requirements?(?: affected| type)?(?:\(s\))?" + TAIL
DASH = r"\s[–—-]\s"

_NEXT_LINE = re.compile(NEXT_LINE)


@dataclass(frozen=True)
class Fact:
    field: str
    value: str | bool
    start: int
    end: int
    quote: str


def _labelled_values(pattern: str, text: str):
    for match in re.finditer(pattern, text, LINES):
        value = match.group("value")
        end = match.end()
        stripped = value.strip()
        if not stripped:
            next_line = _NEXT_LINE.match(text, match.end())
            if next_line is None:
                continue
            value = next_line.group(1)
            end = next_line.end(1)
            stripped = value.strip()
        if not stripped or len(stripped) > MAX_VALUE:
            continue
        yield stripped, match.start(), end


def severity(text: str) -> Fact | None:
    for match in re.finditer(SEVERITY, text, CASE):
        before = text[max(0, match.start() - 40) : match.start()]
        after = text[match.end() : match.end() + 40]
        if re.search(BEFORE[0], before) or any(re.search(p, before, CASE) for p in BEFORE[1:]):
            continue
        if any(re.match(p, after, CASE) for p in AFTER):
            continue
        value = "material_weakness" if match.group(0).lower() == "material weakness" else "significant_deficiency"
        return Fact("severity", value, match.start(), match.end(), text[match.start() : match.end()])
    return None


def repeat(text: str) -> Fact | None:
    for value, start, end in _labelled_values(REPEAT_LABEL, text):
        if re.search(REPEAT_NO, value, CASE):
            return Fact("repeat", False, start, end, text[start:end])
        if re.match(REPEAT_YES, value, CASE):
            return Fact("repeat", True, start, end, text[start:end])
    for pattern, value in ((NOT_REPEAT_SENTENCE, False), (REPEAT_SENTENCE, True)):
        match = re.search(pattern, text, CASE)
        if match:
            return Fact("repeat", value, match.start(), match.end(), text[match.start() : match.end()])
    return None


def questioned_costs(text: str) -> Fact | None:
    for value, start, end in _labelled_values(QUESTIONED_LABEL, text):
        if re.search(BELOW_THRESHOLD, value, CASE):
            continue
        if re.match(NO_COSTS, value, CASE):
            return Fact("questioned_costs", False, start, end, text[start:end])
        amount = re.search(AMOUNT, value)
        if amount and float(amount.group(1).replace(",", "")) > 0:
            return Fact("questioned_costs", True, start, end, text[start:end])
    match = re.search(NO_COSTS_SENTENCE, text, CASE)
    if match:
        return Fact("questioned_costs", False, match.start(), match.end(), text[match.start() : match.end()])
    return None


def requirement_letters(value: str, letters: dict[str, str] = LETTERS) -> str:
    for part in re.split(DASH, value):
        found = "".join(letter for letter, pattern in letters.items() if re.search(pattern, part, CASE))
        if found:
            return found
    return ""


def requirements(text: str, letters: dict[str, str] = LETTERS) -> Fact | None:
    for value, start, end in _labelled_values(REQUIREMENT_LABEL, text):
        found = requirement_letters(value, letters)
        if found:
            return Fact("requirements", found, start, end, text[start:end])
    return None


def extract(text: str, letters: dict[str, str] = LETTERS) -> dict[str, Fact | None]:
    return {
        "severity": severity(text),
        "repeat": repeat(text),
        "questioned_costs": questioned_costs(text),
        "requirements": requirements(text, letters),
    }
