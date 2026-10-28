# Rakshak AI — Voice-Based Cybercrime Assistance & Reporting System

Rakshak AI is an AI-powered interactive voice agent (IVR) designed to act as a first responder for cybercrime reporting in India. Victims of cyber fraud can report incidents over a regular phone call in **Hindi or English**. Rakshak AI records statements, transcribes them using speech recognition, classifies the fraud category, asks targeted follow-up questions, gives emergency legal/financial guidance (Helpline 1930, bank account freeze instructions), and automatically compiles an official bilingual PDF investigation report.

---

## Architecture & Call Flow

```
[Citizen Phone]
      │
      ▼  (Voice Call)
[Twilio Programmable Voice]
      │
      ▼  (HTTP Webhook)
[FastAPI Backend (Uvicorn)] ───► [Speech-to-Text (hi-IN / en-IN)]
      │                                       │
      ▼                                       ▼
[DTMF Language Menu (1: Hindi, 2: English)]  [Incident Intelligence Classifier]
      │                                       │
      ▼                                       ▼
[Voice Narrative & Follow-Up Intake] ───────► [Auto PDF & JSON Generation]
      │                                               │
      ▼                                               ▼
[Delivery Selection Menu] ────────────────► [Secure Access Token Engine]
      │                                               │
      ├─► [1: SMS Link via Twilio] ───────────────────┤
      ├─► [2: WhatsApp Link via Sandbox] ─────────────┤
      └─► [3: Decline Link / Dashboard Only] ─────────▼
                                   [Secure Citizen Access (/report/access/{token})]
```

---

## Prerequisites (Windows)

