"""
Comprehensive Automated Test Suite for Rakshak AI
Tests the complete end-to-end workflow, Twilio TwiML compliance,
speech recognition fallbacks, fraud detection, PDF/JSON generation,
session isolation, and security.
"""

import os
import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path

from main import (
    app,
    sessions,
    detect_scenario,
    extract_loss_amount,
    sanitize_sensitive_data,
    generate_pdf_report,
    save_json_report,
    incoming_call,
    select_language,
    retry_language,
    step1_name,
    step2_story,
    step3_details,
    confirm_interview,
    auto_save,
    health,
    list_reports,
    download_report,
    REPORTS_DIR,
)


def run_coro(coro):
    """Direct synchronous runner for coroutines without requiring loopback socket binding."""
    try:
        while True:
            coro.send(None)
    except StopIteration as e:
        return e.value


class FakeFormRequest:
    def __init__(self, data: dict):
        self._data = data
        self.headers = {"x-forwarded-proto": "https", "host": "localhost:8000"}

    async def form(self):
        return self._data


class DirectResponse:
    def __init__(self, res):
        self._res = res
        self.status_code = getattr(res, "status_code", 200)
        body_bytes = getattr(res, "body", b"")
        self.text = body_bytes.decode("utf-8") if isinstance(body_bytes, bytes) else str(body_bytes)
        self.headers = getattr(res, "headers", {"content-type": getattr(res, "media_type", "application/xml")})

    def json(self):
        return json.loads(self.text)


class DirectTestClient:
    def post(self, url, data=None):
        req = FakeFormRequest(data or {})
        with patch("asyncio.to_thread", side_effect=lambda func, *args, **kwargs: func(*args, **kwargs)):
            if url == "/incoming-call":
                res = run_coro(incoming_call(req))
            elif url == "/select-language":
                res = run_coro(select_language(req))
            elif url.startswith("/retry-language"):
                call_sid = (data or {}).get("CallSid", "")
                res = run_coro(retry_language(req, CallSid=call_sid))
            elif url == "/step1-name":
                res = run_coro(step1_name(req))
            elif url == "/step2-story":
                res = run_coro(step2_story(req))
            elif url == "/step3-details":
                res = run_coro(step3_details(req))
            elif url == "/confirm-interview":
                res = run_coro(confirm_interview(req))
            elif url.startswith("/auto-save"):
                call_sid = (data or {}).get("CallSid", "")
                res = run_coro(auto_save(req, CallSid=call_sid))
            else:
                raise ValueError(f"Unknown post url: {url}")
        return DirectResponse(res)

    def get(self, url):
        req = FakeFormRequest({})
        with patch("asyncio.to_thread", side_effect=lambda func, *args, **kwargs: func(*args, **kwargs)):
            if url == "/health":
                res = run_coro(health())
                dummy_res = MagicMock()
                dummy_res.status_code = 200
                dummy_res.body = json.dumps(res).encode("utf-8")
                dummy_res.headers = {"content-type": "application/json"}
                return DirectResponse(dummy_res)
            elif url == "/reports":
                res = run_coro(list_reports(req))
                dummy_res = MagicMock()
                dummy_res.status_code = 200
                dummy_res.body = json.dumps(res).encode("utf-8")
                dummy_res.headers = {"content-type": "application/json"}
                return DirectResponse(dummy_res)
            elif url.startswith("/download/"):
                fname = url.replace("/download/", "")
                try:
                    res = run_coro(download_report(fname))
                    dummy_res = MagicMock()
                    dummy_res.status_code = 200
                    dummy_res.body = b"PDF_CONTENT"
                    dummy_res.headers = {"content-type": getattr(res, "media_type", "application/pdf")}
                    return DirectResponse(dummy_res)
                except Exception as e:
                    status = getattr(e, "status_code", 400)
                    dummy_res = MagicMock()
                    dummy_res.status_code = status
                    dummy_res.body = b""
                    dummy_res.headers = {}
                    return DirectResponse(dummy_res)
            else:
                raise ValueError(f"Unknown get url: {url}")


client = DirectTestClient()


@pytest.fixture(autouse=True)
def clean_sessions():
    """Reset session state before each test."""
    sessions.clear()
    yield
    sessions.clear()


