# Synthetic dataset from templates + random phones/UPI ids/amounts. No real complaints.
# usage: python -m ml.generate_synthetic
import csv
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "synthetic_complaints.csv"

AREAS = ["Rohini", "Dwarka", "Laxmi Nagar", "Saket", "Karol Bagh", "Janakpuri", "Shahdara", "Pitampura",
         "Mayur Vihar", "Vasant Kunj", "Uttam Nagar", "Chandni Chowk"]
BANKS = ["ybl", "okaxis", "paytm", "oksbi", "ibl", "okhdfcbank", "apl"]
NAMES = ["lucky.kbc", "rahul.verma88", "jobs.hr.desk", "trade.guru", "support.help", "refund.team",
         "amit.k22", "priya.s", "invest.daily", "kyc.update", "cash.win", "hr.placement"]


def phone():
    return f"{random.choice('6789')}{random.randint(100000000, 999999999)}"


def upi():
    return f"{random.choice(NAMES)}{random.randint(1, 99)}@{random.choice(BANKS)}"


def amount():
    return f"{random.choice([1500, 2999, 5000, 8500, 12000, 15000, 25000, 49999, 75000, 120000, 250000]):,}"


TEMPLATES = {
    "upi_fraud": [
        "I received a request on PhonePe from {upi}. The caller from {phone} said it was to receive money but Rs {amt} got debited from my account.",
        "Someone called from {phone} pretending to be from my bank and asked me to approve a UPI request. I lost Rs {amt} to {upi}.",
        "Mujhe {phone} se call aaya, bola galti se paise bhej diye wapas karo. Maine {upi} pe Rs {amt} bhej diye, baad me pata chala fraud tha.",
        "A buyer on OLX contacted me from {phone} and sent a QR code. When I scanned it Rs {amt} was deducted and sent to {upi}.",
        "Fraudster sent a collect request from {upi} saying it was a cashback. I entered my UPI PIN and lost Rs {amt}. His number is {phone}.",
    ],
    "lottery_scam": [
        "I got a call from {phone} saying I won KBC lottery of 25 lakh. They asked me to pay Rs {amt} processing fee to {upi}. After paying they blocked me.",
        "Whatsapp message from {phone} said I won a lucky draw car. To claim it I paid Rs {amt} as tax to {upi} but no prize came.",
        "Kaun Banega Crorepati ke naam pe {phone} se call aaya, lottery jeetne ka bola aur Rs {amt} GST ke naam pe {upi} pe le liye.",
        "Received SMS that my mobile number won 50 lakh in a lucky draw. Called {phone}, they took Rs {amt} as registration charges via {upi}.",
        "A person on {phone} told me I won an iPhone in an online contest. He asked for Rs {amt} delivery charges to {upi} and then stopped answering.",
    ],
    "job_scam": [
        "I got a job offer on WhatsApp from {phone} for a work from home job. They took Rs {amt} as registration fee on {upi} and never gave any work.",
        "Fake HR from {phone} offered me a job at a big company and asked for Rs {amt} for training and laptop. I paid to {upi}.",
        "Mujhe part time job ka message aaya, YouTube videos like karne ke paise milenge bola. Task ke naam pe Rs {amt} {upi} pe le liye. Number {phone}.",
        "Telegram task job scam. First they paid small amounts then asked me to deposit Rs {amt} to {upi}. Contact number was {phone}.",
        "A placement agency called from {phone} promising a government job. They demanded Rs {amt} as security deposit through {upi}.",
    ],
    "investment_scam": [
        "I joined a stock market tips group. The admin {phone} asked me to invest in an app promising 30 percent returns. I invested Rs {amt} via {upi}, now I cannot withdraw.",
        "Crypto trading website showed big profits but when I tried to withdraw they asked for more tax. Total Rs {amt} paid to {upi}. Contact {phone}.",
        "Ek aadmi ne {phone} se trading app me paisa double karne ka bola. Maine Rs {amt} {upi} pe invest kiye, ab app band hai.",
        "Fake IPO allotment scheme. They asked Rs {amt} on {upi} for guaranteed shares. Their number {phone} is now switched off.",
        "Someone on Instagram promised daily returns on forex trading. I sent Rs {amt} to {upi}. He used number {phone}.",
    ],
    "sextortion": [
        "Someone is threatening to leak my morphed photos unless I pay Rs {amt}. He keeps calling from {phone} and asked money on {upi}.",
        "I received a video call from {phone}, it was recorded and now they are blackmailing me with an obscene video. They want Rs {amt} on {upi}.",
        "Ek ladki ne video call kiya aur ab {phone} se dhamki de rahe hai ki video viral kar denge. Rs {amt} maang rahe hai {upi} pe.",
        "A person I met on a dating app is threatening to send my private photos to my family unless I pay Rs {amt}. Number {phone}.",
        "Blackmail from {phone}: they say they have my intimate video and will leak it. Already paid Rs {amt} to {upi}, they want more.",
    ],
    "account_hacking": [
        "My Instagram account was hacked and the hacker is asking my friends for money. He is using number {phone} and UPI {upi}.",
        "Someone took over my WhatsApp after I shared an OTP with a caller from {phone}. Now he is asking my contacts to send money to {upi}.",
        "Mera Facebook account hack ho gaya, ab mere naam se logo se paise maang raha hai {upi} pe. Usne {phone} se OTP manga tha.",
        "My email and bank app were accessed after I installed AnyDesk on the advice of a caller from {phone}. Rs {amt} transferred to {upi}.",
        "Hacker changed the password of my Gmail and is sending messages asking for Rs {amt} to {upi}. The recovery number was changed to {phone}.",
    ],
    "phishing": [
        "I got an SMS that my electricity connection will be cut tonight and to call {phone}. They sent a link and Rs {amt} was taken from my card.",
        "Received a message saying my KYC is pending with a link. I filled my bank details and Rs {amt} got debited. Message came from {phone}.",
        "Bank ke naam pe fake link aaya, KYC update karne ko bola. Details daalte hi Rs {amt} kat gaye. Number {phone} tha.",
        "Email pretending to be from income tax department asked me to claim a refund through a link. I lost Rs {amt}. Caller {phone} followed up.",
        "Got a fake courier message that my parcel is stuck and to pay Rs 25 on a link. After entering card details Rs {amt} was stolen. Contact {phone}.",
    ],
}


def main(per_template: int = 6, seed: int = 42) -> None:
    random.seed(seed)
    rows = []
    for category, templates in TEMPLATES.items():
        for t_index, template in enumerate(templates):
            for _ in range(per_template):
                rows.append(
                    {
                        "text": template.format(phone=phone(), upi=upi(), amt=amount()),
                        "category": category,
                        "area": random.choice(AREAS),
                        "template_id": f"{category}-{t_index}",
                    }
                )
    random.shuffle(rows)
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "category", "area", "template_id"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} synthetic complaints to {OUT}")


if __name__ == "__main__":
    main()
