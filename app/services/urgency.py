# Rule based on purpose so every score can be explained to the officer.
import re

CATEGORY_BASE = {
    "sextortion": 45,
    "account_hacking": 30,
    "upi_fraud": 25,
    "investment_scam": 25,
    "phishing": 20,
    "job_scam": 20,
    "lottery_scam": 20,
}
DEFAULT_BASE = 20

# (pattern, points, reason)
SIGNALS = [
    (r"\b(threat\w*|blackmail\w*|dhamki|dhamka\w*|kill|maar dunga|jaan se)\b", 25, "threat to the victim"),
    (r"\b(suicide|khudkushi|end my life|marna chahta|marna chahti)\b", 40, "victim mentions self-harm"),
    (r"\b(nude|naked|morph\w*|intimate|private (photo|video)s?|obscene|leak)\b", 20, "intimate images involved"),
    (r"\b(child|minor|my (son|daughter)|beti|beta|school (boy|girl))\b", 20, "a minor may be involved"),
    (r"\b(today|just now|abhi|aaj|1 hour|few minutes|an hour ago|minutes ago)\b", 15,
     "very recent: money may still be frozen"),
    (r"\b(otp|remote access|anydesk|teamviewer|screen ?share)\b", 10, "attacker may still have account access"),
]


def score_urgency(
    category: str | None,
    text: str,
    amount_involved: float = 0.0,
    linked_count: int = 0,
) -> tuple[int, str, list[str]]:
    score = CATEGORY_BASE.get(category or "", DEFAULT_BASE)
    reasons = [f"category: {category or 'unknown'}"]
    lowered = text.lower()

    for pattern, points, reason in SIGNALS:
        if re.search(pattern, lowered):
            score += points
            reasons.append(reason)

    if amount_involved >= 100_000:
        score += 25
        reasons.append(f"large amount involved: ₹{amount_involved:,.0f}")
    elif amount_involved >= 10_000:
        score += 12
        reasons.append(f"amount involved: ₹{amount_involved:,.0f}")
    elif amount_involved > 0:
        score += 5
        reasons.append(f"amount involved: ₹{amount_involved:,.0f}")

    if linked_count:
        score += min(linked_count * 5, 20)
        reasons.append(f"linked to {linked_count} other complaint(s): possible repeat offender")

    score = max(0, min(100, score))
    level = "high" if score >= 70 else "medium" if score >= 40 else "low"
    return score, level, reasons
