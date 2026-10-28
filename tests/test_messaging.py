"""
Unit and Integration Tests for Rakshak AI — SMS & WhatsApp Integration
Validates secure tokenized report access, phone normalization, Twilio trial handling,
bilingual notification templates, and IVR delivery selection workflow.
Uses DirectTestClient for fast, sandbox-safe execution without loopback socket binding.
"""

import os
import json
import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from main import (
    app,
    sessions,
    generate_pdf_report,
    confirm_interview,
    select_delivery,
    access_report_by_token,
    auto_save,
)
from messaging_service import (
    create_report_access_token,
    verify_report_token,
    get_token_metadata,
    revoke_report_token,
    build_secure_report_url,
    normalize_phone_number,
    is_valid_e164,
    get_sms_text,
    get_whatsapp_text,
    send_report_sms,
    send_report_whatsapp,
    is_delivery_already_dispatched,
    record_delivery_dispatch,
    REPORTS_DIR,
)


# ══════════════════════════════════════════════
#  FAST SANDBOX-SAFE DIRECT TEST RUNNER
# ══════════════════════════════════════════════

def run_coro(coro):
    """Direct synchronous runner for coroutines without requiring loopback socket binding."""
    try:
        while True:
            coro.send(None)
    except StopIteration as e:
        return e.value


class FakeRequest:
    def __init__(self, data: dict = None, query_params: dict = None):
        self._data = data or {}
        self.query_params = query_params or {}
        self.headers = {
            "x-forwarded-proto": "https",
            "host": "localhost:8000",
            "accept": "application/pdf",
        }

    async def form(self):
        return self._data


class DirectResponse:
    def __init__(self, res, status_code=200, headers=None, body=b""):
        self.status_code = getattr(res, "status_code", status_code)
        body_bytes = getattr(res, "body", body)
        self.text = body_bytes.decode("utf-8", errors="replace") if isinstance(body_bytes, bytes) else str(body_bytes)
        default_headers = {"content-type": getattr(res, "media_type", "application/xml")}
        self.headers = getattr(res, "headers", headers or default_headers)

    def json(self):
        return json.loads(self.text)


class DirectTestClient:
    def post(self, url, data=None):
        req = FakeRequest(data or {})
        with patch("asyncio.to_thread", side_effect=lambda func, *args, **kwargs: func(*args, **kwargs)):
            if url == "/confirm-interview":
                res = run_coro(confirm_interview(req))
            elif url == "/select-delivery":
                res = run_coro(select_delivery(req))
            elif url.startswith("/auto-save"):
                call_sid = (data or {}).get("CallSid", "")
                res = run_coro(auto_save(req, CallSid=call_sid))
            else:
                raise ValueError(f"Unknown test POST url: {url}")
        return DirectResponse(res)

    def get(self, url):
        req = FakeRequest({})
        with patch("asyncio.to_thread", side_effect=lambda func, *args, **kwargs: func(*args, **kwargs)):
            if url.startswith("/report/access/"):
                token_part = url.replace("/report/access/", "")
                token = token_part.split("?")[0]
                dl = 1 if "download=1" in url else 0
                try:
                    res = run_coro(access_report_by_token(token, req, download=dl))
                    headers = getattr(res, "headers", {})
                    headers["content-type"] = getattr(res, "media_type", "application/pdf")
                    return DirectResponse(res, status_code=200, headers=headers, body=b"%PDF-1.4 mock")
                except HTTPException as e:
                    body = json.dumps({"detail": e.detail}).encode("utf-8")
                    return DirectResponse(None, status_code=e.status_code, body=body)
            else:
                raise ValueError(f"Unknown test GET url: {url}")


client = DirectTestClient()


# ══════════════════════════════════════════════
#  1. SECURE TOKEN ENGINE TESTS
# ══════════════════════════════════════════════

def test_token_creation_and_verification():
    """Token generation produces a valid, cryptographically secure token that resolves to the report file."""
    test_pdf = REPORTS_DIR / "Rakshak_Report_TEST_SECURE.pdf"
    test_pdf.write_text("Dummy PDF content for testing", encoding="utf-8")

    try:
        report_id = "RAK-20261028-TEST01"
        token = create_report_access_token(report_id, test_pdf, expiry_hours=2)

        assert token and len(token) >= 32
        meta = get_token_metadata(token)
        assert meta["report_id"] == report_id
        assert meta["filename"] == test_pdf.name
        assert meta["access_count"] == 0

        # Verify token is valid
        is_valid, resolved_path, reason = verify_report_token(token)
        assert is_valid is True
        assert reason == "valid"
        assert resolved_path.resolve() == test_pdf.resolve()

        # Access counter incremented
        meta_updated = get_token_metadata(token)
        assert meta_updated["access_count"] == 1
        assert meta_updated["last_accessed_at"] is not None

        # Revoke token
        assert revoke_report_token(token) is True
        is_valid_after, _, reason_after = verify_report_token(token)
        assert is_valid_after is False
        assert reason_after == "not_found"
    finally:
        if test_pdf.exists():
            test_pdf.unlink()


