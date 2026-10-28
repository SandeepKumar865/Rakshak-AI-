# ╔══════════════════════════════════════════════════════════════════════╗
# ║             RAKSHAK AI — SECURE MESSAGING & NOTIFICATION ENGINE       ║
# ║  Tokenized Report Delivery via SMS and WhatsApp (Twilio Supported)   ║
# ╚══════════════════════════════════════════════════════════════════════╝

import os
import re
import json
import logging
import secrets
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from config import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_PHONE_NUMBER,
    TWILIO_WHATSAPP_FROM,
    DEMO_TO_NUMBER,
    BASE_URL,
    REPORT_TOKEN_EXPIRY_HOURS,
    mask_phone,
    mask_secret,
)

logger = logging.getLogger("RakshakAI.Messaging")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

# Base storage paths
BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"
TOKENS_FILE = REPORTS_DIR / "access_tokens.json"

# Thread-safe synchronization locks
_tokens_lock = threading.Lock()
_dispatch_lock = threading.Lock()

# In-memory dispatch tracking to prevent duplicate webhook dispatches
# {call_sid: {"sms": {"sid": "...", "timestamp": "..."}, "whatsapp": {...}}}
_dispatched_deliveries: Dict[str, Dict[str, Any]] = {}


# ══════════════════════════════════════════════
#  1. SECURE TOKEN MANAGEMENT & PATH INTEGRITY
# ══════════════════════════════════════════════

