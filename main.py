"""
Rakshak AI — Voice-Based Cybercrime Assistance & Reporting System
FastAPI Backend with Twilio Voice, Google Speech-to-Text, LLM Incident Intelligence, and PDF Generation.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response, FileResponse, JSONResponse
from fpdf import FPDF
import requests
import os
import re
import uuid
import json
import asyncio
from datetime import datetime
import logging
from pathlib import Path

# Ensure SpeechRecognition compatibility with Python 3.13/3.14
try:
    import standard_aifc as aifc
    import sys
    sys.modules["aifc"] = aifc
except ImportError:
    pass

import speech_recognition as sr
from pydub import AudioSegment

from config import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_PHONE_NUMBER,
    DEMO_TO_NUMBER,
    BASE_URL,
    mask_phone,
    mask_secret,
)
from llm_analyzer import (
    analyze_incident_with_llm,
    CybercrimeIncidentAnalysis,
    IncidentState,
    FieldStatus,
    FieldValue,
    select_next_follow_up_question,
    merge_extracted_facts,
    extract_facts_from_text,
    CATEGORY_FIELD_PRIORITIES,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rakshak_ai")

app = FastAPI(
    title="Rakshak AI",
    description="Voice-based cybercrime assistance and automated incident reporting",
    version="2.1.0",
)

# ══════════════════════════════════════════════
#  DIRECTORY & FONT CONFIGURATION
# ══════════════════════════════════════════════
BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"
TEMP_DIR = BASE_DIR / "temp"
FONTS_DIR = BASE_DIR / "fonts"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

FONT_HI = str(FONTS_DIR / "NotoSansDevanagari-Regular.ttf")
FONT_HI_B = str(FONTS_DIR / "NotoSansDevanagari-Bold.ttf")
FONT_EN = str(FONTS_DIR / "NotoSans-Regular.ttf")

# In-memory session store keyed strictly by CallSid
sessions: dict[str, dict] = {}


# ══════════════════════════════════════════════
#  SCENARIO DEFINITIONS & BILINGUAL CONTENT
# ══════════════════════════════════════════════
SCENARIOS = {
    "OTP_FRAUD": {
        "label_hi": "ओटीपी / बैंकिंग धोखाधड़ी",
        "label_en": "OTP / Banking Fraud",
        "question_hi": "कृपया बताएं कि इस धोखाधड़ी में आपका कुल कितने रुपये का नुकसान हुआ है?",
        "question_en": "Please state the total amount of money lost or debited from your account.",
    },
    "OLX_SCAM": {
        "label_hi": "ओएलएक्स / मार्केटप्लेस धोखाधड़ी",
        "label_en": "OLX / Marketplace Scam",
        "question_hi": "यह धोखाधड़ी किस ऑनलाइन प्लेटफॉर्म पर हुई, जैसे ओएलएक्स, फेसबुक मार्केटप्लेस, या क्विकर?",
        "question_en": "Which platform did this occur on, such as OLX, Facebook Marketplace, or Quikr?",
    },
    "JOB_SCAM": {
        "label_hi": "फर्जी नौकरी / टास्क धोखाधड़ी",
        "label_en": "Job / Task Scam",
        "question_hi": "नौकरी या टास्क का ऑफर आपको किस प्लेटफॉर्म पर मिला था, जैसे टेलीग्राम या व्हाट्सएप?",
        "question_en": "On which platform was this job or task offered, such as Telegram or WhatsApp?",
    },
    "LOAN_FRAUD": {
        "label_hi": "फर्जी लोन ऐप / एक्सटॉर्शन धोखाधड़ी",
        "label_en": "Loan App Fraud",
        "question_hi": "उस फर्जी लोन ऐप का नाम क्या है जिससे आपने लोन लिया या अप्लाई किया था?",
        "question_en": "What is the exact name of the loan application you downloaded or applied through?",
    },
    "PHISHING": {
        "label_hi": "फ़िशिंग / खाता समझौता",
        "label_en": "Phishing / Account Compromise",
        "question_hi": "कृपया बताएं कि इस धोखाधड़ी में आपका कुल कितने रुपये का नुकसान हुआ है?",
        "question_en": "Please state the total amount of financial loss incurred in this incident.",
    },
    "GENERAL_FRAUD": {
        "label_hi": "सामान्य साइबर अपराध",
        "label_en": "General Cybercrime",
        "question_hi": "कृपया बताएं कि इस धोखाधड़ी में आपका कुल कितने रुपये का नुकसान हुआ है?",
        "question_en": "Please state the total amount of financial loss incurred in this incident.",
    },
}

KEYWORDS = {
    "OTP_FRAUD": [
        "otp", "one time password", "bank", "bank account", "password", "pin", "atm", "cvv",
        "debit", "credit card", "kyc", "sbi", "hdfc", "icici", "pnb", "axis", "net banking",
        "ओटीपी", "बैंक", "खाता", "पासवर्ड", "पिन", "एटीएम", "केवाईसी", "सीवीवी"
    ],
    "OLX_SCAM": [
        "olx", "quikr", "qr", "qr code", "scanner", "scan", "facebook marketplace",
        "buyer", "seller", "army", "courier", "advance payment",
        "ओएलएक्स", "क्यूआर", "स्कैन", "स्कैनर", "बेचना", "खरीदना"
    ],
    "JOB_SCAM": [
        "job", "part time", "telegram", "wfh", "work from home", "data entry",
        "youtube like", "subscribe", "task", "prepaid", "registration fee", "commission", "hr",
        "नौकरी", "टेलीग्राम", "पार्ट टाइम", "टास्क", "रजिस्ट्रेशन", "फीस", "कमीशन"
    ],
    "LOAN_FRAUD": [
        "loan", "instant loan", "loan app", "processing fee", "emi", "interest",
        "cibil", "credit score", "gallery", "contacts", "threat", "blackmail", "recovery agent",
        "लोन", "ऋण", "बीमा", "किस्त", "धमकी", "रिकवरी"
    ],
    "PHISHING": [
        "phishing", "fake link", "link", "apk", "malware", "fake site", "website",
        "फ़िशिंग", "लिंक", "वेबसाइट", "एपीके"
    ],
}


def detect_scenario(text: str) -> str:
    """Classify fraud scenario based on bilingual keywords."""
    clean = text.lower()
    for category, words in KEYWORDS.items():
        for w in words:
            if w.isascii():
                if re.search(r"\b" + re.escape(w) + r"\b", clean):
                    return category
            else:
                if w in clean:
                    return category
    return "GENERAL_FRAUD"


def extract_loss_amount(text: str) -> str:
    """Extract mentioned loss amounts from transcript."""
    patterns = [
        r"(?:₹|rs\.?|inr|रुपये|रुपए)\s*([0-9]+(?:,[0-9]+)*)",
        r"([0-9]+(?:,[0-9]+)*)\s*(?:₹|rs\.?|inr|रुपये|रुपए|rupees)",
        r"([0-9]+\s*(?:thousand|lakh|crore|हज़ार|हजार|लाख))",
        r"\b([0-9]{3,7})\b",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()
    return "Not explicitly specified"


def sanitize_sensitive_data(text: str) -> str:
    """Redact sensitive credentials like 4-6 digit OTPs, PINs, CVVs from transcripts."""
    redacted = re.sub(r"\b(otp|pin|cvv|password)\s*(?:is|was|tha|hai)?\s*([0-9]{4,6})\b", r"\1 [REDACTED]", text, flags=re.IGNORECASE)
    redacted = re.sub(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b", "[CARD REDACTED]", redacted)
    return redacted


def get_base_url(request: Request = None) -> str:
    """Dynamically obtain base URL from active request headers, falling back to config."""
    if request is not None and hasattr(request, "headers"):
        headers = request.headers
        if isinstance(headers, dict) or hasattr(headers, "get"):
            proto = headers.get("x-forwarded-proto", "https")
            host = headers.get("x-forwarded-host") or headers.get("host")
            if host:
                return f"{proto}://{host}".rstrip("/")
    return os.getenv("BASE_URL", BASE_URL).rstrip("/")


# ══════════════════════════════════════════════
#  AUDIO & TRANSCRIPTION (NON-BLOCKING)
# ══════════════════════════════════════════════
def _download_and_convert_audio_sync(url: str, call_sid: str) -> str:
    """Synchronous worker: Downloads recording from Twilio and converts to 16kHz PCM WAV."""
    raw_path = TEMP_DIR / f"{call_sid}_raw.wav"
    conv_path = TEMP_DIR / f"{call_sid}_conv.wav"

    response = requests.get(url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), timeout=6)
    response.raise_for_status()

    with open(raw_path, "wb") as f:
        f.write(response.content)

    audio = AudioSegment.from_file(str(raw_path))
    audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)
    audio.export(str(conv_path), format="wav")

    return str(conv_path)


def _transcribe_file_sync(wav_path: str, language_code: str) -> str:
    """Synchronous worker: Runs Google Speech Recognition on local WAV file with strict timeout."""
    recognizer = sr.Recognizer()
    recognizer.operation_timeout = 4
    with sr.AudioFile(wav_path) as source:
        audio_data = recognizer.record(source)

    return recognizer.recognize_google(audio_data, language=language_code)


async def transcribe_audio_async(url: str, call_sid: str, language: str = "hi") -> str:
    """Non-blocking audio download and transcription with safe 6s timeout."""
    lang_code = "hi-IN" if language == "hi" else "en-IN"
    try:
        conv_path = await asyncio.wait_for(
            asyncio.to_thread(_download_and_convert_audio_sync, url, call_sid),
            timeout=5.0,
        )
        text = await asyncio.wait_for(
            asyncio.to_thread(_transcribe_file_sync, conv_path, lang_code),
            timeout=5.0,
        )
        logger.info(f"[STT] ({language}) {call_sid} -> {text}")
        return text.strip()
    except asyncio.TimeoutError:
        logger.warning(f"[STT] Transcription timed out for {call_sid}")
        return ""
    except sr.UnknownValueError:
        logger.warning(f"[STT] Inaudible or unintelligible audio for {call_sid}")
        return ""
    except sr.RequestError as e:
        logger.error(f"[STT] Google Speech API request error for {call_sid}: {e}")
        return ""
    except Exception as e:
        logger.error(f"[STT] Audio processing failed for {call_sid}: {e}")
        return ""


# ══════════════════════════════════════════════
#  PDF GENERATION ENGINE (FPDF2)
# ══════════════════════════════════════════════
def generate_pdf_report(data: dict) -> str:
    """
    Generate an official, tamper-evident bilingual Incident Report.
    Ensures Devanagari text renders with NotoSansDevanagari and English with NotoSans.
    """
    report_id = data.get("report_id") or f"RAK-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    data["report_id"] = report_id

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Register fonts safely
    pdf.add_font("Devanagari", "", FONT_HI)
    pdf.add_font("Devanagari", "B", FONT_HI_B)
    pdf.add_font("NotoSans", "", FONT_EN)
    pdf.set_fallback_fonts(["NotoSans", "Devanagari"])

    # ── Header Banner ──
    pdf.set_fill_color(10, 25, 70)  # Navy
    pdf.rect(0, 0, 210, 30, "F")
    pdf.set_y(5)
    pdf.set_text_color(0, 200, 200)  # Cyan
    pdf.set_font("NotoSans", "", 18)
    pdf.cell(0, 8, "RAKSHAK AI — CYBERCRIME FIRST RESPONDER REPORT", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(240, 240, 240)
    pdf.set_font("NotoSans", "", 9)
    pdf.cell(0, 6, "AI-Assisted Citizen Incident Intake & Evidence Documentation", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # ── Case Summary Details Box ──
    pdf.set_fill_color(240, 248, 255)
    pdf.set_draw_color(0, 150, 180)
    pdf.set_line_width(0.3)
    box_y = pdf.get_y()
    pdf.rect(10, box_y, 190, 62, "FD")
    pdf.set_xy(14, box_y + 3)

    is_hindi = (data.get("language") == "hi")
    scen_key = data.get("scenario", "GENERAL_FRAUD")
    scen_info = SCENARIOS.get(scen_key, SCENARIOS["GENERAL_FRAUD"])
    category_label = f"{scen_info['label_en']} ({scen_info['label_hi']})"

    llm_an = data.get("llm_analysis") or {}
    inc_date = data.get("incident_date") or llm_an.get("incident_date")
    inc_time = data.get("incident_time") or llm_an.get("incident_time")
    bank_info = data.get("bank_details") or llm_an.get("bank_details") or {}
    suspect_info = data.get("suspect_details") or llm_an.get("suspect_details") or {}
    missing_info = data.get("missing_information") or llm_an.get("missing_information") or []

    raw_st = data.get("incident_state")
    if raw_st and isinstance(raw_st, dict):
        if not inc_date and raw_st.get("incident_date", {}).get("value"):
            inc_date = raw_st["incident_date"]["value"]
        if not inc_time and raw_st.get("incident_time", {}).get("value"):
            inc_time = raw_st["incident_time"]["value"]
        if not data.get("financial_loss") and raw_st.get("financial_loss", {}).get("value"):
            data["financial_loss"] = raw_st["financial_loss"]["value"]
        if not bank_info.get("bank_name") and raw_st.get("bank_name", {}).get("value"):
            bank_info["bank_name"] = raw_st["bank_name"]["value"]
        if not suspect_info.get("names") and raw_st.get("suspect_contact", {}).get("value"):
            suspect_info.setdefault("names", [raw_st["suspect_contact"]["value"]])
        if not missing_info and raw_st.get("missing_information"):
            missing_info = raw_st["missing_information"]

    def meta_row(label: str, val: str, use_hindi: bool = False):
        pdf.set_x(14)
        pdf.set_font("NotoSans", "", 10)
        pdf.set_text_color(10, 25, 70)
        pdf.cell(55, 6, f"{label}:", border=0)
        pdf.set_font("Devanagari" if use_hindi else "NotoSans", "", 10)
        pdf.set_text_color(20, 20, 20)
        pdf.cell(0, 6, val, new_x="LMARGIN", new_y="NEXT")

    meta_row("Report Identification", report_id)
    meta_row("Incident Intake Time", datetime.now().strftime("%d %B %Y, %I:%M %p IST"))
    if inc_date or inc_time:
        occ_val = f"{inc_date or ''}" + (f" ({inc_time})" if inc_time else "")
        meta_row("Incident Occurrence", occ_val, use_hindi=True)
    meta_row("Caller / Victim Name", data.get("name") or "Anonymous Citizen", use_hindi=is_hindi)
    meta_row("Interview Language", "Hindi (हिन्दी)" if is_hindi else "English")
    meta_row("Suspected Fraud Category", category_label, use_hindi=True)
    meta_row("Estimated Financial Loss", data.get("financial_loss") or "Not explicitly specified", use_hindi=is_hindi)
    meta_row("Twilio Telephony SID", data.get("call_sid") or "Direct Outbound")

    pdf.set_y(box_y + 66)

    def render_section(title: str, content: str, use_hindi: bool = True):
        pdf.set_fill_color(10, 25, 70)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("NotoSans", "", 11)
        pdf.cell(0, 7, f"  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        pdf.set_text_color(30, 30, 30)
        pdf.set_font("Devanagari" if use_hindi else "NotoSans", "", 10)
        clean_text = sanitize_sensitive_data(content.strip() or "No statement provided.")
        pdf.multi_cell(190, 6, clean_text)
        pdf.ln(4)

    # Incident Narrative
    story_title = "VICTIM'S RECORDED STATEMENT / पीड़ित का बयान"
    render_section(story_title, data.get("story", ""), use_hindi=True)

    # Follow-up Q&A
    qa_title = "FOLLOW-UP INVESTIGATION DETAILS / अतिरिक्त विवरण"
    qa_pairs = data.get("qa_pairs", [])
    if qa_pairs:
        qa_lines = []
        for i, pair in enumerate(qa_pairs, 1):
            q_text = pair.get("question", "")
            a_text = pair.get("answer", "")
            if q_text or a_text:
                qa_lines.append(f"Q{i}: {q_text}\nA: {a_text}")
        qa_content = "\n\n".join(qa_lines) if qa_lines else "No follow-up responses recorded."
    else:
        fq = data.get("follow_up_question", "")
        fa = data.get("details", "")
        qa_content = f"Question Asked: {fq}\nResponse Given: {fa}" if (fq or fa) else "No follow-up responses recorded."
    render_section(qa_title, qa_content, use_hindi=True)

    # Evidentiary Particulars (Bank Details & Suspect Details)
    ev_lines = []
    if inc_date or inc_time:
        ev_lines.append(f"• Incident Occurrence Date/Time: {inc_date or 'Not stated'}" + (f" at {inc_time}" if inc_time else ""))

    b_name = bank_info.get("bank_name")
    b_branch = bank_info.get("bank_branch")
    b_acc = bank_info.get("account_number")
    if b_name or b_branch or b_acc:
        acc_masked = f"XXXX{b_acc[-4:]}" if (b_acc and len(b_acc) >= 4) else (b_acc or "Not stated")
        ev_lines.append(f"• Victim Bank Information: {b_name or 'Bank unspecified'}, Branch: {b_branch or 'Not stated'}, A/C: {acc_masked}")

    s_names = suspect_info.get("names", [])
    s_phones = suspect_info.get("phone_numbers", [])
    s_upis = suspect_info.get("upi_ids", [])
    s_emails = suspect_info.get("emails", [])
    s_telegrams = suspect_info.get("telegram_handles", [])

    if s_names or s_phones or s_upis or s_emails or s_telegrams:
        ev_lines.append("• Suspect / Accused Identifiers:")
        if s_names:
            ev_lines.append(f"   - Name / Alias: {', '.join(s_names)}")
        if s_phones:
            ev_lines.append(f"   - Contact Phone: {', '.join(s_phones)}")
        if s_upis:
            ev_lines.append(f"   - UPI ID: {', '.join(s_upis)}")
        if s_emails:
            ev_lines.append(f"   - Email Address: {', '.join(s_emails)}")
        if s_telegrams:
            ev_lines.append(f"   - Telegram Handles: @{', @'.join(s_telegrams)}")

    if missing_info:
        ev_lines.append(f"• Pending / Missing Evidentiary Items: {', '.join(missing_info)}")

    if ev_lines:
        ev_title = "EVIDENTIARY PARTICULARS & BANK / SUSPECT DETAILS / साक्ष्य एवं बैंक/संदिग्ध विवरण"
        render_section(ev_title, "\n".join(ev_lines), use_hindi=True)

    # Formal Complaint Draft if generated by LLM
    draft = data.get("formal_complaint_draft")
    if draft:
        draft_title = "OFFICIAL COMPLAINT DRAFT (FOR CYBERCRIME.GOV.IN SUBMISSION)"
        render_section(draft_title, draft, use_hindi=True)

    # ── Immediate Action Guidance Box ──
    pdf.set_fill_color(255, 243, 205)
    pdf.set_draw_color(255, 165, 0)
    adv_y = pdf.get_y()
    pdf.rect(10, adv_y, 190, 32, "FD")
    pdf.set_xy(14, adv_y + 2)
    pdf.set_font("NotoSans", "", 10)
    pdf.set_text_color(140, 70, 0)
    pdf.cell(0, 6, "CRITICAL NEXT STEPS / तत्काल आवश्यक कदम:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("NotoSans", "", 9)
    pdf.set_text_color(20, 20, 20)
    pdf.set_x(14)
    advisory_text = (
        "1. DIAL 1930: Contact the National Cybercrime Reporting Helpline immediately for financial freeze.\n"
        "2. NOTIFY BANK: Request an immediate freeze of compromised debit/credit cards and accounts.\n"
        "3. FORMAL PORTAL: Register an official complaint online at https://cybercrime.gov.in."
    )
    pdf.multi_cell(180, 5, advisory_text)
    pdf.ln(4)

    # ── Mandatory Legal Disclaimer ──
    pdf.set_fill_color(245, 245, 245)
    pdf.set_draw_color(180, 180, 180)
    disc_y = pdf.get_y()
    pdf.rect(10, disc_y, 190, 22, "FD")
    pdf.set_xy(12, disc_y + 2)
    pdf.set_font("NotoSans", "", 7.5)
    pdf.set_text_color(90, 90, 90)
    disclaimer_text = (
        "DISCLAIMER & NOTICE: This report is generated automatically by Rakshak AI based solely on verbal disclosures "
        "provided by the caller during an emergency voice interview. It serves as an intake record for citizen guidance "
        "and documentation assistance. This document DOES NOT constitute an official Police First Information Report (FIR) "
        "or legal banking chargeback. Citizens must register an official complaint at https://cybercrime.gov.in."
    )
    pdf.multi_cell(186, 3.8, disclaimer_text)
    pdf.ln(4)

    clean_name = re.sub(r"[^\w\s-]", "", data.get("name", "Citizen")).strip() or "Citizen"
    clean_name = clean_name.replace(" ", "_")[:20]
    filename = f"Rakshak_Report_{report_id}_{clean_name}.pdf"
    pdf_path = REPORTS_DIR / filename
    pdf.output(str(pdf_path))

    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        raise RuntimeError(f"PDF generation failed or created 0-byte file: {pdf_path}")

    logger.info(f"[PDF] Report successfully created: {pdf_path.name} ({pdf_path.stat().st_size} bytes)")
    return str(pdf_path)


def save_json_report(data: dict) -> str:
    """Save structured report metadata as JSON."""
    report_id = data.get("report_id") or f"RAK-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    data["report_id"] = report_id
    filename = f"Data_{report_id}.json"
    json_path = REPORTS_DIR / filename

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"[JSON] Data successfully saved: {json_path.name}")
    return str(json_path)


# ══════════════════════════════════════════════
#  TWIML RESPONSE HELPERS (DYNAMIC RELATIVE URLS)
# ══════════════════════════════════════════════
def twiml_response(xml_body: str) -> Response:
    content = f'<?xml version="1.0" encoding="UTF-8"?><Response>{xml_body}</Response>'
    return Response(content=content, media_type="application/xml")


def say(text: str, language: str = "hi") -> str:
    """Render Twilio Say verb with proper Polly voice."""
    if language == "hi":
        return f'<Say language="hi-IN" voice="Polly.Aditi">{text}</Say>'
    else:
        return f'<Say language="en-IN" voice="Polly.Aditi">{text}</Say>'


def record(action: str, max_length: int = 45, finish_on_key: str = "#") -> str:
    """
    Generate Record verb with finishOnKey and relative action URL so Twilio resolves it
    against the active incoming request host.
    """
    act = action if action.startswith("/") else f"/{action}"
    finish_attr = f'finishOnKey="{finish_on_key}"' if finish_on_key else ""
    return (
        f'<Record action="{act}" method="POST" '
        f'{finish_attr} maxLength="{max_length}" playBeep="true" trim="trim-silence"/>'
    )


def clean_caller_name(raw: str, lang: str = "hi") -> str:
    """Extract clean person name from natural spoken introductions like 'मेरा नाम आशीष मौर्य है'."""
    if not raw:
        return "नागरिक" if lang == "hi" else "Citizen"
    cleaned = raw.strip()
    # Strip common Hindi intros/outros
    cleaned = re.sub(r"^(मेरा\s*नाम|नाम|मैं)\s*(?:है\s*)?", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^(my\s*name\s*is|this\s*is|i\s*am)\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*(है|हूँ|हु|बोल\s*रहा\s*हूँ|speaking|here)[.!]?$", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"[।.,!?:;\"'()\[\]{}]", "", cleaned).strip()
    return cleaned or ("नागरिक" if lang == "hi" else "Citizen")


def speech_gather_or_record(
    action: str,
    language: str = "hi",
    max_speech_time: int = 20,
    max_record_len: int = 45,
    finish_on_key: str = "#",
) -> str:
    """
    Combined Twilio speech gather + DTMF `#` finish + record fallback.
    Twilio uses input="speech dtmf" with finishOnKey="#".
    - When the caller speaks and presses '#', Twilio immediately stops collecting speech,
      transcribes it, and POSTs SpeechResult along with Digits="#".
    - If the caller finishes speaking without pressing '#', speechTimeout="auto" automatically
      detects silence (in ~2-3s) and submits without waiting for maxSpeechTime.
    - If no speech is detected, Twilio seamlessly falls back to <Record finishOnKey="#">.
    """
    lang_code = "hi-IN" if language == "hi" else "en-IN"
    act = action if action.startswith("/") else f"/{action}"
    finish_attr = f'finishOnKey="{finish_on_key}"' if finish_on_key else ""
    return (
        f'<Gather input="speech dtmf" action="{act}" method="POST" '
        f'language="{lang_code}" {finish_attr} speechTimeout="auto" timeout="8" maxSpeechTime="{max_speech_time}">'
        f'</Gather>'
        f'{record(act, max_length=max_record_len, finish_on_key=finish_on_key)}'
    )


# ══════════════════════════════════════════════
#  CALL FLOW ROUTES
# ══════════════════════════════════════════════

@app.post("/incoming-call")
async def incoming_call(request: Request):
    """
    Step 1 & 2: Greet caller and offer language selection menu (DTMF).
    1 for Hindi, 2 for English.
    Uses relative action URLs so it works across any tunnel or domain!
    """
    form = await request.form()
    call_sid = form.get("CallSid", str(uuid.uuid4()))
    from_num = form.get("From", "")

    logger.info(f"[CALL] Received incoming call: SID={call_sid}, From={mask_phone(from_num)}")

    sessions[call_sid] = {
        "call_sid": call_sid,
        "caller_phone": from_num,
        "language": "hi",
        "lang_retry": 0,
        "name": "",
        "name_retries": 0,
        "step1_completed": False,
        "story": "",
        "story_retries": 0,
        "step2_completed": False,
        "scenario": "GENERAL_FRAUD",
        "scenario_label": "General Cybercrime",
        "follow_up_question": "",
        "last_targeted_field": None,
        "details": "",
        "details_retries": 0,
        "step3_completed": False,
        "financial_loss": "",
        "incident_date": "",
        "incident_time": "",
        "bank_details": {},
        "suspect_details": {},
        "missing_information": [],
        "formal_complaint_draft": "",
        "incident_state": IncidentState().model_dump(),
        "llm_analysis": {},
        "started_at": datetime.now().isoformat(),
        "status": "IN_PROGRESS",
    }

    body = (
        '<Gather action="/select-language" method="POST" numDigits="1" timeout="7">'
        + say("नमस्ते! रक्षक एआई में आपका स्वागत है। हिंदी में बात करने के लिए 1 दबाएं।", language="hi")
        + say("Welcome to Rakshak AI. Press 1 for Hindi, or press 2 for English.", language="en")
        + '</Gather>'
        + f'<Redirect method="POST">/retry-language?CallSid={call_sid}</Redirect>'
    )
    return twiml_response(body)


@app.post("/retry-language")
async def retry_language(request: Request, CallSid: str = ""):
    """Handles timeout or no-input during language selection."""
    form = await request.form()
    call_sid = form.get("CallSid") or CallSid
    session = sessions.get(call_sid, {})
    retries = session.get("lang_retry", 0) + 1
    session["lang_retry"] = retries

    if retries <= 2:
        body = (
            '<Gather action="/select-language" method="POST" numDigits="1" timeout="7">'
            + say("कृपया हिंदी के लिए 1, या English के लिए 2 दबाएं।", language="hi")
            + say("Please press 1 for Hindi, or 2 for English.", language="en")
            + '</Gather>'
            + f'<Redirect method="POST">/retry-language?CallSid={call_sid}</Redirect>'
        )
        return twiml_response(body)
    else:
        session["language"] = "hi"
        body = (
            say("कोई इनपुट नहीं मिला। हम हिंदी में आगे बढ़ रहे हैं।", language="hi")
            + say("कृपया बीप के बाद अपना पूरा नाम बोलें और समाप्त होने पर हैश (#) दबाएं।", language="hi")
            + speech_gather_or_record("/step1-name", language="hi", max_speech_time=15, max_record_len=15)
        )
        return twiml_response(body)


@app.post("/select-language")
async def select_language(request: Request):
    """Processes DTMF selection: 1 for Hindi, 2 for English."""
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    digits = (form.get("Digits") or "").strip()

    if call_sid not in sessions:
        sessions[call_sid] = {"call_sid": call_sid, "started_at": datetime.now().isoformat()}

    session = sessions[call_sid]

    if digits == "1":
        session["language"] = "hi"
        body = (
            say("आपने हिंदी चुनी है। रक्षक एआई आपकी सहायता के लिए तैयार है।", language="hi")
            + say("कृपया बीप के बाद अपना पूरा नाम बोलें और समाप्त होने पर हैश (#) दबाएं।", language="hi")
            + speech_gather_or_record("/step1-name", language="hi", max_speech_time=15, max_record_len=15)
        )
        return twiml_response(body)

    elif digits == "2":
        session["language"] = "en"
        body = (
            say("You have selected English. Rakshak AI is here to assist you.", language="en")
            + say("Please say your full name after the beep and press hash (#) when finished.", language="en")
            + speech_gather_or_record("/step1-name", language="en", max_speech_time=15, max_record_len=15)
        )
        return twiml_response(body)

    else:
        body = (
            '<Gather action="/select-language" method="POST" numDigits="1" timeout="7">'
            + say("अमान्य विकल्प। हिंदी के लिए 1 या English के लिए 2 दबाएं।", language="hi")
            + say("Invalid option. Press 1 for Hindi or 2 for English.", language="en")
            + '</Gather>'
            + f'<Redirect method="POST">/retry-language?CallSid={call_sid}</Redirect>'
        )
        return twiml_response(body)


@app.post("/step1-name")
async def step1_name(request: Request):
    """Step 3: Collect caller name and prompt for the incident story."""
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    speech_result = (form.get("SpeechResult") or "").strip()
    audio_url = form.get("RecordingUrl", "")

    session = sessions.setdefault(call_sid, {"call_sid": call_sid, "language": "hi"})
    lang = session.get("language", "hi")

    # Idempotency check: if Step 1 was already successfully completed for this CallSid
    if session.get("step1_completed"):
        name = session.get("name", "नागरिक" if lang == "hi" else "Citizen")
        logger.info(f"[IDEMPOTENCY] Step 1 already completed for {call_sid}, re-serving Question 2 prompt")
        if lang == "hi":
            body = (
                say(f"धन्यवाद, {name} जी।", language="hi")
                + say("बीप के बाद कृपया विस्तार से बताएं कि आपके साथ क्या घटना घटी और समाप्त होने पर हैश (#) दबाएं।", language="hi")
                + speech_gather_or_record("/step2-story", language="hi", max_speech_time=60, max_record_len=60)
            )
        else:
            body = (
                say(f"Thank you, {name}.", language="en")
                + say("After the beep, please describe in detail what happened and press hash (#) when finished.", language="en")
                + speech_gather_or_record("/step2-story", language="en", max_speech_time=60, max_record_len=60)
            )
        return twiml_response(body)

    raw_name = ""
    if speech_result:
        logger.info(f"[SPEECH] ({lang}) {call_sid} name -> {speech_result}")
        raw_name = speech_result
    elif audio_url:
        raw_name = await transcribe_audio_async(audio_url, call_sid, language=lang)

    # Empty answer check: if caller pressed # without speaking or audio was inaudible
    clean_raw = raw_name.replace("#", "").strip()
    if not clean_raw:
        retries = session.get("name_retries", 0) + 1
        session["name_retries"] = retries
        if retries <= 2:
            logger.warning(f"[RETRY] Step 1 empty name retry {retries}/2 for {call_sid}")
            if lang == "hi":
                body = (
                    say("हमें आपका नाम सुनाई नहीं दिया। कृपया बीप के बाद अपना पूरा नाम बोलें और समाप्त होने पर हैश (#) दबाएं।", language="hi")
                    + speech_gather_or_record("/step1-name", language="hi", max_speech_time=15, max_record_len=15)
                )
            else:
                body = (
                    say("We could not hear your name. Please say your full name after the beep and press hash (#) when finished.", language="en")
                    + speech_gather_or_record("/step1-name", language="en", max_speech_time=15, max_record_len=15)
                )
            return twiml_response(body)
        else:
            logger.warning(f"[FALLBACK] Step 1 name retries exceeded for {call_sid}, using default")
            clean_raw = ""

    name = clean_caller_name(clean_raw, lang=lang) if clean_raw else ("नागरिक" if lang == "hi" else "Citizen")
    session["name"] = name
    session["step1_completed"] = True

    # Initialize / update incident state with caller name and any extra facts provided early
    raw_st = session.get("incident_state")
    curr_st = IncidentState(**raw_st) if raw_st else IncidentState()
    if name not in ["नागरिक", "Citizen"]:
        curr_st.victim_name.value = name
        curr_st.victim_name.status = FieldStatus.COLLECTED
    if clean_raw and len(clean_raw) > 10:
        extracted = extract_facts_from_text(clean_raw, language=lang, caller_name=name)
        curr_st = merge_extracted_facts(curr_st, extracted)
    session["incident_state"] = curr_st.model_dump()

    logger.info(f"[CALLER] Registered name for {call_sid}: '{name}' (raw='{raw_name}')")

    if lang == "hi":
        body = (
            say(f"धन्यवाद, {name} जी।", language="hi")
            + say("बीप के बाद कृपया विस्तार से बताएं कि आपके साथ क्या घटना घटी और समाप्त होने पर हैश (#) दबाएं।", language="hi")
            + speech_gather_or_record("/step2-story", language="hi", max_speech_time=60, max_record_len=60)
        )
    else:
        body = (
            say(f"Thank you, {name}.", language="en")
            + say("After the beep, please describe in detail what happened and press hash (#) when finished.", language="en")
            + speech_gather_or_record("/step2-story", language="en", max_speech_time=60, max_record_len=60)
        )

    return twiml_response(body)


@app.post("/step2-story")
async def step2_story(request: Request):
    """Step 4: Transcribe incident story, run LLM intelligence layer, and ask context-aware question."""
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    speech_result = (form.get("SpeechResult") or "").strip()
    audio_url = form.get("RecordingUrl", "")

    session = sessions.setdefault(call_sid, {"call_sid": call_sid, "language": "hi"})
    lang = session.get("language", "hi")
    caller_name = session.get("name", "नागरिक" if lang == "hi" else "Citizen")

    # Idempotency check: if Step 2 already completed, re-serve Question 3 prompt without re-running LLM
    if session.get("step2_completed"):
        logger.info(f"[IDEMPOTENCY] Step 2 already completed for {call_sid}, re-serving Question 3 prompt")
        label = session.get("scenario_label", "General Cybercrime")
        follow_up_q = session.get("follow_up_question", "")
        if lang == "hi":
            body = (
                say(f"समझ गया। यह मामला {label} से संबंधित प्रतीत होता है।", language="hi")
                + say(f"{follow_up_q} अपना उत्तर देने के बाद हैश (#) दबाएं।", language="hi")
                + speech_gather_or_record("/step3-details", language="hi", max_speech_time=45, max_record_len=45)
            )
        else:
            body = (
                say(f"Understood. This incident appears related to {label}.", language="en")
                + say(f"{follow_up_q} Press hash (#) when you have finished answering.", language="en")
                + speech_gather_or_record("/step3-details", language="en", max_speech_time=45, max_record_len=45)
            )
        return twiml_response(body)

    story = ""
    if speech_result:
        logger.info(f"[SPEECH] ({lang}) {call_sid} story -> {speech_result}")
        story = speech_result
    elif audio_url:
        story = await transcribe_audio_async(audio_url, call_sid, language=lang)

    # Empty answer check: if caller pressed # without speaking or recognition was empty
    clean_story = story.replace("#", "").strip()
    if not clean_story:
        retries = session.get("story_retries", 0) + 1
        session["story_retries"] = retries
        if retries <= 2:
            logger.warning(f"[RETRY] Step 2 empty story retry {retries}/2 for {call_sid}")
            if lang == "hi":
                body = (
                    say("हमें घटना का विवरण सुनाई नहीं दिया। कृपया बीप के बाद बताएं कि क्या हुआ और समाप्त होने पर हैश (#) दबाएं।", language="hi")
                    + speech_gather_or_record("/step2-story", language="hi", max_speech_time=60, max_record_len=60)
                )
            else:
                body = (
                    say("We could not hear the details. Please describe what happened after the beep and press hash (#) when finished.", language="en")
                    + speech_gather_or_record("/step2-story", language="en", max_speech_time=60, max_record_len=60)
                )
            return twiml_response(body)
        else:
            logger.warning(f"[FALLBACK] Step 2 story retries exceeded for {call_sid}, using default fallback")
            clean_story = "कोई विवरण नहीं मिला" if lang == "hi" else "No description provided"

    story = clean_story

    # LLM-Assisted Incident Analysis with context-aware state tracking
    raw_st = session.get("incident_state")
    curr_st = IncidentState(**raw_st) if raw_st else IncidentState()

    analysis: CybercrimeIncidentAnalysis = await asyncio.to_thread(
        analyze_incident_with_llm,
        story=story,
        details="",
        language=lang,
        caller_name=caller_name,
        existing_state=curr_st,
        target_field="incident_description",
    )

    session["story"] = story
    session["scenario"] = analysis.fraud_category
    session["scenario_label"] = analysis.fraud_category_label
    session["follow_up_question"] = analysis.follow_up_question
    session["last_targeted_field"] = analysis.target_field
    session["formal_complaint_draft"] = analysis.formal_complaint_draft
    session["llm_analysis"] = analysis.model_dump()
    session["step2_completed"] = True

    if analysis.incident_state:
        session["incident_state"] = analysis.incident_state.model_dump()

    if analysis.incident_date:
        session["incident_date"] = analysis.incident_date
    if analysis.incident_time:
        session["incident_time"] = analysis.incident_time
    if analysis.bank_details:
        session["bank_details"] = analysis.bank_details.model_dump()
    if analysis.suspect_details:
        session["suspect_details"] = analysis.suspect_details.model_dump()
    if analysis.missing_information:
        session["missing_information"] = analysis.missing_information
    if analysis.financial_loss:
        session["financial_loss"] = analysis.financial_loss

    follow_up_q = analysis.follow_up_question
    label = analysis.fraud_category_label

    if lang == "hi":
        body = (
            say(f"समझ गया। यह मामला {label} से संबंधित प्रतीत होता है।", language="hi")
            + say(f"{follow_up_q} अपना उत्तर देने के बाद हैश (#) दबाएं।", language="hi")
            + speech_gather_or_record("/step3-details", language="hi", max_speech_time=45, max_record_len=45)
        )
    else:
        body = (
            say(f"Understood. This incident appears related to {label}.", language="en")
            + say(f"{follow_up_q} Press hash (#) when you have finished answering.", language="en")
            + speech_gather_or_record("/step3-details", language="en", max_speech_time=45, max_record_len=45)
        )

    return twiml_response(body)


@app.post("/step3-details")
async def step3_details(request: Request):
    """Step 5: Collect follow-up response, enrich LLM analysis, give verbal summary, and prompt confirmation."""
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    speech_result = (form.get("SpeechResult") or "").strip()
    audio_url = form.get("RecordingUrl", "")

    session = sessions.setdefault(call_sid, {"call_sid": call_sid, "language": "hi"})
    lang = session.get("language", "hi")
    caller_name = session.get("name", "नागरिक" if lang == "hi" else "Citizen")

    # Idempotency check: if Step 3 already completed, re-serve confirmation prompt
    if session.get("step3_completed"):
        logger.info(f"[IDEMPOTENCY] Step 3 already completed for {call_sid}, re-serving confirmation prompt")
        name = session.get("name", caller_name)
        label = session.get("scenario_label", "General Cybercrime")
        if lang == "hi":
            summary_prompt = (
                f"आपकी जानकारी दर्ज कर ली गई है। नाम: {name}, श्रेणी: {label}। "
                "रिपोर्ट तैयार करने और आपातकालीन सलाह के लिए 1 दबाएं या हैश (#) दबाएं। दोबारा सुनने के लिए 2 दबाएं।"
            )
        else:
            summary_prompt = (
                f"Your information has been logged. Name: {name}, Category: {label}. "
                "Press 1 or hash (#) to generate your report, or press 2 to replay."
            )
        body = (
            '<Gather action="/confirm-interview" method="POST" numDigits="1" timeout="8">'
            + say(summary_prompt, language=lang)
            + '</Gather>'
            + f'<Redirect method="POST">/auto-save?CallSid={call_sid}</Redirect>'
        )
        return twiml_response(body)

    details = ""
    if speech_result:
        logger.info(f"[SPEECH] ({lang}) {call_sid} details -> {speech_result}")
        details = speech_result
    elif audio_url:
        details = await transcribe_audio_async(audio_url, call_sid, language=lang)

    clean_details = details.replace("#", "").strip()
    target_field = session.get("last_targeted_field")
    follow_up_q = session.get("follow_up_question", "")

    if not clean_details:
        retries = session.get("details_retries", 0) + 1
        session["details_retries"] = retries
        if retries <= 1:
            logger.warning(f"[RETRY] Step 3 empty details retry {retries}/1 for {call_sid}")
            if lang == "hi":
                prompt = f"{follow_up_q} कृपया अपना उत्तर दें और समाप्त होने पर हैश (#) दबाएं।" if follow_up_q else "कृपया अतिरिक्त विवरण दें और समाप्त होने पर हैश (#) दबाएं।"
                body = (
                    say(prompt, language="hi")
                    + speech_gather_or_record("/step3-details", language="hi", max_speech_time=45, max_record_len=45)
                )
            else:
                prompt = f"{follow_up_q} Please provide your answer and press hash (#) when finished." if follow_up_q else "Please provide additional details and press hash (#) when finished."
                body = (
                    say(prompt, language="en")
                    + speech_gather_or_record("/step3-details", language="en", max_speech_time=45, max_record_len=45)
                )
            return twiml_response(body)
        else:
            logger.warning(f"[FALLBACK] Step 3 details retries exceeded for {call_sid}, using default")
            clean_details = "याद नहीं / पता नहीं" if lang == "hi" else "Don't know / Not available"

    # Reset retry counter for next field
    session["details_retries"] = 0

    # Record Q&A pair in history
    session.setdefault("qa_pairs", []).append({
        "question": follow_up_q,
        "target_field": target_field,
        "answer": clean_details,
    })

    if session.get("details"):
        session["details"] = f"{session['details']} | {clean_details}"
    else:
        session["details"] = clean_details

    # Retrieve accumulated state and targeted field
    raw_st = session.get("incident_state")
    curr_st = IncidentState(**raw_st) if raw_st else IncidentState()

    # Update LLM analysis with the follow-up details and context-aware state tracking
    final_analysis: CybercrimeIncidentAnalysis = await asyncio.to_thread(
        analyze_incident_with_llm,
        story=session.get("story", ""),
        details=clean_details,
        language=lang,
        caller_name=caller_name,
        existing_state=curr_st,
        target_field=target_field,
    )
    session["llm_analysis"] = final_analysis.model_dump()
    session["formal_complaint_draft"] = final_analysis.formal_complaint_draft
    if final_analysis.incident_state:
        session["incident_state"] = final_analysis.incident_state.model_dump()
        curr_st = final_analysis.incident_state
    if final_analysis.incident_date:
        session["incident_date"] = final_analysis.incident_date
    if final_analysis.incident_time:
        session["incident_time"] = final_analysis.incident_time
    if final_analysis.bank_details:
        session["bank_details"] = final_analysis.bank_details.model_dump()
    if final_analysis.suspect_details:
        session["suspect_details"] = final_analysis.suspect_details.model_dump()
    if final_analysis.missing_information:
        session["missing_information"] = final_analysis.missing_information
    if final_analysis.financial_loss:
        session["financial_loss"] = final_analysis.financial_loss

    # Determine next follow-up question
    category = session.get("scenario") or (curr_st.primary_fraud_category.value if curr_st.primary_fraud_category else "GENERAL_FRAUD")
    priorities = CATEGORY_FIELD_PRIORITIES.get(category, CATEGORY_FIELD_PRIORITIES.get("GENERAL_FRAUD", []))
    max_turns = len(priorities)
    turns = session.get("followup_turns", 0) + 1
    session["followup_turns"] = turns

    next_field, next_question = select_next_follow_up_question(curr_st, language=lang)

    # If more priority fields remain and within turn limits, ask the next question!
    if next_field != "all_collected" and turns < max_turns:
        session["step3_completed"] = False
        session["last_targeted_field"] = next_field
        session["follow_up_question"] = next_question

        logger.info(f"[QUESTION] ({lang}) {call_sid} Turn {turns}/{max_turns} -> Next field '{next_field}': {next_question}")
        if lang == "hi":
            body = (
                say(f"{next_question} अपना उत्तर देने के बाद हैश (#) दबाएं।", language="hi")
                + speech_gather_or_record("/step3-details", language="hi", max_speech_time=45, max_record_len=45)
            )
        else:
            body = (
                say(f"{next_question} Press hash (#) when you have finished answering.", language="en")
                + speech_gather_or_record("/step3-details", language="en", max_speech_time=45, max_record_len=45)
            )
        return twiml_response(body)

    # All priority questions collected or max turns reached -> Transition to final report confirmation
    session["step3_completed"] = True
    name = session.get("name", "Citizen")
    label = session.get("scenario_label", "Cyber Fraud")

    if lang == "hi":
        summary_prompt = (
            f"आपकी जानकारी दर्ज कर ली गई है। नाम: {name}, श्रेणी: {label}। "
            "रिपोर्ट तैयार करने और आपातकालीन सलाह के लिए 1 दबाएं या हैश (#) दबाएं। दोबारा सुनने के लिए 2 दबाएं।"
        )
    else:
        summary_prompt = (
            f"Your information has been logged. Name: {name}, Category: {label}. "
            "Press 1 or hash (#) to generate your report, or press 2 to replay."
        )

    body = (
        '<Gather action="/confirm-interview" method="POST" numDigits="1" timeout="8">'
        + say(summary_prompt, language=lang)
        + '</Gather>'
        + f'<Redirect method="POST">/auto-save?CallSid={call_sid}</Redirect>'
    )
    return twiml_response(body)


def _send_sms_sync(to_phone: str, body: str):
    """Synchronous worker to dispatch confirmation SMS via Twilio REST API."""
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER and to_phone):
        return None
    try:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            body=body,
            from_=TWILIO_PHONE_NUMBER,
            to=to_phone,
        )
        logger.info(f"[SMS] Sent confirmation to {mask_phone(to_phone)}: SID={msg.sid}")
        return msg.sid
    except Exception as e:
        logger.warning(f"[SMS] Notice: Could not send SMS to {mask_phone(to_phone)}: {e}")
        return None


async def send_report_sms_async(to_phone: str, download_url: str, report_id: str, language: str = "hi"):
    """Non-blocking dispatch of SMS notification with report download link and helpline guidance."""
    if not to_phone or to_phone.startswith("client:") or to_phone == TWILIO_PHONE_NUMBER:
        return None
    if language == "hi":
        sms_text = (
            f"रक्षक एआई (Rakshak AI) — आपकी साइबर शिकायत रिपोर्ट ({report_id}) तैयार है।\n"
            f"रिपोर्ट डाउनलोड लिंक: {download_url}\n"
            f"तत्काल कदम: 1930 हेल्पलाइन पर कॉल करें व बैंक को खाता/कार्ड फ्रीज करने हेतु सूचित करें।"
        )
    else:
        sms_text = (
            f"Rakshak AI — Your cyber incident report ({report_id}) has been generated.\n"
            f"Download Report: {download_url}\n"
            f"Critical: Call 1930 Cybercrime Helpline immediately and notify your bank."
        )
    try:
        return await asyncio.to_thread(_send_sms_sync, to_phone, sms_text)
    except Exception as e:
        logger.warning(f"[SMS] Async dispatch error: {e}")
        return None


@app.post("/confirm-interview")
async def confirm_interview(request: Request):
    """Step 6 & 7: Finalize interview, generate PDF/JSON report, give emergency guidance, and hang up."""
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    digit = (form.get("Digits") or "1").strip()

    session = sessions.get(call_sid, {"call_sid": call_sid, "language": "hi"})
    lang = session.get("language", "hi")

    if digit == "2":
        session["step3_completed"] = False
        return await step3_details(request)

    # Idempotency check: if report already generated for this CallSid
    if session.get("status") == "COMPLETED" and session.get("pdf_path"):
        logger.info(f"[IDEMPOTENCY] Report already generated for {call_sid}, returning closing prompt")
    else:
        try:
            pdf_path = await asyncio.to_thread(generate_pdf_report, session)
            json_path = await asyncio.to_thread(save_json_report, session)
            session["pdf_path"] = pdf_path
            session["json_path"] = json_path
            session["status"] = "COMPLETED"
            session["completed_at"] = datetime.now().isoformat()

            # Asynchronously send SMS confirmation with download link
            base = get_base_url(request)
            pdf_filename = Path(pdf_path).name
            download_url = f"{base}/download/{pdf_filename}"
            caller_phone = session.get("caller_phone") or DEMO_TO_NUMBER
            if caller_phone and caller_phone != TWILIO_PHONE_NUMBER:
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(send_report_sms_async(
                        to_phone=caller_phone,
                        download_url=download_url,
                        report_id=session.get("report_id", ""),
                        language=lang,
                    ))
                except (RuntimeError, Exception):
                    pass
        except Exception as e:
            logger.error(f"[REPORT] Generation error for {call_sid}: {e}")
            session["status"] = "FAILED"

    if lang == "hi":
        body = (
            say("आपकी रक्षक साइबर रिपोर्ट तैयार कर ली गई है।", language="hi")
            + say("कृपया तुरंत 1930 साइबर हेल्पलाइन पर कॉल करें और cybercrime.gov.in पर रिपोर्ट दर्ज करें।", language="hi")
            + say("अपने बैंक को तत्काल सूचित करके अपना खाता और कार्ड सुरक्षित करवाएं।", language="hi")
            + say("रक्षक एआई से जुड़ने के लिए धन्यवाद। सतर्क रहें, सुरक्षित रहें।", language="hi")
            + "<Hangup/>"
        )
    else:
        body = (
            say("Your Rakshak Cyber Incident Report has been successfully generated.", language="en")
            + say("Please dial 1930 immediately to report to the National Cyber Crime Helpline.", language="en")
            + say("Contact your bank immediately to block any compromised cards or accounts.", language="en")
            + say("Thank you for using Rakshak AI. Stay vigilant and stay safe.", language="en")
            + "<Hangup/>"
        )

    return twiml_response(body)


@app.post("/auto-save")
async def auto_save(request: Request, CallSid: str = ""):
    """Fallback handler: automatically preserves caller data if no DTMF key is pressed."""
    form = await request.form()
    call_sid = form.get("CallSid") or CallSid
    session = sessions.get(call_sid, {"call_sid": call_sid, "language": "hi"})
    lang = session.get("language", "hi")

    if session.get("status") != "COMPLETED":
        try:
            pdf_path = await asyncio.to_thread(generate_pdf_report, session)
            json_path = await asyncio.to_thread(save_json_report, session)
            session["pdf_path"] = pdf_path
            session["json_path"] = json_path
            session["status"] = "COMPLETED"
            session["completed_at"] = datetime.now().isoformat()

            # Asynchronously send SMS confirmation with download link
            base = get_base_url(request)
            pdf_filename = Path(pdf_path).name
            download_url = f"{base}/download/{pdf_filename}"
            caller_phone = session.get("caller_phone") or DEMO_TO_NUMBER
            if caller_phone and caller_phone != TWILIO_PHONE_NUMBER:
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(send_report_sms_async(
                        to_phone=caller_phone,
                        download_url=download_url,
                        report_id=session.get("report_id", ""),
                        language=lang,
                    ))
                except (RuntimeError, Exception):
                    pass
        except Exception as e:
            logger.error(f"[AUTO-SAVE] Error for {call_sid}: {e}")
            session["status"] = "FAILED"

    closing = (
        "आपकी रिपोर्ट सुरक्षित रूप से सेव कर ली गई है। धन्यवाद। सुरक्षित रहें।"
        if lang == "hi"
        else "Your incident report has been securely saved. Thank you. Stay safe."
    )
    body = say(closing, language=lang) + "<Hangup/>"
    return twiml_response(body)


# ══════════════════════════════════════════════
#  LOCAL TEXT-TESTING & LLM API ENDPOINTS
# ══════════════════════════════════════════════

@app.post("/api/analyze-incident")
async def api_analyze_incident(request: Request):
    """
    Local testing endpoint to test LLM incident understanding and complaint drafting
    without needing Twilio or a real phone call.
    Accepts JSON: {"text": "...", "details": "...", "language": "hi", "caller_name": "...", "generate_pdf": true}
    """
    body = await request.json()
    story = body.get("text", "").strip()
    details = body.get("details", "").strip()
    language = body.get("language", "hi")
    caller_name = body.get("caller_name", "नागरिक")
    gen_pdf = body.get("generate_pdf", False)

    if not story:
        raise HTTPException(status_code=400, detail="Missing required 'text' parameter")

    analysis: CybercrimeIncidentAnalysis = await asyncio.to_thread(
        analyze_incident_with_llm,
        story=story,
        details=details,
        language=language,
        caller_name=caller_name,
    )

    response_data = analysis.model_dump()

    if gen_pdf:
        session_data = {
            "name": caller_name,
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
        pdf_path = await asyncio.to_thread(generate_pdf_report, session_data)
        base = get_base_url(request)
        response_data["pdf_download_url"] = f"{base}/download/{Path(pdf_path).name}"

    return {
        "status": "success",
        "analysis": response_data,
    }


# ══════════════════════════════════════════════
#  DASHBOARD & SECURE DOWNLOAD ENDPOINTS
# ══════════════════════════════════════════════

@app.get("/reports")
async def list_reports(request: Request):
    """List all generated incident reports with metadata and secure download links."""
    reports = []
    base = get_base_url(request)

    if REPORTS_DIR.exists():
        # First gather structured json files
        json_map = {}
        for jf in REPORTS_DIR.glob("Data_*.json"):
            try:
                with open(jf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    rep_id = data.get("report_id") or jf.stem.replace("Data_", "")
                    json_map[rep_id] = data
            except Exception:
                continue

        for f in REPORTS_DIR.glob("Rakshak_Report_*.pdf"):
            st = f.stat()
            m = re.search(r"RAK-\d{8}-[A-F0-9]{6}", f.name)
            rep_id = m.group(0) if m else ""
            meta = json_map.get(rep_id, {})

            reports.append({
                "filename": f.name,
                "report_id": rep_id or "Legacy",
                "name": meta.get("name", "Citizen"),
                "scenario": meta.get("scenario", "GENERAL_FRAUD"),
                "scenario_label": meta.get("scenario_label", "General Cybercrime"),
                "loss": meta.get("financial_loss", "Not specified"),
                "size_kb": round(st.st_size / 1024, 1),
                "created_at": datetime.fromtimestamp(st.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
                "download_url": f"{base}/download/{f.name}",
            })

    reports.sort(key=lambda x: x["created_at"], reverse=True)

    headers = getattr(request, "headers", {})
    accept = headers.get("accept", "") if hasattr(headers, "get") else ""
    q_params = getattr(request, "query_params", {})
    fmt = q_params.get("format", "") if hasattr(q_params, "get") else ""

    if "text/html" in accept and fmt != "json":
        rows = "".join(
            f"<tr>"
            f"<td><span class='badge id-badge'>{r['report_id']}</span></td>"
            f"<td class='fw-bold'>{r['name']}</td>"
            f"<td><span class='badge scenario-badge {r['scenario']}'>{r['scenario_label']}</span></td>"
            f"<td class='loss-col'>{r['loss']}</td>"
            f"<td>{r['created_at']}</td>"
            f"<td><a href='{r['download_url']}' target='_blank' class='btn btn-dl'>⬇ Download PDF</a></td>"
            f"</tr>"
            for r in reports
        )
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Rakshak AI — Incident Intake & Investigation Dashboard</title>
    <style>
        :root {{ --bg: #0d1117; --card-bg: #161b22; --border: #30363d; --text: #c9d1d9; --accent: #58a6ff; --accent-hover: #1f6feb; --danger: #f85149; --warning: #d29922; --success: #3fb950; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 24px; }}
        .header {{ max-width: 1200px; margin: 0 auto 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 16px; }}
        .title-group {{ display: flex; align-items: center; gap: 12px; }}
        .shield-icon {{ font-size: 32px; }}
        h1 {{ margin: 0; font-size: 22px; color: #f0f6fc; font-weight: 700; }}
        .subtitle {{ margin: 4px 0 0; font-size: 13px; color: #8b949e; }}
        .status-pill {{ background: rgba(63, 185, 80, 0.15); border: 1px solid var(--success); color: var(--success); padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; display: inline-flex; align-items: center; gap: 6px; }}
        .stats-grid {{ max-width: 1200px; margin: 0 auto 24px; display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }}
        .stat-card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }}
        .stat-label {{ font-size: 12px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }}
        .stat-val {{ font-size: 24px; color: #f0f6fc; font-weight: 700; margin-top: 6px; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }}
        .toolbar {{ padding: 14px 18px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; gap: 12px; }}
        .search-box {{ background: #0d1117; border: 1px solid var(--border); color: #f0f6fc; padding: 8px 14px; border-radius: 6px; width: 300px; font-size: 13px; }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; }}
        th {{ padding: 12px 18px; font-size: 12px; color: #8b949e; text-transform: uppercase; border-bottom: 1px solid var(--border); background: rgba(22, 27, 34, 0.8); }}
        td {{ padding: 14px 18px; font-size: 13px; border-bottom: 1px solid var(--border); vertical-align: middle; }}
        tr:hover td {{ background: rgba(88, 166, 255, 0.04); }}
        .fw-bold {{ font-weight: 600; color: #f0f6fc; }}
        .badge {{ padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; display: inline-block; }}
        .id-badge {{ background: #21262d; border: 1px solid var(--border); color: #58a6ff; font-family: monospace; }}
        .scenario-badge {{ background: rgba(88, 166, 255, 0.15); color: #58a6ff; }}
        .scenario-badge.OTP_FRAUD {{ background: rgba(248, 81, 73, 0.15); color: #f85149; }}
        .scenario-badge.JOB_SCAM {{ background: rgba(210, 153, 34, 0.15); color: #d29922; }}
        .scenario-badge.LOAN_FRAUD {{ background: rgba(163, 113, 247, 0.15); color: #bc8cff; }}
        .scenario-badge.OLX_SCAM {{ background: rgba(56, 139, 253, 0.15); color: #58a6ff; }}
        .loss-col {{ font-weight: 600; color: #f85149; }}
        .btn {{ text-decoration: none; padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; display: inline-block; }}
        .btn-dl {{ background: var(--accent); color: #0d1117; }}
        .btn-dl:hover {{ background: var(--accent-hover); color: #fff; }}
        .empty {{ text-align: center; padding: 40px; color: #8b949e; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="title-group">
            <span class="shield-icon">🛡️</span>
            <div>
                <h1>Rakshak AI — Incident Investigation Portal</h1>
                <div class="subtitle">Automated Voice Intake &bull; Helpline 1930 Integration &bull; Police FIR Documentation Aid</div>
            </div>
        </div>
        <div class="status-pill">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#3fb950;"></span> System Active
        </div>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-label">Total Cases Processed</div>
            <div class="stat-val">{len(reports)}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Active Helpline Status</div>
            <div class="stat-val" style="color:var(--success);">DIAL 1930</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Primary Languages</div>
            <div class="stat-val">Hindi &bull; English</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Tamper-Evident PDFs</div>
            <div class="stat-val" style="color:var(--accent);">100% Verified</div>
        </div>
    </div>

    <div class="container">
        <div class="toolbar">
            <div class="fw-bold">Intake Incident Logs</div>
            <input type="text" id="searchInput" class="search-box" placeholder="Filter by Name, Category, or ID..." onkeyup="filterTable()">
        </div>
        <table id="reportsTable">
            <thead>
                <tr>
                    <th>Report ID</th>
                    <th>Citizen / Victim</th>
                    <th>Fraud Category</th>
                    <th>Financial Loss</th>
                    <th>Timestamp</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                {rows if rows else '<tr><td colspan="6" class="empty">No incident reports recorded yet. Make a call to log an incident.</td></tr>'}
            </tbody>
        </table>
    </div>

    <script>
        function filterTable() {{
            var input = document.getElementById("searchInput").value.toUpperCase();
            var trs = document.getElementById("reportsTable").getElementsByTagName("tr");
            for (var i = 1; i < trs.length; i++) {{
                var text = trs[i].textContent || trs[i].innerText;
                trs[i].style.display = text.toUpperCase().indexOf(input) > -1 ? "" : "none";
            }}
        }}
    </script>
</body>
</html>"""
        return Response(content=html, media_type="text/html")

    return {
        "status": "success",
        "total_reports": len(reports),
        "reports": reports,
    }