def test_token_expiration():
    """Expired tokens are rejected with 'expired' reason."""
    test_pdf = REPORTS_DIR / "Rakshak_Report_EXPIRY.pdf"
    test_pdf.write_text("PDF content", encoding="utf-8")

    try:
        # Create token with -1 hour expiry (already expired)
        token = create_report_access_token("RAK-EXP-01", test_pdf, expiry_hours=-1)
        is_valid, path, reason = verify_report_token(token)

        assert is_valid is False
        assert path is None
        assert reason == "expired"
    finally:
        if test_pdf.exists():
            test_pdf.unlink()


def test_token_path_traversal_protection():
    """Tokens maliciously pointing outside REPORTS_DIR are blocked."""
    assert verify_report_token("../../secret.txt") == (False, None, "not_found")
    assert verify_report_token(None) == (False, None, "not_found")
    assert verify_report_token("") == (False, None, "not_found")


# ══════════════════════════════════════════════
#  2. HTTP TOKEN ACCESS ENDPOINT TESTS
# ══════════════════════════════════════════════

def test_http_report_access_endpoint():
    """GET /report/access/{token} returns valid PDF with secure headers."""
    dummy_pdf = REPORTS_DIR / "Rakshak_Report_HTTP_TEST.pdf"
    dummy_pdf.write_text("Sample PDF Content", encoding="utf-8")

    try:
        token = create_report_access_token("RAK-HTTP-01", dummy_pdf, expiry_hours=24)

        # 1. Valid inline access
        res = client.get(f"/report/access/{token}")
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert "inline" in res.headers["content-disposition"]
        assert res.headers["x-content-type-options"] == "nosniff"

        # 2. Download mode
        res_dl = client.get(f"/report/access/{token}?download=1")
        assert res_dl.status_code == 200
        assert "attachment" in res_dl.headers["content-disposition"]

        # 3. Invalid token returns 404
        res_invalid = client.get("/report/access/non_existent_token_xyz")
        assert res_invalid.status_code == 404

        # 4. Expired token returns 410 Gone
        expired_token = create_report_access_token("RAK-EXP-HTTP", dummy_pdf, expiry_hours=-2)
        res_exp = client.get(f"/report/access/{expired_token}")
        assert res_exp.status_code == 410
        assert "expired" in res_exp.json()["detail"].lower()
    finally:
        if dummy_pdf.exists():
            dummy_pdf.unlink()


# ══════════════════════════════════════════════
#  3. PHONE NORMALIZATION & VALIDATION TESTS
# ══════════════════════════════════════════════

def test_phone_number_normalization():
    """Validates normalization of various phone input formats to E.164."""
    assert normalize_phone_number("9528818624") == "+919528818624"
    assert normalize_phone_number("09528818624") == "+919528818624"
    assert normalize_phone_number("919528818624") == "+919528818624"
    assert normalize_phone_number("+919528818624") == "+919528818624"
    assert normalize_phone_number("+91 95288-18624") == "+919528818624"
    assert normalize_phone_number("+12492028238") == "+12492028238"
    assert normalize_phone_number("whatsapp:+919528818624") == "+919528818624"

    assert is_valid_e164("+919528818624") is True
    assert is_valid_e164("+12492028238") is True
    assert is_valid_e164("9528818624") is False

    with pytest.raises(ValueError):
        normalize_phone_number("invalid_number")
    with pytest.raises(ValueError):
        normalize_phone_number("123")
    with pytest.raises(ValueError):
        normalize_phone_number("")


# ══════════════════════════════════════════════
#  4. NOTIFICATION TEMPLATE TESTS
# ══════════════════════════════════════════════

def test_sms_and_whatsapp_templates():
    """Templates contain report ID, secure URL, bank advisory, and trial-friendly length."""
    rep_id = "RAK-20261028-X9Y8Z7"
    sec_url = "https://rakshak.example/report/access/token123"

    # SMS Hindi / Hinglish
    sms_hi = get_sms_text(rep_id, sec_url, language="hi")
    assert rep_id in sms_hi
    assert sec_url in sms_hi
    assert "Bank" in sms_hi

    # SMS English
    sms_en = get_sms_text(rep_id, sec_url, language="en")
    assert rep_id in sms_en
    assert sec_url in sms_en
    assert "bank" in sms_en.lower()

    # WhatsApp Hindi
    wa_hi = get_whatsapp_text(report_id=rep_id, secure_url=sec_url, language="hi")
    assert rep_id in wa_hi
    assert sec_url in wa_hi
    assert "एफआईआर" in wa_hi

    # WhatsApp English
    wa_en = get_whatsapp_text(report_id=rep_id, secure_url=sec_url, language="en")
    assert rep_id in wa_en
    assert sec_url in wa_en
    assert "FIR" in wa_en


