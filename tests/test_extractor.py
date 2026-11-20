from app.services.extractor import extract


def test_phone_formats_are_normalised():
    text = "Calls came from +91 98765-43210, 919876543210, 09876543210 and 7012345678"
    assert extract(text).phones == ["9876543210", "7012345678"]


def test_upi_not_confused_with_email():
    found = extract("Paid to lucky.kbc@ybl, then he emailed me from scam.guy@gmail.com")
    assert found.upi_ids == ["lucky.kbc@ybl"]
    assert found.emails == ["scam.guy@gmail.com"]


def test_amount_formats():
    found = extract("Paid Rs 15,000 then ₹2.5 lakh and INR 500, also 8500 rupees and rs.50k")
    assert found.amounts == [15000, 250000, 500, 50000, 8500]
    assert found.total_amount == 324000


def test_account_number_needs_keyword_and_is_not_a_phone():
    found = extract("Money went to account no 9876543210123 and a/c: 7890123456. Order id 123456789012")
    assert found.accounts == ["9876543210123", "7890123456"]
    assert found.phones == []


def test_urls():
    found = extract("Fake KYC link https://sbi-kyc-update.in/login?id=5, also www.free-prize.xyz.")
    assert found.urls == ["https://sbi-kyc-update.in/login?id=5", "www.free-prize.xyz"]


def test_hinglish_text():
    found = extract("Maine 9123456789 pe call kiya aur Rs 8,500 bhej diye rahul99@okaxis pe")
    assert found.phones == ["9123456789"]
    assert found.upi_ids == ["rahul99@okaxis"]
    assert found.amounts == [8500]
