"""
Rakshak AI — Local Text-Testing CLI Tool
Test LLM cybercrime understanding, structured entity extraction,
context-aware follow-up question generation, and formal complaint drafting
WITHOUT requiring Twilio or spending telephony credits.

Usage:
    python test_llm.py
    python test_llm.py --scenario otp
    python test_llm.py --text "My bank account was debited Rs 15000 after sharing OTP" --lang en
"""

import sys
import json
import argparse
from pathlib import Path

# Fix Windows console UTF-8 printing for Devanagari Hindi
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from llm_analyzer import analyze_incident_with_llm, CybercrimeIncidentAnalysis
from main import generate_pdf_report

PRESET_SCENARIOS = {
    "otp": {
        "title": "Hindi — Banking KYC / OTP Fraud",
        "lang": "hi",
        "caller": "रमेश गुप्ता",
        "story": "एक्चुअली मुझे 9876543210 से कॉल आया और उन्होंने बोला कि आपका SBI बैंक खाता KYC न होने के कारण बंद हो जाएगा। उन्होंने मुझसे एक ओटीपी पूछा तो मैंने दे दिया। फिर तुरंत मेरे खाते से 45,000 रुपये कटने का मैसेज आया। UTR नंबर 839201928372 है।",
        "details": "मुझे फ्रॉड कॉलर ने कहा था कि वह एसबीआई शाखा प्रबंधक बोल रहा है।",
    },
    "job": {
        "title": "Hinglish — Telegram Work-From-Home Task Scam",
        "lang": "hi",
        "caller": "Pooja Sharma",
        "story": "Mujhe Telegram par ek part time job offer aayi thi @dailyincome24 se. Unhone YouTube video like karne ke paise dene ka vada kiya. Shuru me 500 diye, fir prepaid task ke naam par 25000 rupaye scammer ke UPI ID taskpay@okaxis par transfer karwa liye aur ab block kar diya.",
        "details": "Mera 25000 ka loss hua hai, maine Google Pay se payment ki thi.",
    },
    "olx": {
        "title": "English — OLX / QR Code Payment Scam",
        "lang": "en",
        "caller": "Vikram Malhotra",
        "story": "I listed a sofa on OLX for Rs 18,000. A buyer claiming to be an army officer from Pune contacted me and sent a QR code on WhatsApp saying scan this to receive advance payment. When I scanned and entered my UPI PIN, Rs 18,000 was debited from my HDFC account instead of credited.",
        "details": "The suspect phone number was 9123456789 and UPI ID was armytrade@icici.",
    },
    "loan": {
        "title": "Hindi — Instant Loan App Extortion",
        "lang": "hi",
        "caller": "सुनील कुमार",
        "story": "मैंने एक ऑनलाइन ऐप 'EasyCash' से 5000 रुपये का लोन लिया था। उन्होंने सिर्फ 3500 खाते में डाले और अब 15000 रुपये मांग रहे हैं। वे मेरी फोन गैलरी और संपर्कों को बदनाम करने की धमकी दे रहे हैं।",
        "details": "वे अज्ञात नंबरों से फोन करके गाली-गलौज कर रहे हैं।",
    },
}


def run_test(scenario_key: str = None, custom_text: str = None, lang: str = "hi", caller_name: str = "नागरिक", gen_pdf: bool = True):
    if custom_text:
        story = custom_text
        details = ""
        language = lang
        name = caller_name
        title = "Custom Text Incident"
    else:
        key = scenario_key if scenario_key in PRESET_SCENARIOS else "otp"
        scen = PRESET_SCENARIOS[key]
        story = scen["story"]
        details = scen["details"]
        language = scen["lang"]
        name = scen["caller"]
        title = scen["title"]

    print("\n" + "=" * 70)
    print(f"  RAKSHAK AI — LOCAL LLM INCIDENT ANALYSIS")
    print(f"  Scenario: {title}")
    print("=" * 70)
    print(f"Victim Name       : {name}")
    print(f"Language          : {language}")
    print(f"Statement         : {story}")
    if details:
        print(f"Follow-up Details : {details}")
    print("\n[AI Analyzing statement...]")

    analysis: CybercrimeIncidentAnalysis = analyze_incident_with_llm(
        story=story,
        details=details,
        language=language,
        caller_name=name,
    )

    print("\n" + "─" * 70)
    print("  STRUCTURED JSON EXTRACTION")
    print("─" * 70)
    print(json.dumps(analysis.model_dump(), indent=2, ensure_ascii=False))

    print("\n" + "─" * 70)
    print("  CONTEXT-AWARE FOLLOW-UP QUESTION")
    print("─" * 70)
    print(f"AI Prompt to Victim: {analysis.follow_up_question}")

    print("\n" + "─" * 70)
    print("  OFFICIAL COMPLAINT DRAFT (CYBERCRIME.GOV.IN)")
    print("─" * 70)
    print(analysis.formal_complaint_draft)

    if gen_pdf:
        print("\n" + "─" * 70)
        print("  GENERATING OFFICIAL PDF INCIDENT REPORT")
        print("─" * 70)
        data = {
            "name": name,
            "language": language,
            "scenario": analysis.fraud_category,
            "story": story,
            "follow_up_question": analysis.follow_up_question,
            "details": details,
            "financial_loss": analysis.financial_loss,
            "incident_date": analysis.incident_date,
            "incident_time": analysis.incident_time,
            "bank_details": analysis.bank_details.model_dump() if analysis.bank_details else {},
            "suspect_details": analysis.suspect_details.model_dump() if analysis.suspect_details else {},
            "missing_information": analysis.missing_information,
            "formal_complaint_draft": analysis.formal_complaint_draft,
            "llm_analysis": analysis.model_dump(),
        }
        pdf_path = generate_pdf_report(data)
        print(f"  [SUCCESS] PDF generated at: {pdf_path}")

    print("=" * 70 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Rakshak AI's LLM Intelligence Layer without Twilio.")
    parser.add_argument("--scenario", choices=list(PRESET_SCENARIOS.keys()), help="Choose preset scenario (otp, job, olx, loan)")
    parser.add_argument("--text", help="Custom incident text to test")
    parser.add_argument("--lang", default="hi", choices=["hi", "en"], help="Preferred language (hi/en)")
    parser.add_argument("--name", default="नागरिक", help="Caller name")
    parser.add_argument("--no-pdf", action="store_true", help="Skip PDF generation")

    args = parser.parse_args()

    if not args.scenario and not args.text:
        print("\nSelect a preset scenario or test custom text:")
        print("  1. Hindi — Banking KYC / OTP Fraud")
        print("  2. Hinglish — Telegram Task Job Scam")
        print("  3. English — OLX QR Code Scam")
        print("  4. Hindi — Instant Loan App Blackmail")
        choice = input("Enter choice (1-4) or press Enter for default [1]: ").strip() or "1"
        key_map = {"1": "otp", "2": "job", "3": "olx", "4": "loan"}
        chosen_key = key_map.get(choice, "otp")
        run_test(scenario_key=chosen_key, gen_pdf=not args.no_pdf)
    else:
        run_test(
            scenario_key=args.scenario,
            custom_text=args.text,
            lang=args.lang,
            caller_name=args.name,
            gen_pdf=not args.no_pdf,
        )