def _load_tokens_unsafe() -> Dict[str, Dict[str, Any]]:
    """Loads token database from JSON without acquiring lock (internal use)."""
    if not TOKENS_FILE.exists():
        return {}
    try:
        with open(TOKENS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[TOKEN] Error reading tokens file: {e}")
        return {}


def _save_tokens_unsafe(tokens: Dict[str, Dict[str, Any]]) -> None:
    """Saves token database atomically without acquiring lock (internal use)."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = TOKENS_FILE.with_suffix(".tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(tokens, f, indent=2, ensure_ascii=False)
        temp_file.replace(TOKENS_FILE)
    except Exception as e:
        logger.error(f"[TOKEN] Error persisting tokens: {e}")
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass


def create_report_access_token(
    report_id: str,
    pdf_path: str | Path,
    expiry_hours: Optional[int] = None,
) -> str:
    """
    Generates a cryptographically secure, time-limited access token for a report.
    Persists token metadata thread-safely in access_tokens.json.
    """
    if expiry_hours is None:
        expiry_hours = REPORT_TOKEN_EXPIRY_HOURS

    token = secrets.token_urlsafe(32)
    filename = Path(pdf_path).name

    now_utc = datetime.now(timezone.utc)
    expires_at = now_utc + timedelta(hours=expiry_hours)

    record = {
        "token": token,
        "report_id": report_id,
        "filename": filename,
        "created_at": now_utc.isoformat(),
        "expires_at": expires_at.isoformat(),
        "access_count": 0,
        "last_accessed_at": None,
    }

    with _tokens_lock:
        tokens = _load_tokens_unsafe()
        tokens[token] = record
        _save_tokens_unsafe(tokens)

    logger.info(
        f"[TOKEN] Created token for report {report_id} (file: {filename}, "
        f"expires in {expiry_hours}h)"
    )
    return token


def verify_report_token(token: str) -> Tuple[bool, Optional[Path], str]:
    """
    Verifies that a report token is valid, unexpired, and maps safely within REPORTS_DIR.
    Returns:
        (is_valid: bool, file_path: Optional[Path], reason: str)
        where reason is one of 'valid', 'not_found', 'expired', 'file_missing', 'security_violation'.
    """
    if not token or not isinstance(token, str):
        return False, None, "not_found"

    with _tokens_lock:
        tokens = _load_tokens_unsafe()
        record = tokens.get(token)

        if not record:
            return False, None, "not_found"

        # Check expiration
        expires_at_str = record.get("expires_at")
        if expires_at_str:
            try:
                expires_at_dt = datetime.fromisoformat(expires_at_str)
                if datetime.now(timezone.utc) > expires_at_dt:
                    return False, None, "expired"
            except Exception:
                return False, None, "expired"

        filename = record.get("filename", "")
        if not filename or "/" in filename or "\\" in filename or ".." in filename:
            return False, None, "security_violation"

        # Path traversal guard
        safe_path = (REPORTS_DIR / filename).resolve()
        try:
            safe_path.relative_to(REPORTS_DIR.resolve())
        except ValueError:
            return False, None, "security_violation"

        if not safe_path.exists() or not safe_path.is_file():
            return False, None, "file_missing"

        # Record access count and last accessed time
        record["access_count"] = record.get("access_count", 0) + 1
        record["last_accessed_at"] = datetime.now(timezone.utc).isoformat()
        _save_tokens_unsafe(tokens)

        return True, safe_path, "valid"


def get_token_metadata(token: str) -> Optional[Dict[str, Any]]:
    """Retrieves metadata for a given token, without recording an access hit."""
    with _tokens_lock:
        tokens = _load_tokens_unsafe()
        return tokens.get(token)


def revoke_report_token(token: str) -> bool:
    """Manually revokes an active report access token."""
    with _tokens_lock:
        tokens = _load_tokens_unsafe()
        if token in tokens:
            del tokens[token]
            _save_tokens_unsafe(tokens)
            return True
        return False


def build_secure_report_url(token: str, base_url: Optional[str] = None) -> str:
    """Builds the full public access URL for a tokenized report link."""
    base = (base_url or BASE_URL or "").rstrip("/")
    return f"{base}/report/access/{token}"


# ══════════════════════════════════════════════
#  2. PHONE NUMBER NORMALIZATION & VALIDATION
# ══════════════════════════════════════════════

def normalize_phone_number(phone: str, default_country_code: str = "+91") -> str:
    """
    Normalizes a destination phone number to E.164 format.
    Handles Indian mobile formats (10 digits, leading 0, 91 prefix) and standard international numbers.
    Raises ValueError if number cannot be parsed to a valid phone format.
    """
    if not phone or not isinstance(phone, str):
        raise ValueError("Phone number must be a non-empty string")

    # Clean whatsapp: prefix and whitespace
    raw = phone.strip()
    if raw.lower().startswith("whatsapp:"):
        raw = raw[9:].strip()

    # Strip formatting characters: dashes, spaces, parentheses, dots
    cleaned = re.sub(r"[\s\-\(\)\.]", "", raw)

    if not cleaned:
        raise ValueError("Invalid phone number: empty after cleaning")

    # Case 1: Already has a leading '+'
    if cleaned.startswith("+"):
        digits_only = cleaned[1:]
        if digits_only.isdigit() and 7 <= len(digits_only) <= 15:
            return cleaned
        raise ValueError(f"Invalid E.164 phone number: {mask_phone(phone)}")

    # Case 2: Only digits
    if cleaned.isdigit():
        # 10 digits (Standard Indian mobile: e.g. 9528818624)
        if len(cleaned) == 10:
            return f"{default_country_code}{cleaned}"
        # 11 digits with leading 0 (e.g. 09528818624)
        if len(cleaned) == 11 and cleaned.startswith("0"):
            return f"{default_country_code}{cleaned[1:]}"
        # 12 digits starting with 91 (e.g. 919528818624)
        if len(cleaned) == 12 and cleaned.startswith("91"):
            return f"+{cleaned}"
        # Generic international without '+' but valid length
        if 11 <= len(cleaned) <= 15:
            return f"+{cleaned}"

    raise ValueError(f"Unable to normalize phone number to E.164: {mask_phone(phone)}")


def is_valid_e164(phone: str) -> bool:
    """Checks whether a string strictly matches E.164 regex (e.g. +919528818624)."""
    if not phone:
        return False
    return bool(re.match(r"^\+[1-9]\d{6,14}$", phone))


# ══════════════════════════════════════════════
#  3. NOTIFICATION MESSAGE TEMPLATES
# ══════════════════════════════════════════════

def get_sms_text(report_id: str, secure_url: str, language: str = "hi") -> str:
    """Generates concise, compliant SMS body with secure link and draft disclaimer."""
    if language == "hi":
        return (
            f"रक्षक एआई (Rakshak AI): आपकी साइबर शिकायत रिपोर्ट ({report_id}) तैयार है।\n"
            f"सुरक्षित लिंक (24 घंटे वैध): {secure_url}\n"
            f"यह एक मसौदा रिपोर्ट है। तत्काल 1930 राष्ट्रीय साइबर हेल्पलाइन पर कॉल करें "
            f"और बैंक को खाता/कार्ड फ्रीज करने हेतु सूचित करें।"
        )
    return (
        f"Rakshak AI: Your cyber incident report ({report_id}) is ready.\n"
        f"Secure Link (valid 24h): {secure_url}\n"
        f"This is an intake draft, not an official police complaint. "
        f"Call 1930 Cyber Helpline & notify your bank immediately."
    )


def get_whatsapp_text(report_id: str, secure_url: str, language: str = "hi") -> str:
    """Generates formatted WhatsApp body with clear headers, draft disclaimer, and helpline info."""
    if language == "hi":
        return (
            f"🛡️ *रक्षक एआई — साइबर अपराध रिपोर्ट मसौदा*\n\n"
            f"आपकी शिकायत का मसौदा तैयार कर लिया गया है।\n"
            f"• रिपोर्ट संदर्भ: *{report_id}*\n"
            f"• सुरक्षित डाउनलोड लिंक: {secure_url}\n\n"
            f"⚠️ *महत्वपूर्ण कानूनी सूचना:*\n"
            f"यह केवल एक सहायता रिपोर्ट (Draft) है, आधिकारिक एफआईआर (FIR) नहीं। "
            f"कानूनी शिकायत के लिए तुरंत *1930* राष्ट्रीय साइबर हेल्पलाइन पर कॉल करें "
            f"या www.cybercrime.gov.in पर दर्ज करें।\n\n"
            f"तत्काल अपने बैंक से संपर्क करके संदिग्ध खाता या कार्ड ब्लॉक करवाएं।"
        )
    return (
        f"🛡️ *Rakshak AI — Cyber Incident Draft Report*\n\n"
        f"Your incident intake draft has been generated.\n"
        f"• Report Reference: *{report_id}*\n"
        f"• Secure Download Link: {secure_url}\n\n"
        f"⚠️ *Important Legal Notice:*\n"
        f"This document is an assistance draft, not an official police FIR. "
        f"To file an official complaint, immediately call the National Cyber Crime Helpline *1930* "
        f"or register at www.cybercrime.gov.in.\n\n"
        f"Notify your bank immediately to block any compromised cards or accounts."
    )


# ══════════════════════════════════════════════
#  4. TWILIO REST CLIENT DISPATCH (SMS & WHATSAPP)
# ══════════════════════════════════════════════

def _resolve_twilio_client(client: Optional[Any] = None) -> Tuple[Optional[Any], Optional[str]]:
    """Resolves or initializes a Twilio REST client safely."""
    if client is not None:
        return client, None

    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        return None, "Twilio credentials missing (TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN)"

    try:
        from twilio.rest import Client
        return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), None
    except Exception as e:
        return None, f"Failed to initialize Twilio client: {e}"


def send_report_sms(
    to_phone: str,
    secure_url: str,
    report_id: str,
    language: str = "hi",
    client: Optional[Any] = None,
    from_number: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Sends the secure report link via SMS using the configured Twilio account.
    Handles Twilio trial restrictions (e.g. error 21608 unverified caller ID) gracefully.
    Never raises an uncaught exception.
    """
    sender = from_number or TWILIO_PHONE_NUMBER
    if not sender:
        return {
            "success": False,
            "channel": "sms",
            "sid": None,
            "status": "config_error",
            "to": mask_phone(to_phone),
            "error_code": None,
            "error_message": "Twilio sender phone number is not configured (TWILIO_PHONE_NUMBER)",
        }

    try:
        normalized_to = normalize_phone_number(to_phone)
    except ValueError as ve:
        return {
            "success": False,
            "channel": "sms",
            "sid": None,
            "status": "invalid_number",
            "to": mask_phone(to_phone),
            "error_code": 21211,
            "error_message": str(ve),
        }

    twilio_client, err = _resolve_twilio_client(client)
    if not twilio_client:
        return {
            "success": False,
            "channel": "sms",
            "sid": None,
            "status": "client_error",
            "to": mask_phone(normalized_to),
            "error_code": 20003,
            "error_message": err or "Twilio client unavailable",
        }

    sms_body = get_sms_text(report_id, secure_url, language)

    try:
        message = twilio_client.messages.create(
            body=sms_body,
            from_=sender,
            to=normalized_to,
        )
        logger.info(
            f"[SMS] Dispatched to {mask_phone(normalized_to)} | SID={message.sid} | Status={message.status}"
        )
        return {
            "success": True,
            "channel": "sms",
            "sid": message.sid,
            "status": message.status,
            "to": mask_phone(normalized_to),
            "error_code": None,
            "error_message": None,
        }
    except Exception as e:
        # Check for Twilio-specific error codes
        code = getattr(e, "code", None)
        msg_text = str(e)

        if code == 21608:
            friendly = (
                "Twilio Trial Restriction: The destination phone number is not a verified caller ID. "
                "Add and verify this number in Twilio Console (Phone Numbers > Verified Caller IDs)."
            )
        elif code == 21211:
            friendly = f"Invalid destination phone number: {mask_phone(normalized_to)}"
        elif code == 21408:
            friendly = "Permission to send SMS to this destination region is disabled in Twilio Geo-permissions."
        elif code == 20003:
            friendly = "Twilio authentication failed. Please verify TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN."
        else:
            friendly = f"Twilio SMS delivery failed: {msg_text}"

        logger.warning(
            f"[SMS] Notice: Could not send SMS to {mask_phone(normalized_to)} (Code {code}): {friendly}"
        )
        return {
            "success": False,
            "channel": "sms",
            "sid": None,
            "status": "failed",
            "to": mask_phone(normalized_to),
            "error_code": code,
            "error_message": friendly,
        }


def send_report_whatsapp(
    to_phone: str,
    secure_url: str,
    report_id: str,
    language: str = "hi",
    client: Optional[Any] = None,
    from_sender: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Sends the secure report link via WhatsApp using the Twilio WhatsApp API / Sandbox.
    Handles Twilio WhatsApp Sandbox opt-in requirements (error 63007) gracefully.
    Never raises an uncaught exception.
    """
    sender = from_sender or TWILIO_WHATSAPP_FROM or "whatsapp:+14155238886"
    if not sender.startswith("whatsapp:"):
        sender = f"whatsapp:{sender}"

    try:
        normalized_to = normalize_phone_number(to_phone)
    except ValueError as ve:
        return {
            "success": False,
            "channel": "whatsapp",
            "sid": None,
            "status": "invalid_number",
            "to": mask_phone(to_phone),
            "error_code": 21211,
            "error_message": str(ve),
        }

    # Format destination for Twilio WhatsApp
    whatsapp_to = f"whatsapp:{normalized_to}"

    twilio_client, err = _resolve_twilio_client(client)
    if not twilio_client:
        return {
            "success": False,
            "channel": "whatsapp",
            "sid": None,
            "status": "client_error",
            "to": mask_phone(normalized_to),
            "error_code": 20003,
            "error_message": err or "Twilio client unavailable",
        }

    whatsapp_body = get_whatsapp_text(report_id, secure_url, language)

    try:
        message = twilio_client.messages.create(
            body=whatsapp_body,
            from_=sender,
            to=whatsapp_to,
        )
        logger.info(
            f"[WhatsApp] Dispatched to {mask_phone(normalized_to)} | SID={message.sid} | Status={message.status}"
        )
        return {
            "success": True,
            "channel": "whatsapp",
            "sid": message.sid,
            "status": message.status,
            "to": mask_phone(normalized_to),
            "error_code": None,
            "error_message": None,
        }
    except Exception as e:
        code = getattr(e, "code", None)
        msg_text = str(e)

        if code == 63007:
            friendly = (
                "Twilio WhatsApp Sandbox Opt-in Required: The recipient has not joined the WhatsApp Sandbox. "
                "The recipient must send 'join <sandbox-code>' to +1 415 523 8886 on WhatsApp first."
            )
        elif code == 21608:
            friendly = (
                "Twilio Trial Restriction: The destination phone number is not verified on your Twilio account."
            )
        elif code == 63016:
            friendly = (
                "Twilio WhatsApp Session Window: Attempted to send a freeform message outside the 24-hour "
                "conversation window. An approved WhatsApp template is required for business-initiated chats."
            )
        elif code == 21211:
            friendly = f"Invalid destination WhatsApp number: {mask_phone(normalized_to)}"
        else:
            friendly = f"Twilio WhatsApp delivery failed: {msg_text}"

        logger.warning(
            f"[WhatsApp] Notice: Could not send WhatsApp to {mask_phone(normalized_to)} (Code {code}): {friendly}"
        )
        return {
            "success": False,
            "channel": "whatsapp",
            "sid": None,
            "status": "failed",
            "to": mask_phone(normalized_to),
            "error_code": code,
            "error_message": friendly,
        }


# ══════════════════════════════════════════════
#  5. CALL DISPATCH TRACKING & IDEMPOTENCY
# ══════════════════════════════════════════════

def is_delivery_already_dispatched(call_sid: str, channel: str) -> bool:
    """Checks whether a message has already been dispatched for this call and channel."""
    with _dispatch_lock:
        call_records = _dispatched_deliveries.get(call_sid, {})
        return channel in call_records


def record_delivery_dispatch(
    call_sid: str,
    channel: str,
    sid: Optional[str] = None,
    status: str = "sent",
) -> None:
    """Records that a message dispatch attempt has occurred for a CallSid to avoid duplicate sends."""
    with _dispatch_lock:
        if call_sid not in _dispatched_deliveries:
            _dispatched_deliveries[call_sid] = {}
        _dispatched_deliveries[call_sid][channel] = {
            "sid": sid,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def get_delivery_records(call_sid: str) -> Dict[str, Any]:
    """Retrieves delivery status records for a given CallSid."""
    with _dispatch_lock:
        return dict(_dispatched_deliveries.get(call_sid, {}))