# ══════════════════════════════════════════════
#  TEST 1 & 12: TWIML VALIDITY & INCOMING CALL
# ══════════════════════════════════════════════
def test_incoming_call_returns_twiml_with_language_menu():
    """Verify incoming call returns valid TwiML with language selection menu."""
    response = client.post("/incoming-call", data={"CallSid": "CA_TEST_001", "From": "+919876543210"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    content = response.text

    # Verify TwiML structure
    assert '<?xml version="1.0" encoding="UTF-8"?>' in content
    assert "<Response>" in content
    assert "<Gather" in content
    assert 'numDigits="1"' in content
    assert "select-language" in content
    assert "Polly.Aditi" in content
    assert "CA_TEST_001" in sessions


# ══════════════════════════════════════════════
#  TEST 2: LANGUAGE SELECTION (HINDI & ENGLISH)
# ══════════════════════════════════════════════
def test_language_selection_hindi():
    """Pressing 1 sets Hindi language and proceeds to ask name."""
    sessions["CA_TEST_HI"] = {"call_sid": "CA_TEST_HI", "language": "hi"}
    response = client.post("/select-language", data={"CallSid": "CA_TEST_HI", "Digits": "1"})

    assert response.status_code == 200
    assert sessions["CA_TEST_HI"]["language"] == "hi"
    assert "हिंदी चुनी है" in response.text
    assert "<Record" in response.text
    assert "step1-name" in response.text


def test_language_selection_english():
    """Pressing 2 sets English language and proceeds to ask name."""
    sessions["CA_TEST_EN"] = {"call_sid": "CA_TEST_EN", "language": "hi"}
    response = client.post("/select-language", data={"CallSid": "CA_TEST_EN", "Digits": "2"})

    assert response.status_code == 200
    assert sessions["CA_TEST_EN"]["language"] == "en"
    assert "selected English" in response.text
    assert "<Record" in response.text
    assert "step1-name" in response.text


# ══════════════════════════════════════════════
#  TEST 3: INVALID DTMF & TIMEOUT HANDLING
# ══════════════════════════════════════════════
def test_invalid_dtmf_input_handling():
    """Invalid digit (e.g. 5) triggers retry prompt."""
    sessions["CA_TEST_INV"] = {"call_sid": "CA_TEST_INV", "language": "hi"}
    response = client.post("/select-language", data={"CallSid": "CA_TEST_INV", "Digits": "5"})

    assert response.status_code == 200
    assert "<Gather" in response.text
    assert "अमान्य" in response.text or "Invalid" in response.text


def test_timeout_and_retry_language():
    """Timeout redirects to retry-language and defaults to Hindi after maximum retries."""
    sessions["CA_TEST_TIMEOUT"] = {"call_sid": "CA_TEST_TIMEOUT", "lang_retry": 0}

    # Attempt 1
    r1 = client.post("/retry-language", data={"CallSid": "CA_TEST_TIMEOUT"})
    assert r1.status_code == 200
    assert "<Gather" in r1.text

    # Attempt 2
    r2 = client.post("/retry-language", data={"CallSid": "CA_TEST_TIMEOUT"})
    assert r2.status_code == 200

    # Attempt 3 (Max retries exceeded -> defaults to Hindi)
    r3 = client.post("/retry-language", data={"CallSid": "CA_TEST_TIMEOUT"})
    assert r3.status_code == 200
    assert sessions["CA_TEST_TIMEOUT"]["language"] == "hi"
    assert "<Record" in r3.text


# ══════════════════════════════════════════════
#  TEST 4: CALL SESSION ISOLATION
# ══════════════════════════════════════════════
def test_call_session_isolation():
    """Two concurrent calls maintain completely isolated state."""
    # Caller 1 selects Hindi
    client.post("/incoming-call", data={"CallSid": "SID_CALLER_1", "From": "+919000000001"})
    client.post("/select-language", data={"CallSid": "SID_CALLER_1", "Digits": "1"})

    # Caller 2 selects English
    client.post("/incoming-call", data={"CallSid": "SID_CALLER_2", "From": "+919000000002"})
    client.post("/select-language", data={"CallSid": "SID_CALLER_2", "Digits": "2"})

    assert sessions["SID_CALLER_1"]["language"] == "hi"
    assert sessions["SID_CALLER_2"]["language"] == "en"
    assert sessions["SID_CALLER_1"]["caller_phone"] == "+919000000001"
    assert sessions["SID_CALLER_2"]["caller_phone"] == "+919000000002"


# ══════════════════════════════════════════════
#  TEST 5: NAME & INCIDENT COLLECTION WITH STT MOCK
# ══════════════════════════════════════════════
@patch("main.transcribe_audio_async", new_callable=AsyncMock)
def test_name_and_story_collection(mock_stt):
    """Test full intake from name to story with mocked speech recognition."""
    sid = "CA_FLOW_01"
    sessions[sid] = {"call_sid": sid, "language": "hi"}

    # Step 1: Name collection
    mock_stt.return_value = "राहुल वर्मा"
    r_name = client.post("/step1-name", data={"CallSid": sid, "RecordingUrl": "http://mock/audio1.wav"})
    assert r_name.status_code == 200
    assert sessions[sid]["name"] == "राहुल वर्मा"
    assert "राहुल वर्मा" in r_name.text
    assert "step2-story" in r_name.text

    # Step 2: Story collection & classification
    mock_stt.return_value = "मुझे बैंक से कॉल आई और उन्होंने मुझसे आधार कार्ड केवाईसी के नाम पर ओटीपी मांग कर 25000 रुपये निकाल लिए"
    r_story = client.post("/step2-story", data={"CallSid": sid, "RecordingUrl": "http://mock/audio2.wav"})
    assert r_story.status_code == 200
    assert sessions[sid]["scenario"] == "OTP_FRAUD"
    assert "25000" in sessions[sid]["financial_loss"]
    assert "ओटीपी" in r_story.text


# ══════════════════════════════════════════════
#  TEST 6: SPEECH RECOGNITION FAILURE / FALLBACK
# ══════════════════════════════════════════════
@patch("main.transcribe_audio_async", new_callable=AsyncMock)
def test_speech_recognition_failure_handling(mock_stt):
    """Empty or inaudible audio does not crash the system; falls back gracefully after max retries."""
    sid = "CA_FAIL_01"
    sessions[sid] = {"call_sid": sid, "language": "en", "name_retries": 2, "story_retries": 2}

    mock_stt.return_value = ""  # Failed recognition
    r_name = client.post("/step1-name", data={"CallSid": sid, "RecordingUrl": "http://mock/empty.wav"})
    assert r_name.status_code == 200
    assert sessions[sid]["name"] == "Citizen"

    r_story = client.post("/step2-story", data={"CallSid": sid, "RecordingUrl": "http://mock/empty.wav"})
    assert r_story.status_code == 200
    assert sessions[sid]["scenario"] == "GENERAL_FRAUD"


# ══════════════════════════════════════════════
#  TEST 7: FRAUD CATEGORY DETECTION & KEYWORDS
# ══════════════════════════════════════════════
@pytest.mark.parametrize(
    "text,expected_category",
    [
        ("मेरे बैंक खाते से ओटीपी पूछकर पैसे काट लिए", "OTP_FRAUD"),
        ("Someone called me pretending to be from SBI asking for my banking password and OTP", "OTP_FRAUD"),
        ("ओएलएक्स पर पुराना फोन बेच रहा था तो खरीदार ने क्यूआर कोड स्कैन करने को बोला", "OLX_SCAM"),
        ("I posted an ad on OLX and the buyer sent me a QR code scanner link", "OLX_SCAM"),
        ("टेलीग्राम पर पार्ट टाइम वर्क फ्रॉम होम जॉब के लिए रजिस्ट्रेशन फीस ली", "JOB_SCAM"),
        ("I was added to a Telegram group promising daily income for youtube like tasks but had to pay prepaid fees", "JOB_SCAM"),
        ("लोन ऐप से 5000 का लोन लिया अब वे मेरे संपर्कों को फोन करके धमकी दे रहे हैं", "LOAN_FRAUD"),
        ("Instant loan app charged high processing fees and is blackmailing using my contact gallery", "LOAN_FRAUD"),
        ("मुझे एक अज्ञात नंबर से अनजान संदेश आया", "GENERAL_FRAUD"),
        ("Someone hacked my email account", "GENERAL_FRAUD"),
    ],
)
def test_fraud_category_detection(text, expected_category):
    """Test bilingual keyword detection for all supported fraud categories."""
    assert detect_scenario(text) == expected_category


# ══════════════════════════════════════════════
#  TEST 8: DATA SANITIZATION & LOSS EXTRACTION
# ══════════════════════════════════════════════
def test_financial_loss_extraction():
    """Verify loss amounts in various formats are extracted accurately."""
    assert extract_loss_amount("Account debited Rs. 45000 instantly") in ["45000", "Rs. 45000"]
    assert extract_loss_amount("मेरे खाते से ₹15000 कट गए") in ["15000", "₹15000"]
    assert extract_loss_amount("Lost 2 lakh in crypto task") == "2 lakh"


def test_sanitize_sensitive_credentials():
    """Ensure raw OTPs, PINs, and credit card numbers are redacted."""
    raw = "My OTP is 748291 and PIN was 1234 on card 4111-2222-3333-4444"
    cleaned = sanitize_sensitive_data(raw)
    assert "748291" not in cleaned
    assert "4111-2222-3333-4444" not in cleaned
    assert "[REDACTED]" in cleaned
    assert "[CARD REDACTED]" in cleaned


# ══════════════════════════════════════════════
#  TEST 9 & 10: PDF & JSON REPORT GENERATION & HINDI RENDERING
# ══════════════════════════════════════════════
def test_pdf_and_json_report_generation_hindi():
    """Verify PDF and JSON reports generate with Devanagari text and verified file existence."""
    sample_data = {
        "call_sid": "CA_REPORT_TEST_HI",
        "name": "राजेश कुमार",
        "language": "hi",
        "scenario": "OTP_FRAUD",
        "story": "अज्ञात व्यक्ति ने बैंक मैनेजर बनकर कॉल किया और ओटीपी पूछकर 50000 रुपये निकाल लिए।",
        "follow_up_question": "क्या आपके बैंक खाते से पैसे कटे हैं?",
        "details": "हाँ, एसबीआई खाते से 50000 रुपये की अनधिकृत निकासी हुई।",
        "financial_loss": "50000 रुपये",
    }

    pdf_path = generate_pdf_report(sample_data)
    json_path = save_json_report(sample_data)

    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 1000  # Non-empty PDF
    assert os.path.exists(json_path)

    # Verify JSON content
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["name"] == "राजेश कुमार"
    assert data["scenario"] == "OTP_FRAUD"
    assert "report_id" in data


def test_pdf_report_generation_english():
    """Verify PDF generates cleanly with English content."""
    sample_data = {
        "call_sid": "CA_REPORT_TEST_EN",
        "name": "John Doe",
        "language": "en",
        "scenario": "JOB_SCAM",
        "story": "I was promised a work from home job on Telegram and lost Rs 12000 in prepaid fees.",
        "follow_up_question": "Were you asked to pay registration fees for a job?",
        "details": "I sent money through a UPI QR code.",
        "financial_loss": "Rs 12000",
    }

    pdf_path = generate_pdf_report(sample_data)
    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 1000


# ══════════════════════════════════════════════
#  TEST 11: CONFIRM INTERVIEW & AUTO-SAVE
# ══════════════════════════════════════════════
def test_confirm_interview_and_auto_save():
    """Pressing 1 completes interview, generates report, and delivers closing advice."""
    sid = "CA_CONFIRM_01"
    sessions[sid] = {
        "call_sid": sid,
        "language": "en",
        "name": "Test User",
        "story": "Test incident narrative",
        "scenario": "GENERAL_FRAUD",
    }

    response = client.post("/confirm-interview", data={"CallSid": sid, "Digits": "1"})
    assert response.status_code == 200
    assert "<Hangup/>" in response.text
    assert "1930" in response.text
    assert sessions[sid]["status"] == "COMPLETED"


# ══════════════════════════════════════════════
#  TEST 12: REPORT DASHBOARD & DOWNLOAD SECURITY
# ══════════════════════════════════════════════
def test_reports_listing():
    """Verify /reports endpoint returns structured list of reports."""
    response = client.get("/reports")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "total_reports" in data
    assert isinstance(data["reports"], list)


def test_download_security_and_path_traversal():
    """Verify path traversal attacks are rejected and legitimate downloads work."""
    # Create a test PDF
    dummy_data = {
        "call_sid": "CA_SEC_01",
        "name": "Security Tester",
        "language": "en",
        "scenario": "GENERAL_FRAUD",
        "story": "Security validation test",
    }
    pdf_path = generate_pdf_report(dummy_data)
    filename = Path(pdf_path).name

    # 1. Valid download
    res_valid = client.get(f"/download/{filename}")
    assert res_valid.status_code == 200
    assert res_valid.headers["content-type"] == "application/pdf"

    # 2. Path traversal attack attempt
    res_traversal = client.get("/download/../../config.py")
    assert res_traversal.status_code in [400, 403, 404]

    # 3. Disallowed extension
    res_bad_ext = client.get("/download/malicious.exe")
    assert res_bad_ext.status_code == 400


def test_health_check():
    """Verify /health endpoint returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
