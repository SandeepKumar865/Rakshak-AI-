"""
Rakshak AI — System Architecture & Tech Stack PDF Document Generator
Generates a comprehensive, professional, multi-page PDF specification document.
"""

import sys
from pathlib import Path
from datetime import datetime
from fpdf import FPDF

BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"
FONTS_DIR = BASE_DIR / "fonts"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)

FONT_HI = str(FONTS_DIR / "NotoSansDevanagari-Regular.ttf")
FONT_HI_B = str(FONTS_DIR / "NotoSansDevanagari-Bold.ttf")
FONT_EN = str(FONTS_DIR / "NotoSans-Regular.ttf")


class TechSpecPDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("NotoSans", "", 8)
            self.set_text_color(100, 110, 130)
            self.cell(0, 6, "RAKSHAK AI — SYSTEM ARCHITECTURE & TECH STACK SPECIFICATION", align="L")
            self.cell(0, 6, f"v2.1.0 | {datetime.now().strftime('%B %Y')}", align="R", new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(0, 150, 180)
            self.set_line_width(0.3)
            self.line(10, 16, 200, 16)
            self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_draw_color(210, 215, 225)
        self.set_line_width(0.2)
        self.line(10, 282, 200, 282)
        self.set_font("NotoSans", "", 8)
        self.set_text_color(120, 130, 145)
        self.cell(100, 10, "Rakshak AI Project Specification — Confidential & Technical Reference", align="L")
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="R")


