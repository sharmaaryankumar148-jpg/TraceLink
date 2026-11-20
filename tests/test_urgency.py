from app.services.urgency import score_urgency


def test_sextortion_with_threat_is_high():
    score, level, reasons = score_urgency(
        "sextortion", "He is threatening to leak my morphed photos", amount_involved=50000
    )
    assert level == "high"
    assert "threat to the victim" in reasons
    assert "intimate images involved" in reasons


def test_small_old_fraud_is_low():
    score, level, _ = score_urgency("lottery_scam", "I paid a fee last month for a prize", amount_involved=1500)
    assert level == "low"


def test_links_raise_urgency_and_score_is_capped():
    base, _, _ = score_urgency("upi_fraud", "lost money", 20000, linked_count=0)
    linked, _, reasons = score_urgency("upi_fraud", "lost money", 20000, linked_count=3)
    assert linked == base + 15
    assert any("repeat offender" in r for r in reasons)
    capped, _, _ = score_urgency("sextortion", "threat suicide leak nude child abhi otp", 10**7, 10)
    assert capped == 100