# ══════════════════════════════════════════════
#  5. TWILIO CLIENT DISPATCH TESTS (MOCKED)
# ══════════════════════════════════════════════

def test_send_report_sms_success():
    """Mock Twilio success for outbound SMS."""
    mock_client = MagicMock()
    mock_msg = MagicMock()
    mock_msg.sid = "SM_MOCK_SUCCESS_123"
    mock_msg.status = "queued"
    mock_client.messages.create.return_value = mock_msg

    res = send_report_sms(
        to_phone="+919528818624",
        secure_url="https://rakshak.test/report/access/tok",
        report_id="RAK-TEST-01",
        language="en",
        client=mock_client,
        from_number="+12492028238",
    )

    assert res["success"] is True
    assert res["sid"] == "SM_MOCK_SUCCESS_123"
    assert res["channel"] == "sms"
    mock_client.messages.create.assert_called_once()


def test_send_report_sms_trial_restriction():
    """Twilio error 21608 (Trial unverified destination) is handled cleanly."""
    mock_client = MagicMock()
    error_21608 = Exception("The number is unverified")
    error_21608.code = 21608
    mock_client.messages.create.side_effect = error_21608

    res = send_report_sms(
        to_phone="+919999999999",
        secure_url="https://rakshak.test/report/access/tok",
        report_id="RAK-TEST-TRIAL",
        language="hi",
        client=mock_client,
        from_number="+12492028238",
    )

    assert res["success"] is False
    assert res["error_code"] == 21608
    assert "Twilio Trial Restriction" in res["error_message"]


def test_send_report_whatsapp_success():
    """Mock Twilio success for outbound WhatsApp message."""
    mock_client = MagicMock()
    mock_msg = MagicMock()
    mock_msg.sid = "WA_MOCK_SUCCESS_456"
    mock_msg.status = "queued"
    mock_client.messages.create.return_value = mock_msg

    res = send_report_whatsapp(
        to_phone="+919528818624",
        secure_url="https://rakshak.test/report/access/tok",
        report_id="RAK-TEST-WA",
        language="hi",
        client=mock_client,
        from_sender="whatsapp:+14155238886",
    )

    assert res["success"] is True
    assert res["sid"] == "WA_MOCK_SUCCESS_456"
    assert res["channel"] == "whatsapp"
    call_args = mock_client.messages.create.call_args[1]
    assert call_args["to"] == "whatsapp:+919528818624"
    assert call_args["from_"] == "whatsapp:+14155238886"


def test_send_report_whatsapp_sandbox_opt_in_required():
    """Twilio error 63007 (WhatsApp Sandbox not joined) is handled gracefully with clear guidance."""
    mock_client = MagicMock()
    error_63007 = Exception("Could not send WhatsApp message: Sandbox not joined")
    error_63007.code = 63007
    mock_client.messages.create.side_effect = error_63007

    res = send_report_whatsapp(
        to_phone="+919528818624",
        secure_url="https://rakshak.test/report/access/tok",
        report_id="RAK-TEST-OPTIN",
        language="en",
        client=mock_client,
        from_sender="whatsapp:+14155238886",
    )

    assert res["success"] is False
    assert res["error_code"] == 63007
    assert "WhatsApp Sandbox" in res["error_message"]


# ══════════════════════════════════════════════
#  6. IVR FLOW: /confirm-interview & /select-delivery
# ══════════════════════════════════════════════

def test_confirm_interview_offers_delivery_menu():
    """Step 6/7: /confirm-interview generates report and presents delivery menu (1 for SMS, 2 for WhatsApp, 3 for None)."""
    sid = "CA_DELIVERY_MENU_01"
    sessions[sid] = {
        "call_sid": sid,
        "language": "hi",
        "name": "सुरेश कुमार",
        "story": "बैंक खाते से धोखाधड़ी हुई।",
        "scenario": "OTP_FRAUD",
    }

    response = client.post("/confirm-interview", data={"CallSid": sid, "Digits": "1"})
    assert response.status_code == 200
    text = response.text

    assert "<Gather" in text
    assert 'action="/select-delivery"' in text
    assert "एसएमएस" in text
    assert "व्हाट्सएप" in text
    assert sessions[sid]["status"] == "COMPLETED"
    assert "report_token" in sessions[sid]
    assert "secure_download_url" in sessions[sid]