def build_tech_spec_pdf() -> str:
    pdf = TechSpecPDF()
    pdf.add_font("Devanagari", "", FONT_HI)
    pdf.add_font("Devanagari", "B", FONT_HI_B)
    pdf.add_font("NotoSans", "", FONT_EN)
    pdf.set_fallback_fonts(["NotoSans", "Devanagari"])
    pdf.set_auto_page_break(auto=True, margin=18)

    # ══════════════════════════════════════════════
    #  PAGE 1: COVER & EXECUTIVE OVERVIEW
    # ══════════════════════════════════════════════
    pdf.add_page()

    # Title Banner Box
    pdf.set_fill_color(10, 25, 70)  # Navy
    pdf.rect(0, 0, 210, 42, "F")
    pdf.set_y(8)
    pdf.set_text_color(0, 215, 225)  # Cyan
    pdf.set_font("NotoSans", "", 20)
    pdf.cell(0, 9, "RAKSHAK AI (रक्षक एआई)", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(255, 255, 255)
    pdf.set_font("NotoSans", "", 11)
    pdf.cell(0, 7, "Voice-First Cybercrime First Responder & Automated Reporting System", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(180, 210, 230)
    pdf.set_font("NotoSans", "", 8.5)
    pdf.cell(0, 5, "TECHNICAL ARCHITECTURE & SPECIFICATION DOCUMENT | VERSION 2.1.0", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # Metadata Box
    pdf.set_fill_color(240, 248, 255)
    pdf.set_draw_color(0, 150, 180)
    pdf.set_line_width(0.3)
    box_y = pdf.get_y()
    pdf.rect(10, box_y, 190, 32, "FD")
    pdf.set_xy(14, box_y + 2)

    def meta_row(k: str, v: str):
        pdf.set_x(14)
        pdf.set_font("NotoSans", "", 9)
        pdf.set_text_color(10, 25, 70)
        pdf.cell(50, 5.2, k + ":", border=0)
        pdf.set_font("NotoSans", "", 9)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(0, 5.2, v, new_x="LMARGIN", new_y="NEXT")

    meta_row("Document Title", "Rakshak AI Architecture & Tech Stack Reference")
    meta_row("Document ID", f"SPEC-RAKSHAK-{datetime.now().strftime('%Y%m%d')}-V2")
    meta_row("Core Functionality", "Automated bilingual telephony intake, LLM entity extraction & official report generation")
    meta_row("Target Audience", "Technical Architects, Law Enforcement Tech Teams, Systems Integrators")
    meta_row("Publication Date", datetime.now().strftime("%d %B %Y, %I:%M %p IST"))

    pdf.set_y(box_y + 36)

    # Section 1: Executive Summary
    def section_header(title: str):
        pdf.ln(3)
        pdf.set_fill_color(10, 25, 70)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("NotoSans", "", 10.5)
        pdf.cell(0, 6.5, f"  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    section_header("1. EXECUTIVE SUMMARY & PROBLEM STATEMENT")
    pdf.set_font("NotoSans", "", 9)
    pdf.set_text_color(35, 35, 35)
    summary_text = (
        "In India, cyber financial fraud has grown exponentially. When a victim is defrauded (via OTP theft, fake KYC, "
        "OLX QR scams, fake jobs, or extortion loan apps), the first 2-4 hours ('The Golden Hour') are paramount to freeze "
        "stolen funds before multi-layer money mule transfers take place. However, victims encounter severely congested lines "
        "on Helpline 1930, complex English-heavy portal forms at cybercrime.gov.in, panic, and lack of immediate guidance.\n\n"
        "Rakshak AI addresses this national challenge by providing an autonomous, 24/7 AI-driven telephone assistance "
        "gateway. The system answers or dials victims, conducts natural voice interviews in Hindi or English, extracts structured "
        "evidentiary particulars (loss amounts, bank details, transaction UTRs, criminal phone/UPI IDs), drafts a formal complaint narrative, "
        "and immediately outputs official, tamper-evident PDF/JSON reports ready for police and banking escalation."
    )
    pdf.multi_cell(190, 4.8, summary_text)

    # Section 2: Key Capabilities
    section_header("2. CORE SYSTEM CAPABILITIES")
    capabilities = (
        "• Bilingual Voice Pipeline: Fully natural Hindi (hi-IN) and English (en-IN) telephony using Amazon Polly Neural TTS.\n"
        "• Automated Incident Understanding: Contextual classification into OTP Fraud, OLX Scam, Job Scam, Loan Fraud, or Phishing.\n"
        "• Structured Evidence Extraction: Extracts incident date/time, victim bank/branch/account, scammer phone, UPI ID, email, and amount.\n"
        "• Intelligent Dynamic Follow-up: Identifies missing evidentiary gaps and generates single, focused follow-up voice questions.\n"
        "• Formal Complaint Draft: Formats citizen statements into official narratives for cybercrime.gov.in and cyber police stations.\n"
        "• Privacy & Credential Redaction: Automatically masks passwords, OTPs, PINs, and displays masked account numbers (XXXX6789).\n"
        "• Dual-Engine Resilience: Operates on Google Gemini 1.5 Flash / OpenAI, with an instant 100% offline deterministic fallback."
    )
    pdf.set_font("NotoSans", "", 8.8)
    pdf.multi_cell(190, 4.6, capabilities)

    # ══════════════════════════════════════════════
    #  PAGE 2: COMPLETE TECH STACK SPECIFICATION
    # ══════════════════════════════════════════════
    pdf.add_page()
    section_header("3. COMPLETE TECHNOLOGY STACK MATRIX")

    # Table Header
    pdf.set_fill_color(220, 235, 245)
    pdf.set_draw_color(180, 200, 220)
    pdf.set_font("NotoSans", "", 8.5)
    pdf.set_text_color(10, 25, 70)
    pdf.cell(38, 6.5, " Layer / Module", border=1, fill=True)
    pdf.cell(48, 6.5, " Technology & Version", border=1, fill=True)
    pdf.cell(104, 6.5, " Purpose & Architecture Functionality", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    tech_stack = [
        ("Backend Framework", "FastAPI (v0.111.0)\nPython 3.14 / 3.13", "Asynchronous HTTP routing, telephony webhook orchestration, download APIs."),
        ("ASGI Web Server", "Uvicorn (v0.29.0)", "High-throughput asynchronous server running on 0.0.0.0:8000."),
        ("Telephony Cloud", "Twilio Voice API (v9.0.4)\nTwiML XML Protocol", "Handles inbound calls, outbound call dispatching, DTMF gather, and recording."),
        ("Text-to-Speech (TTS)", "Amazon Polly via Twilio\n(Voice: Polly.Aditi)", "Neural speech synthesis for fluent Indian English (en-IN) and natural Hindi (hi-IN)."),
        ("Speech-to-Text (STT)", "SpeechRecognition (v3.10.4)\n+ Google Web Speech", "Converts caller recordings into Devanagari Hindi and English transcripts."),
        ("Audio Transcoding", "Pydub (v0.25.1) +\nstandard-aifc + audioop-lts", "Transcodes Twilio raw audio into 16 kHz 16-bit mono PCM WAV for accurate STT."),
        ("LLM Intelligence", "Google Gemini 1.5 Flash\n/ OpenAI GPT-4o-mini", "Understands incident narrative, categorizes fraud, and generates follow-up prompts."),
        ("Data Validation", "Pydantic v2 (BaseModel, Field)", "Strict schema validation enforcing structured JSON outputs for incident metadata."),
        ("Offline NLP Fallback", "Deterministic Rule Engine\n(Regex & Heuristic Parsers)", "100% offline fallback when API keys are absent, guaranteeing zero call drop."),
        ("Document Engine", "FPDF2 (v2.7.9)\n+ Google Noto Sans Fonts", "Generates bilingual, tamper-evident PDF reports with Devanagari & Latin glyphs."),
        ("Public Ingress", "Cloudflare Tunnel (cloudflared)\nProtocol HTTP/2", "Zero-trust secure public HTTPS reverse proxy directing Twilio webhooks to localhost."),
        ("Testing Suite", "Pytest (v9.1.1)\npytest-asyncio, HTTPX TestClient", "37 automated unit and integration tests verifying routing, NLP, and generation."),
    ]

    pdf.set_font("NotoSans", "", 8)
    pdf.set_text_color(30, 30, 30)
    for layer, tech, purpose in tech_stack:
        # Calculate heights
        x_start = pdf.get_x()
        y_start = pdf.get_y()
        pdf.cell(38, 11, f" {layer}", border=1)
        pdf.set_xy(x_start + 38, y_start)
        pdf.multi_cell(48, 5.5, tech, border=1)
        pdf.set_xy(x_start + 86, y_start)
        pdf.multi_cell(104, 5.5, purpose, border=1)
        pdf.set_y(y_start + 11)

    pdf.ln(3)

    # ══════════════════════════════════════════════
    #  PAGE 3: SYSTEM ARCHITECTURE & DATA FLOW
    # ══════════════════════════════════════════════
    section_header("4. 5-TIER SYSTEM ARCHITECTURE MODEL")
    pdf.set_font("NotoSans", "", 8.5)
    pdf.set_text_color(35, 35, 35)

    arch_layers = [
        ("Tier 1: Telephony & Voice Edge Layer", (
            "• Twilio Voice Cloud initiates or accepts PSTN/cellular phone calls.\n"
            "• Renders neural bilingual speech via Polly.Aditi.\n"
            "• Collects DTMF tones (1 for Hindi, 2 for English) and voice recordings."
        )),
        ("Tier 2: Secure Public Ingress & Tunneling", (
            "• Cloudflare Tunnel (cloudflared) provides encrypted HTTPS ingress.\n"
            "• Eliminates the need for public IP addresses or router port forwarding.\n"
            "• Dynamically provisions secure endpoints for webhook routing."
        )),
        ("Tier 3: Core Application & Voice State Machine (main.py)", (
            "• FastAPI ASGI backend orchestrates the state machine across 7 steps.\n"
            "• Asynchronous thread pool isolates audio downloading and transcoding.\n"
            "• Maintains in-memory session states strictly isolated by CallSid."
        )),
        ("Tier 4: LLM Incident Intelligence Layer (llm_analyzer.py)", (
            "• Primary Engine: Google Gemini 1.5 Flash generates structured JSON.\n"
            "• Extracts: incident date/time, bank name/branch/A/C, and suspect phone/name/UPI/email.\n"
            "• Secondary Engine: Deterministic offline regex/NLP parser ensures 100% uptime."
        )),
        ("Tier 5: Evidence Preservation & Report Dissemination", (
            "• FPDF2 renders bilingual, tamper-evident PDF incident reports.\n"
            "• Exports machine-readable case records (Data_RAK-XXXX.json).\n"
            "• Serves secure report downloads with strict path-traversal validation."
        )),
    ]

    for title, desc in arch_layers:
        pdf.set_fill_color(240, 245, 252)
        pdf.set_draw_color(180, 200, 220)
        pdf.set_font("NotoSans", "", 9)
        pdf.set_text_color(10, 25, 70)
        pdf.cell(0, 5.5, f"  {title}", fill=True, border=1, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("NotoSans", "", 8)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(190, 4.4, desc, border="LRB")
        pdf.ln(1.5)

    # ══════════════════════════════════════════════
    #  PAGE 4: CALL LIFECYCLE & SECURITY ARCHITECTURE
    # ══════════════════════════════════════════════
    pdf.add_page()
    section_header("5. VOICE INTERACTION LIFECYCLE (STATE MACHINE)")

    steps = [
        ("Step 1: Greeting & Language Select", "Plays bilingual greeting. <Gather> collects DTMF (1=Hindi, 2=English). Falls back to Hindi on timeout."),
        ("Step 2: Caller Name Ingestion", "Prompts citizen for full name. Records up to 10 seconds. Transcribes via Google STT."),
        ("Step 3: Narrative Audio Intake", "Prompts victim to describe the incident in detail (45 seconds). Audio converted to 16kHz PCM WAV."),
        ("Step 4: AI Analysis & Targeted Follow-Up", "LLM classifies fraud, checks missing evidence, and speaks a targeted follow-up question."),
        ("Step 5: Follow-Up Response Intake", "Victim answers with bank details, criminal details, date/time. LLM updates incident schema."),
        ("Step 6: Verbal Confirmation", "System speaks summary (Name, Category). Caller presses 1 to confirm or 2 to replay."),
        ("Step 7: Report Generation & Advisory", "Generates PDF and JSON reports. Speaks emergency guidance (Call 1930 / Freeze Account) and hangs up."),
    ]

    pdf.set_font("NotoSans", "", 8)
    for s_title, s_desc in steps:
        pdf.set_text_color(10, 25, 70)
        pdf.cell(55, 5, s_title + ":", border=0)
        pdf.set_text_color(35, 35, 35)
        pdf.multi_cell(135, 5, s_desc, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    section_header("6. SECURITY, PRIVACY & LEGAL SAFEGUARDS")
    security_points = (
        "1. Credential Sanitization: Automatic regex sanitization redacts active OTPs, PINs, CVVs, and passwords into '[REDACTED]'.\n"
        "2. Payment Card Redaction: Full 16-digit debit/credit card numbers are masked as '[CARD REDACTED]'.\n"
        "3. Bank Account Masking: Victim bank accounts are displayed in masked format (e.g. 'XXXX6789') in citizen documents.\n"
        "4. Telephony Session Isolation: Every call session is isolated by its unique Twilio CallSid in memory; no cross-contamination.\n"
        "5. Secure Path-Traversal Protection: Download routes enforce strict filesystem boundary checks; directory traversal is blocked.\n"
        "6. Statutory Non-FIR Legal Disclaimer: Prominently states that Rakshak AI is an intake documentation assistant, not an official FIR."
    )
    pdf.set_font("NotoSans", "", 8.5)
    pdf.set_text_color(35, 35, 35)
    pdf.multi_cell(190, 4.6, security_points)

    section_header("7. PROJECT DIRECTORY & MODULE LAYOUT")
    dir_layout = (
        "cyberAgent-main/\n"
        "  |-- main.py               # FastAPI backend, Twilio webhooks, STT transcoding, PDF generator\n"
        "  |-- llm_analyzer.py       # Pydantic schemas, Gemini/OpenAI orchestrator, offline heuristic NLP engine\n"
        "  |-- config.py             # Secure configuration, .env loader, phone & secret masking utilities\n"
        "  |-- call_me.py            # Outbound call trigger script for automated live demo testing\n"
        "  |-- test_llm.py           # Standalone CLI tool to evaluate LLM analysis & PDF generation offline\n"
        "  |-- requirements.txt      # Python dependencies with pinned versions\n"
        "  |-- fonts/                # Devanagari and Latin Google Noto Sans TrueType fonts\n"
        "  |-- reports/              # Storage directory for Data_*.json records & Rakshak_Report_*.pdf files\n"
        "  |-- temp/                 # Temporary directory for converted 16kHz PCM audio files\n"
        "  `-- tests/                # 37 automated unit and integration tests (test_llm_intelligence, test_workflow)"
    )
    pdf.set_font("NotoSans", "", 7.8)
    pdf.set_fill_color(248, 250, 253)
    pdf.set_draw_color(200, 210, 225)
    pdf.rect(10, pdf.get_y(), 190, 48, "FD")
    pdf.set_xy(13, pdf.get_y() + 2)
    pdf.set_text_color(20, 30, 50)
    pdf.multi_cell(184, 4.2, dir_layout)

    # Output to reports directory
    output_filename = "Rakshak_AI_TechStack_and_Architecture.pdf"
    output_path = REPORTS_DIR / output_filename
    pdf.output(str(output_path))
    print(f"[SUCCESS] PDF generated at: {output_path}")
    return str(output_path)


if __name__ == "__main__":
    build_tech_spec_pdf()
