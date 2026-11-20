import re
from dataclasses import dataclass, field

# +91 / 91 / 0 prefix optional, 10 digits starting 6-9, allows "98765 43210"
PHONE_RE = re.compile(r"(?<![\d\w])(?:\+?91[\s-]?|0)?([6-9]\d{4})[\s-]?(\d{5})(?!\d)")

EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")

# handle part has no dot (ybl, okaxis...), lookahead stops it eating half an email
UPI_RE = re.compile(r"\b([\w.-]{2,256}@[a-zA-Z]{2,64})\b(?!\.\w)")

URL_RE = re.compile(r"\b(?:https?://|www\.)[^\s<>\"']+", re.IGNORECASE)

# only count long numbers as accounts when "account"/"a/c" is written before them
ACCOUNT_RE = re.compile(
    r"(?:a/c|acc(?:ount)?|acct|khata)\s*(?:no\.?|number|num)?\s*[:#-]?\s*(\d{9,18})\b",
    re.IGNORECASE,
)

_NUM = r"(\d[\d,]*(?:\.\d+)?)"
_UNIT = r"\s*(lakh|lac|lakhs|k|thousand|crore|cr)?\b"
AMOUNT_RES = [
    re.compile(r"(?:₹|rs\.?|inr|rupees)\s*" + _NUM + _UNIT, re.IGNORECASE),
    re.compile(_NUM + _UNIT + r"\s*(?:rs\.?|rupees|rupaye|rupay|inr)(?!\w)", re.IGNORECASE),
]
_MULTIPLIER = {"k": 1e3, "thousand": 1e3, "lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "crore": 1e7, "cr": 1e7}


@dataclass
class Extraction:
    phones: list[str] = field(default_factory=list)
    upi_ids: list[str] = field(default_factory=list)
    accounts: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    amounts: list[float] = field(default_factory=list)

    def identifiers(self) -> list[tuple[str, str]]:
        return (
            [("phone", v) for v in self.phones]
            + [("upi", v) for v in self.upi_ids]
            + [("account", v) for v in self.accounts]
            + [("email", v) for v in self.emails]
            + [("url", v) for v in self.urls]
        )

    @property
    def total_amount(self) -> float:
        return sum(self.amounts)


def _unique(items):
    seen, out = set(), []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _parse_amount(number: str, unit: str | None) -> float | None:
    try:
        value = float(number.replace(",", ""))
    except ValueError:
        return None
    if unit:
        value *= _MULTIPLIER.get(unit.lower(), 1)
    return value if value > 0 else None


def extract(text: str) -> Extraction:
    result = Extraction()

    result.emails = _unique(m.group(0).lower() for m in EMAIL_RE.finditer(text))

    text_wo_emails = EMAIL_RE.sub(" ", text)
    result.upi_ids = _unique(m.group(1).lower() for m in UPI_RE.finditer(text_wo_emails))

    result.urls = _unique(m.group(0).rstrip(".,;:!?)").lower() for m in URL_RE.finditer(text))

    result.accounts = _unique(m.group(1) for m in ACCOUNT_RE.finditer(text))

    # a 10 digit account number shouldn't also show up as a phone
    text_for_phones = ACCOUNT_RE.sub(" ", text)
    result.phones = _unique(m.group(1) + m.group(2) for m in PHONE_RE.finditer(text_for_phones))

    amounts = []
    taken: list[tuple[int, int]] = []
    for pattern in AMOUNT_RES:
        for m in pattern.finditer(text):
            if any(m.start() < end and start < m.end() for start, end in taken):
                continue
            value = _parse_amount(m.group(1), m.group(2))
            if value is not None:
                amounts.append(value)
                taken.append((m.start(), m.end()))
    result.amounts = amounts

    return result