- **Python 3.9+** (Tested on Python 3.10 through Python 3.14)
- **Twilio Account** ([twilio.com](https://console.twilio.com))
- **Cloudflare Tunnel** (`cloudflared`) or **ngrok**
- **FFmpeg** (for audio re-encoding and speech processing)

---

## Step-by-Step Setup Guide for Windows

### Step 1: Clone or Navigate to the Project

Open PowerShell in the project directory:
```powershell
cd C:\Users\Deii\Downloads\cyberAgent-main\cyberAgent-main
```

---

### Step 2: Create & Activate Virtual Environment

```powershell
# Create virtual environment
py -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1
```
*(If PowerShell restricts script execution, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

---

### Step 3: Install FFmpeg & Verify

FFmpeg is required by `pydub` and `SpeechRecognition` to process Twilio audio recordings:

```powershell
# Install via Windows Package Manager
winget install --id Gyan.FFmpeg.Essentials -e --accept-source-agreements --accept-package-agreements

# Verify installation
ffmpeg -version
```

---

### Step 4: Install Python Dependencies

```powershell
pip install -r requirements.txt
```

---

### Step 5: Configure Environment (`.env`)

Copy `.env.example` to `.env` and fill in your Twilio details:

```ini
# Twilio Account Credentials (from https://console.twilio.com)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here

# Phone Numbers (E.164 format with country code)
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx
DEMO_TO_NUMBER=+91xxxxxxxxxx

# Twilio WhatsApp Sender (For Trial accounts use Sandbox: whatsapp:+14155238886)
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# Public Base URL (updated in Step 7)
BASE_URL=https://your-tunnel-subdomain.trycloudflare.com

# Token Security (Report access link validity in hours)
REPORT_TOKEN_EXPIRY_HOURS=24
```

> **Trial Account Note:**
> - **SMS Delivery:** On a Twilio Trial account, SMS can only be sent to numbers verified in your Twilio Console:  
>   [Twilio Verified Caller IDs](https://console.twilio.com/us1/develop/phone-numbers/manage/verified)
> - **WhatsApp Delivery:** Twilio numbers are not WhatsApp-enabled by default. Outbound WhatsApp messages use the **Twilio WhatsApp Sandbox** (`whatsapp:+14155238886`). Before receiving WhatsApp reports, the recipient must send `join <your-sandbox-keyword>` to **`+1 415 523 8886`** via WhatsApp.

---

### Step 6: Start the FastAPI Backend Server

In your first PowerShell terminal:

```powershell
py -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

You should see:
```text
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

### Step 7: Start Cloudflare Tunnel & Update `BASE_URL`

Open a **second PowerShell terminal** and run:

```powershell
cloudflared tunnel --url http://localhost:8000
```
*(Alternatively, if using ngrok: `ngrok http 8000`)*

Copy the generated public URL (e.g., `https://example-words.trycloudflare.com`).

Update `BASE_URL` in your `.env` file with this URL:
```ini
BASE_URL=https://example-words.trycloudflare.com
```

---

### Step 8: Configure Twilio Voice Webhook (For Inbound Calls)

1. Open [console.twilio.com](https://console.twilio.com)
2. Go to **Phone Numbers** ➔ **Manage** ➔ **Active numbers**
3. Click your Twilio Number (e.g. **`+1xxxxxxxxxx`**)
4. Scroll down to **Voice Configuration** (under "Voice & Fax"):
   - **A CALL COMES IN**: Select `Webhook`
   - **URL**: `https://<your-tunnel-subdomain>.trycloudflare.com/incoming-call`
   - **HTTP Method**: `HTTP POST`
5. Click **Save configuration** at the bottom.

---

### Step 9: Trigger a Live Demo Call

You can test either via outbound trigger or direct inbound dialing:

#### Option A: Outbound Call (Recommended for Demo)
Twilio calls your phone directly without incurring incoming ISD rates:

```powershell
python call_me.py
```
*(Optionally pass a custom number: `python call_me.py --to +91xxxxxxxxxx`)*

#### Option B: Inbound Call
Dial your configured Twilio number directly from your phone.

---

### Step 10: Complete the Interactive Voice Interview

1. **Language Selection:**
   - Prompt: *"नमस्ते! रक्षक एआई में आपका स्वागत है। हिंदी के लिए 1 दबाएं। For English, press 2."*
   - Press **1** for Hindi, or **2** for English on your dial pad.
2. **State Your Name:**
   - Speak your full name after the tone (e.g., *"राहुल वर्मा"* or *"Jane Doe"*).
   - Press `#` when done speaking.
3. **Describe the Incident:**
   - Explain what happened (e.g., *"मेरे बैंक से कॉल आई और उन्होंने मुझसे आधार कार्ड केवाईसी के नाम पर ओटीपी मांग कर 25000 रुपये निकाल लिए"*).
   - Press `#` when done.
4. **Context-Aware Category Follow-up Questions:**
   - Rakshak AI extracts facts in real-time and asks category-specific questions (OTP Fraud, OLX Scam, Job Scam, Loan Fraud, or General Fraud).
   - Answer each question one at a time, pressing `#` after each answer.
5. **Confirmation & Delivery Channel Selection:**
   - Rakshak AI provides a verbal case summary.
   - Press **1** or `#` to confirm and generate the report.
   - Rakshak AI then offers the **Report Delivery Menu**:
     - Press **1** to receive the secure report link via **SMS**.
     - Press **2** to receive the secure report link via **WhatsApp**.
     - Press **3** to decline receiving a link on your phone.
   - Listen to the immediate guidance (National Cyber Helpline 1930 and bank freeze instructions).

---

### Step 11: View & Access the Generated Report

Citizen reports can be accessed either via the secure, time-limited token link or via the administrative dashboard:

- **Secure Citizen Access (Token-Protected, 24h Expiry):**
  ```text
  http://localhost:8000/report/access/<secure_token>
  ```
  *(Enforces cryptographic token verification, anti-path traversal protection, and automatic 24-hour expiration).*

- **List All Reports (Admin Dashboard):**
  ```text
  http://localhost:8000/reports
  ```
- **Get Latest Report Details:**
  ```text
  http://localhost:8000/reports/latest
  ```
- **Direct Administrative PDF Download:**
  ```text
  http://localhost:8000/download/Rakshak_Report_<ReportID>_<Name>.pdf
  ```

---

## Running Automated Tests

To run the complete automated test suite (including DTMF `#` submissions, LLM incident intelligence, multi-turn category follow-up engine, secure report tokens, SMS/WhatsApp Twilio dispatch, and IVR flows):

```powershell
py -m pytest tests/ -v
```

All 77 automated unit and integration tests should pass:
```text
======================= 77 passed, 16 warnings in 9.11s =======================
```

---

## Troubleshooting Common Issues

| Issue | Likely Cause | Solution |
|---|---|---|
| `TwilioRestException 21216 / 21608` | Unverified number on Trial account | Verify your destination phone number at `https://console.twilio.com/us1/develop/phone-numbers/manage/verified` |
| `ffmpeg not found` | FFmpeg missing from PATH | Run `winget install --id Gyan.FFmpeg.Essentials -e` and restart PowerShell |
| `ModuleNotFoundError: aifc` on Python 3.13+ | Deprecated library removed | Run `pip install standard-aifc audioop-lts` |
| Twilio cannot reach webhook | Tunnel URL mismatch or stopped | Ensure `cloudflared` is running and `BASE_URL` in `.env` matches the active tunnel URL |
| Inaudible or empty speech | Background noise / quick disconnect | Speak clearly after the beep; Rakshak AI automatically applies fallback default if audio is unintelligible |
| Path traversal rejection (400/403) | Non-PDF request or traversal payload | The `/download/{filename}` endpoint enforces strict directory containment and `.pdf`/`.json` extensions |

---

## Legal & Compliance Notice

This system generates an automated incident intake report based exclusively on citizen statements provided during an emergency voice interview. It serves as an advisory and evidence-documentation aid and **does not** constitute an official Police First Information Report (FIR) or bank chargeback dispute.
