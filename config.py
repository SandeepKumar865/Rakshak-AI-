# ╔══════════════════════════════════════════════════════════════════════╗
# ║                   RAKSHAK AI — CONFIGURATION MODULE                  ║
# ║  Loads settings from .env and environment variables securely.         ║
# ╚══════════════════════════════════════════════════════════════════════╝

import os
from pathlib import Path

# Load .env file safely
_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    with open(_env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))

# Twilio Credentials (from https://console.twilio.com)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN", "")

# Twilio Phone Number (Caller ID)
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER") or os.getenv("TWILIO_NUMBER") or ""
TWILIO_NUMBER       = TWILIO_PHONE_NUMBER  # backward compatibility alias

# Destination Mobile Number (Victim / Demo recipient)
DEMO_TO_NUMBER = os.getenv("DEMO_TO_NUMBER") or os.getenv("YOUR_NUMBER") or ""
YOUR_NUMBER    = DEMO_TO_NUMBER  # backward compatibility alias

# Public Base URL (Cloudflare Tunnel or ngrok)
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")

# ── LLM Intelligence Settings (Optional API keys; graceful offline fallback if empty) ──
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY") or ""
LLM_PROVIDER   = os.getenv("LLM_PROVIDER", "gemini").lower()



def mask_phone(phone: str) -> str:
    """Mask phone numbers for privacy in logs (e.g. +919876543210 -> +91*****43210)."""
    if not phone or len(phone) < 7:
        return "****"
    prefix = phone[:3]
    suffix = phone[-4:]
    return f"{prefix}*****{suffix}"


def mask_secret(secret: str) -> str:
    """Mask sensitive tokens (e.g. 9582f5... -> 9582****)."""
    if not secret or len(secret) < 6:
        return "******"
    return f"{secret[:4]}****"