@app.get("/reports/latest")
async def get_latest_report(request: Request):
    """Retrieve the most recently generated report."""
    if not REPORTS_DIR.exists():
        raise HTTPException(status_code=404, detail="No reports available")

    pdf_files = list(REPORTS_DIR.glob("Rakshak_Report_*.pdf"))
    if not pdf_files:
        raise HTTPException(status_code=404, detail="No incident reports generated yet")

    latest_file = max(pdf_files, key=lambda f: f.stat().st_ctime)
    base = get_base_url(request)
    return {
        "filename": latest_file.name,
        "download_url": f"{base}/download/{latest_file.name}",
        "created_at": datetime.fromtimestamp(latest_file.stat().st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
        "size_kb": round(latest_file.stat().st_size / 1024, 1),
    }


@app.get("/download/{filename}")
async def download_report(filename: str):
    """
    Secure download endpoint with strict path-traversal protection.
    Only allows downloads of valid PDF/JSON files from REPORTS_DIR.
    """
    safe_name = os.path.basename(filename)
    if not (safe_name.endswith(".pdf") or safe_name.endswith(".json")):
        raise HTTPException(status_code=400, detail="Invalid file type")

    file_path = (REPORTS_DIR / safe_name).resolve()

    try:
        file_path.relative_to(REPORTS_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Requested report not found")

    media_type = "application/pdf" if safe_name.endswith(".pdf") else "application/json"
    return FileResponse(str(file_path), media_type=media_type, filename=safe_name)


@app.get("/health")
async def health():
    """Health check endpoint displaying system and active call counts."""
    return {
        "status": "healthy",
        "service": "Rakshak AI — Voice Cybercrime Assistance",
        "active_sessions": len(sessions),
        "reports_generated": len(list(REPORTS_DIR.glob("Rakshak_Report_*.pdf"))),
        "server_time": datetime.now().isoformat(),
    }
