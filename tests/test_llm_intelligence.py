"""
Unit and Integration Tests for Rakshak AI's LLM Intelligence Layer
Tests structured extraction, anti-hallucination, missing info detection,
context-aware follow-up questions, and complaint drafting with mocked LLM calls.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from main import app, api_analyze_incident
from llm_analyzer import (
    analyze_incident_with_llm,
    fallback_deterministic_analysis,
    CybercrimeIncidentAnalysis,
    SuspectDetails,
)


def run_coro(coro):
    """Direct synchronous runner for coroutines without requiring loopback socket binding."""
    try:
        while True:
            coro.send(None)
    except StopIteration as e:
        return e.value


class FakeRequest:
    def __init__(self, json_data):
        self._json = json_data
        self.headers = {"host": "localhost:8000"}
        self.query_params = {}

    async def json(self):
        return self._json


# ══════════════════════════════════════════════
#  TEST 1: DETERMINISTIC OFFLINE ANALYSIS SCHEMA
# ══════════════════════════════════════════════
def test_deterministic_analysis_fields_and_schema():
    """Verify that offline deterministic analysis returns fully populated Pydantic schema."""
    story = "Someone called from 9876543210 claiming to be SBI manager and asked for OTP. Rs 35000 debited via UPI."
    res = fallback_deterministic_analysis(story, language="en", caller_name="Rajesh")

    assert isinstance(res, CybercrimeIncidentAnalysis)
    assert res.fraud_category == "OTP_FRAUD"
    assert "9876543210" in res.suspect_details.phone_numbers
    assert res.payment_method == "UPI"
    assert res.victim_name == "Rajesh"
    assert res.follow_up_question is not None
    assert len(res.formal_complaint_draft) > 50
    assert "Subject:" in res.formal_complaint_draft


# ══════════════════════════════════════════════
#  TEST 2: MISSING INFORMATION DETECTION
# ══════════════════════════════════════════════
def test_missing_information_detection():
    """Verify missing critical details (like UTR or amount) are flagged."""
    incomplete_story = "Someone cheated me online on Telegram."
    res = fallback_deterministic_analysis(incomplete_story, language="en")

    assert len(res.missing_information) > 0
    assert any("amount" in item.lower() or "financial loss" in item.lower() for item in res.missing_information)
    assert any("utr" in item.lower() or "reference" in item.lower() for item in res.missing_information)


# ══════════════════════════════════════════════
#  TEST 3: CONTEXT-AWARE FOLLOW-UP QUESTIONS
# ══════════════════════════════════════════════
def test_context_aware_followup_question_hindi():
    """Verify Hindi questions target missing data including date/time and suspect details."""
    story_no_loss = "ओएलएक्स पर खरीदार ने एक क्यूआर कोड भेजा।"
    res = fallback_deterministic_analysis(story_no_loss, language="hi")

    assert "नुकसान" in res.follow_up_question or "रुपये" in res.follow_up_question or "तारीख" in res.follow_up_question


def test_context_aware_followup_question_english():
    """Verify English questions target missing data including date/time and suspect details."""
    story = "I lost Rs 5000 in a fake loan app."
    res = fallback_deterministic_analysis(story, language="en")

    assert "?" in res.follow_up_question
    assert "details" in res.follow_up_question.lower() or "phone" in res.follow_up_question.lower() or "fraudster" in res.follow_up_question.lower() or "contact" in res.follow_up_question.lower()


# ══════════════════════════════════════════════
#  TEST 3B: TARGETED FOLLOW-UP FOR BANKING & CRIMINAL DETAILS
# ══════════════════════════════════════════════
def test_bank_fraud_followup_question_hindi():
    """Verify Hindi follow-up for bank fraud asks single targeted question based on category priority."""
    story = "मेरे बैंक खाते से पैसे कट गए हैं।"
    res = fallback_deterministic_analysis(story, language="hi")

    q = res.follow_up_question
    # Asks for highest priority missing field (financial loss)
    assert "नुकसान" in q or "रुपये" in q
    # When loss is provided, asks for bank name
    res2 = fallback_deterministic_analysis(story + " 25000 रुपये का नुकसान हुआ", language="hi")
    assert "बैंक का नाम" in res2.follow_up_question


def test_bank_fraud_followup_question_english():
    """Verify English follow-up for bank fraud asks single targeted question based on category priority."""
    story = "Money was debited from my bank account."
    res = fallback_deterministic_analysis(story, language="en")

    q = res.follow_up_question.lower()
    assert "financial loss" in q or "amount" in q
    # When loss is provided, asks for bank name
    res2 = fallback_deterministic_analysis(story + " lost 25000 rupees", language="en")
    assert "bank" in res2.follow_up_question.lower()


def test_bank_and_criminal_details_extraction():
    """Verify extraction of date/time, bank info, and criminal particulars (name, phone, UPI, email)."""
    story = "Someone stole money from my bank account."
    details = "It happened yesterday at 11 AM. My bank is HDFC Bank, branch Connaught Place, account number 123456789012. The scammer was named Rahul Sharma, phone 9876543210, upi scammer@okhdfcbank, email fraud@scammail.com, loss Rs 25000."
    res = fallback_deterministic_analysis(story, details=details, language="en", caller_name="Amit Verma")

    assert res.incident_date == "yesterday"
    assert res.incident_time == "11 AM"
    assert "HDFC" in res.bank_details.bank_name
    assert res.bank_details.bank_branch == "Connaught Place"
    assert res.bank_details.account_number == "123456789012"
    assert "Rahul Sharma" in res.suspect_details.names
    assert "9876543210" in res.suspect_details.phone_numbers
    assert "scammer@okhdfcbank" in res.suspect_details.upi_ids
    assert "fraud@scammail.com" in res.suspect_details.emails
    assert "25000" in res.financial_loss


# ══════════════════════════════════════════════
#  TEST 4: ANTI-HALLUCINATION / NO INVENTED FACTS
# ══════════════════════════════════════════════
def test_anti_hallucination_guarantee():
    """Verify that absent details remain None/empty and are NOT invented."""
    story = "My WhatsApp was hacked."
    res = fallback_deterministic_analysis(story, language="en", caller_name=None)

    assert res.victim_name is None
    assert res.incident_date is None
    assert res.financial_loss is None
    assert res.transaction_reference is None
    assert len(res.suspect_details.phone_numbers) == 0
    assert len(res.suspect_details.upi_ids) == 0


# ══════════════════════════════════════════════
#  TEST 5: MOCKED GEMINI API CALL
# ══════════════════════════════════════════════
@patch("llm_analyzer._call_gemini_api")
def test_mocked_gemini_llm_invocation(mock_gemini):
    """Verify that when GEMINI_API_KEY is configured, Gemini is invoked and parsed."""
    mock_payload = {
        "incident_summary": "Victim was tricked into sharing an OTP for electricity bill update, leading to Rs 10000 unauthorized debit.",
        "fraud_category": "OTP_FRAUD",
        "fraud_category_label": "Banking / OTP Fraud",
        "victim_name": "Suresh",
        "incident_date": "2026-10-18",
        "financial_loss": "Rs 10,000",
        "transaction_reference": "UTR992837192",
        "payment_method": "Net Banking",
        "suspect_details": {
            "phone_numbers": ["9876543210"],
            "upi_ids": [],
            "bank_accounts": [],
            "telegram_handles": [],
            "websites_or_apps": [],
            "impersonated_entities": ["Electricity Department"]
        },
        "missing_information": ["Beneficiary bank account number"],
        "follow_up_question": "Did the suspect ask you to download any screen-sharing app like AnyDesk or RustDesk?",
        "formal_complaint_draft": "Subject: Formal Incident Report regarding Rs 10,000 Electricity Bill Fraud.\nSir, I Suresh was defrauded...",
        "language_detected": "en"
    }
    mock_gemini.return_value = mock_payload

    with patch("llm_analyzer.GEMINI_API_KEY", "mock-gemini-key"):
        result = analyze_incident_with_llm(
            story="I was cheated for Rs 10000 by a caller pretending to be from electricity department",
            language="en",
            caller_name="Suresh",
        )

    assert result.fraud_category == "OTP_FRAUD"
    assert result.financial_loss == "Rs 10,000"
    assert result.transaction_reference == "UTR992837192"
    assert "9876543210" in result.suspect_details.phone_numbers
    assert mock_gemini.called


# ══════════════════════════════════════════════
#  TEST 6: API ERROR FALLBACK RESILIENCE
# ══════════════════════════════════════════════
@patch("llm_analyzer._call_gemini_api", side_effect=Exception("API Quota Exceeded"))
def test_llm_api_error_fallback_resilience(mock_gemini):
    """Verify that if external LLM API throws an error, system seamlessly falls back without crashing."""
    with patch("llm_analyzer.GEMINI_API_KEY", "mock-failing-key"):
        result = analyze_incident_with_llm(
            story="Someone on OLX asked me to scan QR code and took 20000 rupees",
            language="en",
            caller_name="Test User",
        )

    assert isinstance(result, CybercrimeIncidentAnalysis)
    assert result.fraud_category == "OLX_SCAM"
    assert result.follow_up_question is not None


# ══════════════════════════════════════════════
#  TEST 7: LOCAL TEST ENDPOINT /api/analyze-incident
# ══════════════════════════════════════════════
def test_api_analyze_incident_endpoint():
    """Verify /api/analyze-incident allows testing via HTTP JSON."""
    payload = {
        "text": "मेरे खाते से अज्ञात व्यक्ति ने 50000 रुपये निकाल लिए जब मैंने टेलीग्राम पर टास्क किया था।",
        "language": "hi",
        "caller_name": "अमित",
        "generate_pdf": False,
    }
    req = FakeRequest(payload)
    with patch("asyncio.to_thread", side_effect=lambda func, *args, **kwargs: func(*args, **kwargs)):
        res = run_coro(api_analyze_incident(req))
    data = res if isinstance(res, dict) else json.loads(res.body.decode("utf-8"))

    assert data["status"] == "success"
    analysis = data["analysis"]
    assert analysis["fraud_category"] == "JOB_SCAM"