@patch("main.send_report_sms")
def test_select_delivery_option_1_sms(mock_sms):
    """Pressing 1 on delivery menu dispatches SMS and speaks confirmation."""
    mock_sms.return_value = {"success": True, "sid": "SM_TEST_001", "status": "queued"}

    sid = "CA_IVR_SMS_01"
    dummy_pdf = REPORTS_DIR / "dummy_report_sms.pdf"
    dummy_pdf.write_text("PDF content", encoding="utf-8")

    try:
        sessions[sid] = {
            "call_sid": sid,
            "language": "hi",
            "report_id": "RAK-IVR-SMS",
            "pdf_path": str(dummy_pdf),
            "caller_phone": "+919528818624",
        }

        response = client.post(
            "/select-delivery",
            data={"CallSid": sid, "Digits": "1", "From": "+919528818624"},
        )
        assert response.status_code == 200
        text = response.text

        assert "एसएमएस के माध्यम से" in text
        assert "बैंक" in text
        assert "1930" not in text
        assert "<Hangup/>" in text
        mock_sms.assert_called_once()
        assert is_delivery_already_dispatched(sid, "sms") is True
    finally:
        if dummy_pdf.exists():
            dummy_pdf.unlink()


@patch("main.send_report_whatsapp")
def test_select_delivery_option_2_whatsapp(mock_wa):
    """Pressing 2 on delivery menu dispatches WhatsApp and speaks confirmation."""
    mock_wa.return_value = {"success": True, "sid": "WA_TEST_002", "status": "queued"}

    sid = "CA_IVR_WA_01"
    dummy_pdf = REPORTS_DIR / "dummy_report_wa.pdf"
    dummy_pdf.write_text("PDF content", encoding="utf-8")

    try:
        sessions[sid] = {
            "call_sid": sid,
            "language": "en",
            "report_id": "RAK-IVR-WA",
            "pdf_path": str(dummy_pdf),
            "caller_phone": "+919528818624",
        }

        response = client.post(
            "/select-delivery",
            data={"CallSid": sid, "Digits": "2", "From": "+919528818624"},
        )
        assert response.status_code == 200
        text = response.text

        assert "WhatsApp" in text
        assert "bank" in text.lower()
        assert "1930" not in text
        assert "<Hangup/>" in text
        mock_wa.assert_called_once()
        assert is_delivery_already_dispatched(sid, "whatsapp") is True
    finally:
        if dummy_pdf.exists():
            dummy_pdf.unlink()


@patch("main.send_report_sms")
@patch("main.send_report_whatsapp")
def test_select_delivery_option_3_declined(mock_wa, mock_sms):
    """Pressing 3 declines report delivery; no SMS or WhatsApp is dispatched."""
    sid = "CA_IVR_DECLINE_01"
    sessions[sid] = {
        "call_sid": sid,
        "language": "hi",
        "report_id": "RAK-IVR-DECLINE",
    }

    response = client.post(
        "/select-delivery",
        data={"CallSid": sid, "Digits": "3"},
    )
    assert response.status_code == 200
    text = response.text

    assert "कोई लिंक नहीं भेजा जाएगा" in text
    assert "बैंक" in text
    assert "1930" not in text
    assert "<Hangup/>" in text
    mock_sms.assert_not_called()
    mock_wa.assert_not_called()


@patch("main.send_report_sms")
def test_select_delivery_idempotency(mock_sms):
    """Repeated or duplicate webhook hits do not send duplicate messages."""
    mock_sms.return_value = {"success": True, "sid": "SM_IDEMP_001", "status": "queued"}

    sid = "CA_IDEMP_CALL_01"
    dummy_pdf = REPORTS_DIR / "dummy_report_idemp.pdf"
    dummy_pdf.write_text("PDF content", encoding="utf-8")

    try:
        sessions[sid] = {
            "call_sid": sid,
            "language": "en",
            "report_id": "RAK-IDEMP",
            "pdf_path": str(dummy_pdf),
            "caller_phone": "+919528818624",
        }

        # First request sends SMS
        r1 = client.post("/select-delivery", data={"CallSid": sid, "Digits": "1"})
        assert r1.status_code == 200
        assert mock_sms.call_count == 1

        # Second request detects already dispatched
        r2 = client.post("/select-delivery", data={"CallSid": sid, "Digits": "1"})
        assert r2.status_code == 200
        assert "already been sent" in r2.text
        assert mock_sms.call_count == 1
    finally:
        if dummy_pdf.exists():
            dummy_pdf.unlink()
