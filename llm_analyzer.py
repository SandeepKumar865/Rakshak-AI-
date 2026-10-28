"""
Rakshak AI — LLM Intelligence Layer
Provides structured cybercrime incident understanding, anti-hallucination fact extraction,
context-aware follow-up question generation, and formal complaint drafting.
Supports Google Gemini (primary), OpenAI/Groq (secondary), with deterministic offline fallback.
"""

import os
import json
import logging
import re
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field

from config import GEMINI_API_KEY, OPENAI_API_KEY, LLM_PROVIDER

logger = logging.getLogger("rakshak_ai.llm")


# ══════════════════════════════════════════════
#  FIELD STATUS & INCIDENT STATE MODELS
# ══════════════════════════════════════════════
class FieldStatus(str, Enum):
    COLLECTED = "COLLECTED"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"


class FieldValue(BaseModel):
    value: Optional[Any] = None
    status: FieldStatus = FieldStatus.MISSING
    clarification_note: Optional[str] = None


class IncidentState(BaseModel):
    victim_name: FieldValue = Field(default_factory=lambda: FieldValue(status=FieldStatus.MISSING))
    incident_description: FieldValue = Field(default_factory=lambda: FieldValue(status=FieldStatus.MISSING))
    primary_fraud_category: FieldValue = Field(default_factory=lambda: FieldValue(status=FieldStatus.MISSING))
    secondary_fraud_category: FieldValue = Field(default_factory=lambda: FieldValue(status=FieldStatus.NOT_APPLICABLE))
    incident_date: FieldValue = Field(default_factory=lambda: FieldValue(status=FieldStatus.MISSING))
    incident_time: FieldValue = Field(default_factory=lambda: FieldValue(status=FieldStatus.MISSING))
    financial_loss: FieldValue = Field(default_factory=lambda: FieldValue(status=FieldStatus.MISSING))
    payment_method: FieldValue = Field(default_factory=lambda: FieldValue(status=FieldStatus.MISSING))
    bank_name: FieldValue = Field(default_factory=lambda: FieldValue(status=FieldStatus.MISSING))
    transaction_reference: FieldValue = Field(default_factory=lambda: FieldValue(status=FieldStatus.MISSING))
    suspect_contact: FieldValue = Field(default_factory=lambda: FieldValue(status=FieldStatus.MISSING))
    missing_information: list[str] = Field(default_factory=list)


# ══════════════════════════════════════════════
#  STRUCTURED OUTPUT SCHEMA
# ══════════════════════════════════════════════
class SuspectDetails(BaseModel):
    names: list[str] = Field(default_factory=list, description="Explicitly mentioned names or aliases used by suspect/fraudster")
    phone_numbers: list[str] = Field(default_factory=list, description="Explicitly mentioned suspect phone numbers")
    upi_ids: list[str] = Field(default_factory=list, description="Explicitly mentioned suspect UPI IDs or VPA")
    emails: list[str] = Field(default_factory=list, description="Explicitly mentioned suspect email addresses")
    bank_accounts: list[str] = Field(default_factory=list, description="Explicitly mentioned suspect/beneficiary bank account numbers/names")
    telegram_handles: list[str] = Field(default_factory=list, description="Explicitly mentioned Telegram channels or usernames")
    websites_or_apps: list[str] = Field(default_factory=list, description="Explicitly mentioned fraudulent websites, URLs, or APKs/apps")
    impersonated_entities: list[str] = Field(default_factory=list, description="Entities impersonated by scammer (e.g. SBI, Police, FedEx, Electricity Dept)")


class BankDetails(BaseModel):
    bank_name: Optional[str] = Field(default=None, description="Name of victim's bank (e.g. State Bank of India, HDFC)")
    bank_branch: Optional[str] = Field(default=None, description="Name of victim's bank branch if mentioned")
    account_number: Optional[str] = Field(default=None, description="Victim's bank account number if mentioned")


class CybercrimeIncidentAnalysis(BaseModel):
    incident_summary: str = Field(
        description="Factual, concise summary of the incident based strictly on the victim's statement."
    )
    fraud_category: str = Field(
        description="Standard category: OTP_FRAUD, OLX_SCAM, JOB_SCAM, LOAN_FRAUD, PHISHING, or GENERAL_FRAUD"
    )
    secondary_fraud_category: Optional[str] = Field(
        default=None,
        description="Secondary overlapping category if relevant (e.g. PHISHING for OTP_FRAUD or vice versa)"
    )
    fraud_category_label: str = Field(
        description="Human-readable title in the requested language (e.g. 'Banking / OTP Fraud')"
    )
    victim_name: Optional[str] = Field(
        default=None, description="Victim's name if explicitly provided, else null"
    )
    incident_date: Optional[str] = Field(
        default=None, description="Date when incident occurred if mentioned, else null"
    )
    incident_time: Optional[str] = Field(
        default=None, description="Time when incident occurred if mentioned, else null"
    )
    financial_loss: Optional[str] = Field(
        default=None, description="Exact or estimated financial loss amount if mentioned, else null"
    )
    transaction_reference: Optional[str] = Field(
        default=None, description="UTR, UPI Ref No, or Transaction ID if mentioned, else null"
    )
    payment_method: Optional[str] = Field(
        default=None, description="Payment method used (e.g. UPI, Net Banking, Credit Card, Debit Card, QR Code), else null"
    )
    bank_details: Optional[BankDetails] = Field(
        default_factory=BankDetails,
        description="Victim's bank details for banking/financial fraud (bank name, branch, account number)"
    )
    suspect_details: SuspectDetails = Field(
        default_factory=SuspectDetails, description="Details regarding the suspect explicitly stated by the victim."
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="Key evidentiary details not yet provided (e.g. incident date/time, bank name/branch/account, suspect phone/name/UPI/email)"
    )
    follow_up_question: str = Field(
        description="A polite, single, context-aware question in caller's language targeting the highest-priority missing evidentiary detail."
    )
    target_field: Optional[str] = Field(
        default=None,
        description="The field targeted by follow_up_question (e.g. financial_loss, bank_name, suspect_contact)"
    )
    incident_state: Optional[IncidentState] = Field(
        default=None,
        description="Structured multi-field incident state tracking status of all fields."
    )
    formal_complaint_draft: str = Field(
        description="A formal citizen complaint statement drafted strictly from provided facts. Omit missing values without inventing facts."
    )
    language_detected: str = Field(
        default="hi", description="Detected language: 'hi', 'en', or 'hinglish'"
    )


# ══════════════════════════════════════════════
#  CATEGORY PRIORITIES & SINGLE QUESTIONS
# ══════════════════════════════════════════════
CATEGORY_FIELD_PRIORITIES = {
    "OTP_FRAUD": [
        "financial_loss",
        "bank_name",
        "transaction_reference",
        "suspect_contact",
        "incident_date",
        "payment_method",
    ],
    "PHISHING": [
        "financial_loss",
        "bank_name",
        "suspect_contact",
        "transaction_reference",
        "incident_date",
        "payment_method",
    ],
    "OLX_SCAM": [
        "financial_loss",
        "suspect_contact",
        "payment_method",
        "transaction_reference",
        "incident_date",
    ],
    "JOB_SCAM": [
        "financial_loss",
        "suspect_contact",
        "payment_method",
        "transaction_reference",
        "incident_date",
    ],
    "LOAN_FRAUD": [
        "suspect_contact",
        "financial_loss",
        "payment_method",
        "incident_date",
        "transaction_reference",
    ],
    "GENERAL_FRAUD": [
        "financial_loss",
        "suspect_contact",
        "payment_method",
        "incident_date",
        "transaction_reference",
    ],
}

SINGLE_QUESTIONS = {
    "financial_loss": {
        "hi": "कृपया बताएं कि इस धोखाधड़ी में आपका कुल कितने रुपये का नुकसान हुआ है?",
        "en": "Please tell us the total amount of financial loss incurred in this incident.",
        "clarify_hi": "क्या आप बता सकते हैं कि लगभग कितने रुपये का नुकसान हुआ है?",
        "clarify_en": "Could you please clarify approximately how much money was debited or lost?",
    },
    "bank_name": {
        "hi": "धोखाधड़ी किस बैंक के खाते से हुई है, कृपया अपने बैंक का नाम बताएं?",
        "en": "Which bank was your affected account with? Please share your bank's name.",
    },
    "suspect_contact": {
        "hi": "क्या आपके पास धोखाधड़ी करने वाले का फोन नंबर, नाम, या यूपीआई आईडी है?",
        "en": "Do you have any details of the fraudster, such as their phone number, UPI ID, or name?",
    },
    "transaction_reference": {
        "hi": "क्या आपके पास बैंक संदेश में आया हुआ कोई UTR नंबर या ट्रांजेक्शन आईडी है?",
        "en": "Do you have any transaction reference or UTR number from your bank message?",
    },
    "payment_method": {
        "hi": "पैसे किस माध्यम से कटे या भेजे गए, जैसे यूपीआई, नेट बैंकिंग, या कार्ड?",
        "en": "How was the payment made, for example through UPI, net banking, or card?",
    },
    "incident_date": {
        "hi": "कृपया बताएं कि यह घटना किस तारीख या दिन घटी थी?",
        "en": "Could you specify the date or day when this incident occurred?",
    },
    "all_collected": {
        "hi": "क्या इस घटना से संबंधित कोई अन्य प्रमाण या संदेश आपके पास उपलब्ध है?",
        "en": "Do you have any other evidentiary details or records regarding this incident?",
    },
}

UNKNOWN_PATTERNS = [
    r"\b(don'?t\s+know|dont\s+know|do\s+not\s+know|not\s+remember(?:ed)?|can'?t\s+remember|cannot\s+remember|no\s+idea|not\s+sure|none|no\s+info|not\s+available|pata\s+nahi|yaad\s+nahi|nahi\s+pata|naahi\s+pata)\b",
    r"(?:याद\s*नहीं|पता\s*नहीं|मालूम\s*नहीं|नहीं\s*पता|ध्यान\s*नहीं|नहीं\s*है|नहीं\s*मालूम|कुछ\s*नहीं\s*पता|कोई\s*जानकारी\s*नहीं|नाही\s*पता|नही\s*पता|नहीं\s*मालुम)",
]

AMBIGUOUS_LOSS_PATTERNS = [
    r"\b(some\s+money|few\s+thousands?|lot\s+of\s+money|not\s+sure\s+how\s+much)\b",
    r"(?:कुछ\s*पैसे|थोड़े\s*पैसे|बहुत\s*पैसे|कुछ\s*रुपये|पैसे\s*कट\s*गए|पैसे\s*गए)",
]


def is_unknown_response(text: str) -> bool:
    """Checks whether the caller indicated they don't know, cannot remember, or lack the requested detail."""
    if not text:
        return False
    clean = text.strip().lower()
    for pat in UNKNOWN_PATTERNS:
        if re.search(pat, clean, re.IGNORECASE):
            return True
    return False


def is_ambiguous_loss_response(text: str) -> bool:
    """Detects whether loss was mentioned ambiguously without an explicit figure."""
    if not text:
        return False
    clean = text.strip().lower()
    has_digit = bool(re.search(r"\d+", clean))
    has_amount_word = any(w in clean for w in ["hazaar", "hazar", "thousand", "lakh", "crore", "हजार", "लाख"])
    if has_digit or has_amount_word:
        return False
    for pat in AMBIGUOUS_LOSS_PATTERNS:
        if re.search(pat, clean, re.IGNORECASE):
            return True
    return False


def select_next_follow_up_question(
    state: IncidentState,
    language: str = "hi",
) -> tuple[str, str]:
    """
    Selects EXACTLY ONE short, natural question based on the incident category
    and highest-priority missing or clarification-needed field.
    Skips any field that is COLLECTED, UNKNOWN, or NOT_APPLICABLE.
    Returns: (target_field_name, question_text)
    """
    category = "GENERAL_FRAUD"
    if state.primary_fraud_category and state.primary_fraud_category.value:
        category = state.primary_fraud_category.value

    priorities = CATEGORY_FIELD_PRIORITIES.get(category, CATEGORY_FIELD_PRIORITIES["GENERAL_FRAUD"])

    # 1. First check for fields needing clarification
    for field_name in priorities:
        field_val: FieldValue = getattr(state, field_name, None)
        if field_val and field_val.status == FieldStatus.NEEDS_CLARIFICATION:
            q_dict = SINGLE_QUESTIONS.get(field_name, {})
            q_text = q_dict.get(f"clarify_{language}") or q_dict.get("clarify_en") or q_dict.get(language, "")
            return field_name, q_text

    # 2. Check highest-priority MISSING field
    for field_name in priorities:
        field_val: FieldValue = getattr(state, field_name, None)
        if field_val and field_val.status == FieldStatus.MISSING:
            q_dict = SINGLE_QUESTIONS.get(field_name, {})
            q_text = q_dict.get(language) or q_dict.get("en", "")
            return field_name, q_text

    # 3. All priority fields satisfied
    q_dict = SINGLE_QUESTIONS["all_collected"]
    return "all_collected", q_dict.get(language, q_dict["en"])


def extract_facts_from_text(
    combined: str,
    language: str = "hi",
    caller_name: str = "Citizen",
) -> dict:
    """
    Extracts all discernible facts from caller text (single turn or multi-turn).
    Returns a dictionary of raw extracted facts for state merging.
    """
    clean = combined.lower()

    # 1. Category Detection & Secondary Category
    category = "GENERAL_FRAUD"
    secondary_category = None
    if any(w in clean for w in ["telegram", "टेलीग्राम", "job", "नौकरी", "task", "टास्क", "part time", "wfh", "commission"]):
        category = "JOB_SCAM"
        if any(w in clean for w in ["otp", "बैंक", "bank", "खाता"]):
            secondary_category = "OTP_FRAUD"
    elif any(w in clean for w in ["olx", "ओएलएक्स", "qr", "क्यूआर", "scanner", "स्कैन", "quikr"]):
        category = "OLX_SCAM"
    elif any(w in clean for w in ["loan", "लोन", "ऋण", "emi", "processing fee", "धमकी", "blackmail"]):
        category = "LOAN_FRAUD"
    elif any(w in clean for w in ["phishing", "फिशिंग", "fake link", "लिंक", "fake website", "apk"]):
        category = "PHISHING"
        if any(w in clean for w in ["otp", "ओटीपी", "bank", "बैंक", "खाता", "अकाउंट"]):
            secondary_category = "OTP_FRAUD"
    elif any(w in clean for w in ["otp", "ओटीपी", "bank", "बैंक", "खाता", "खाते", "अकाउंट", "account", "password", "पासवर्ड", "pin", "पिन", "kyc", "debit", "credit"]):
        category = "OTP_FRAUD"
        if any(w in clean for w in ["link", "लिंक", "message", "sms", "संदेश", "phishing"]):
            secondary_category = "PHISHING"

    # 2. Extract Incident Date & Time
    incident_date = None
    date_match = re.search(
        r"\b(yesterday|today|kal|aaj|parson|कल|आज|परसों|\d{1,2}(?:st|nd|rd|th)?\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)(?:\s+\d{4})?|\d{1,2}\s*(?:जनवरी|फरवरी|मार्च|अप्रैल|मई|जून|जुलाई|अगस्त|सितंबर|अक्टूबर|नवंबर|दिसंबर)(?:\s+\d{4})?|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
        combined,
        re.IGNORECASE,
    )
    if date_match:
        incident_date = date_match.group(0).strip()

    incident_time = None
    time_match = re.search(
        r"((?:सुबह|दोपहर|शाम|रात|morning|afternoon|evening|night|dopahar|sham|raat)\s*\d{1,2}(?::\d{2})?(?:\s*(?:बजे|पर))?|\d{1,2}(?::\d{2})?\s*(?:am|pm|hours|hrs|o'clock|बजे)|(?:सुबह|दोपहर|शाम|रात|morning|afternoon|evening|night|dopahar|sham|raat))",
        combined,
        re.IGNORECASE,
    )
    if time_match:
        incident_time = time_match.group(0).strip()

    # 3. Extract Financial Loss
    explicit_loss_patterns = [
        r"(?:₹|rs\.?|inr|रुपये|रुपए)\s*([0-9]{1,3}(?:,[0-9]{2,3})+|[0-9]{3,8})",
        r"([0-9]{1,3}(?:,[0-9]{2,3})+|[0-9]{3,8})\s*(?:₹|rs\.?|inr|रुपये|रुपए|rupees|thousand|lakh|हजार|लाख)",
        r"(?:loss of|lost|debited|कट गए|कटे|नुकसान)\s*(?:₹|rs\.?|inr|रुपये|रुपए)?\s*([0-9]{1,3}(?:,[0-9]{2,3})+|[0-9]{3,8})",
    ]
    financial_loss = None
    for pat in explicit_loss_patterns:
        m = re.search(pat, combined, re.IGNORECASE)
        if m:
            financial_loss = m.group(0).strip()
            break

    if not financial_loss:
        for m in re.finditer(r"\b([0-9]{3,7})\b", combined):
            num_str = m.group(1)
            if len(num_str) == 10 and num_str[0] in "6789":
                continue
            financial_loss = f"₹{num_str}"
            break

    # 4. Extract Payment Method
    payment_method = None
    if re.search(r"\b(upi|gpay|phonepe|paytm)\b|गूगल पे|फोनपे|पेटीएम", clean):
        payment_method = "UPI"
    elif re.search(r"\b(net banking|neft|rtgs|imps)\b|नेट बैंकिंग", clean):
        payment_method = "Net Banking"
    elif re.search(r"\b(card|credit card|debit card|atm)\b|कार्ड", clean):
        payment_method = "Card"
    elif "qr" in clean or "क्यूआर" in clean:
        payment_method = "QR Code Scan"

    # 5. Extract Bank Details
    bank_name = None
    known_banks = [
        ("State Bank of India (SBI)", r"(sbi|state bank of india|स्टेट बैंक|एसबीआई)"),
        ("HDFC Bank", r"(hdfc|एचडीएफसी)"),
        ("ICICI Bank", r"(icici|आईसीआईसीआई)"),
        ("Punjab National Bank (PNB)", r"(pnb|punjab national bank|पीएनबी|पंजाब नेशनल)"),
        ("Axis Bank", r"(axis|एक्सिस बैंक)"),
        ("Bank of Baroda", r"(bank of baroda|bob|बैंक ऑफ बड़ौदा)"),
        ("Kotak Mahindra Bank", r"(kotak|कोटक)"),
        ("Canara Bank", r"(canara|केनरा|कैनरा)"),
        ("Union Bank of India", r"(union bank|यूनियन बैंक)"),
        ("IndusInd Bank", r"(indusind|इंडसइंड)"),
    ]
    for b_label, b_pat in known_banks:
        if re.search(b_pat, clean):
            bank_name = b_label
            break

    if not bank_name:
        gen_bank = re.search(r"([A-Za-z\u0900-\u097F]{2,20})\s*(?:bank|बैंक)", combined, re.IGNORECASE)
        if gen_bank and gen_bank.group(1).lower() not in ["net", "the", "my", "our", "mere", "apne", "apna", "kisi", "मेरे", "अपने", "अपना", "किसी"]:
            bank_name = f"{gen_bank.group(1).strip()} Bank"

    bank_branch = None
    branch_match = re.search(r"(?:branch|शाखा)\s*[:\-]?\s*([a-zA-Z\u0900-\u097F]+(?:\s+[a-zA-Z\u0900-\u097F]+)?)", combined, re.IGNORECASE)
    if branch_match:
        cand_branch = branch_match.group(1).strip()
        if not re.search(r"\b(manager|officer|प्रबंधक|अधिकारी|बोल|हेड|है|बैंक)\b", cand_branch, re.IGNORECASE):
            bank_branch = cand_branch

    account_number = None
    acc_match = re.search(r"(?:account|a/c|ac|खाता|खाते|अकाउंट|अकाउन्ट)(?:[^\d\n:]*?)(?:no|number|संख्या|नं)?[\s:#-]*((?:\d[\s-]*){9,18}|[xX*]{4,12}\d{3,4})", combined, re.IGNORECASE)
    if acc_match:
        account_number = re.sub(r"[\s-]+", "", acc_match.group(1).strip())

    # 6. Extract Transaction Ref / UTR
    utr_match = re.search(r"\b(utr|ref|transaction\s*id|txn)[\s:#-]*([A-Za-z0-9]{8,22})\b", combined, re.IGNORECASE)
    txn_ref = utr_match.group(2) if utr_match else None

    # 7. Extract Suspect Details
    suspect_phones = [
        re.sub(r"[\s-]+", "", m.group(0))
        for m in re.finditer(r"\b(?:\+91[\s-]?)?[6-9](?:[\s-]?\d){8,9}\b", combined)
    ]
    suspect_phones = [p for p in suspect_phones if p not in ["1930"]]

    raw_at_matches = re.findall(r"\b[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z0-9.\-_]{2,64}\b", combined)
    suspect_upis = []
    suspect_emails = []
    upi_handles = ("okaxis", "okhdfcbank", "oksbi", "okicici", "paytm", "ybl", "ibl", "axl", "upi", "apl", "fbl", "idfcbank", "freecharge", "barodampay")
    for item in raw_at_matches:
        parts = item.split("@")
        if len(parts) == 2:
            domain = parts[1].lower()
            if any(domain.startswith(u) for u in upi_handles) or "." not in domain:
                suspect_upis.append(item)
            elif "." in domain and domain.endswith(("com", "in", "org", "net", "gov", "co", "io")):
                suspect_emails.append(item)
            else:
                suspect_upis.append(item)

    suspect_telegrams = re.findall(r"(?:telegram|tg)?\s*@([a-zA-Z0-9_]{4,32})", combined, re.IGNORECASE)

    suspect_names = []
    name_patterns = [
        r"([A-Za-z\u0900-\u097F]{3,25})\s+नाम\s+से",
        r"(?:उसका\s*नाम\s*(?:था|है)?(?:\s*उसको)?|नाम\s*(?:था|है|का))\s*[:\-]?\s*([A-Za-z\u0900-\u097F]{3,25})",
        r"(?:scammer(?:\s+(?:name\s+(?:is|was)|was\s+named|named|was))?|caller(?:\s+(?:name\s+(?:is|was)|was\s+named|named|was))?|fraudster(?:\s+(?:name\s+(?:is|was)|was\s+named|named|was))?|named|व्यक्ति\s+का\s+नाम|कॉलर\s+का\s+नाम)\s*[:\-]?\s*([A-Za-z\u0900-\u097F]{3,25}(?:\s+[A-Za-z\u0900-\u097F]{3,25})?)",
    ]
    stop_words = {
        "sbi", "hdfc", "icici", "pnb", "axis", "manager", "branch", "was", "named",
        "unknown", "caller", "scammer", "bank", "प्रबंधक", "शाखा", "उसको", "उसका",
        "का", "था", "नाम", "है", "बता", "रहा", "क्रिमिनल"
    }
    for np in name_patterns:
        m = re.search(np, combined, re.IGNORECASE)
        if m:
            matched_suspect_name = m.group(1).strip()
            cleaned_words = [w for w in matched_suspect_name.split() if w.lower() not in stop_words]
            if cleaned_words:
                suspect_names.append(" ".join(cleaned_words))
                break

    # Build primary suspect contact representation
    suspect_contact = None
    if suspect_phones:
        suspect_contact = suspect_phones[0]
    elif suspect_upis:
        suspect_contact = suspect_upis[0]
    elif suspect_names:
        suspect_contact = suspect_names[0]
    elif suspect_emails:
        suspect_contact = suspect_emails[0]
    elif suspect_telegrams:
        suspect_contact = f"@{suspect_telegrams[0]}"

    # 8. Victim Name
    v_name = None
    if caller_name and caller_name not in ["नागरिक", "Citizen"]:
        v_name = re.sub(r"^(?:मेरा\s*नाम\s*|my\s*name\s*is\s*|i\s*am\s*)", "", caller_name, flags=re.I).strip(" .।हैहे")
    else:
        caller_match = re.search(r"(?:मेरा\s*नाम\s*|my\s*name\s*is\s*|i\s*am\s*)([A-Za-z\u0900-\u097F]{2,25}(?:\s+[A-Za-z\u0900-\u097F]{2,25})?)", combined, re.IGNORECASE)
        if caller_match:
            v_name = caller_match.group(1).strip(" .।हैहे")

    return {
        "victim_name": v_name,
        "incident_description": combined,
        "primary_fraud_category": category,
        "secondary_fraud_category": secondary_category,
        "incident_date": incident_date,
        "incident_time": incident_time,
        "financial_loss": financial_loss,
        "payment_method": payment_method,
        "bank_name": bank_name,
        "bank_branch": bank_branch,
        "account_number": account_number,
        "transaction_reference": txn_ref,
        "suspect_contact": suspect_contact,
        "suspect_names": suspect_names,
        "suspect_phones": suspect_phones,
        "suspect_upis": suspect_upis,
        "suspect_emails": suspect_emails,
        "suspect_telegrams": suspect_telegrams,
    }


def merge_extracted_facts(
    state: IncidentState,
    extracted: dict,
    target_field: Optional[str] = None,
    raw_answer: str = "",
) -> IncidentState:
    """
    Merges newly extracted facts into an existing IncidentState.
    Respects existing COLLECTED / UNKNOWN states and handles ambiguity or unknown intent.
    """
    clean_raw = (raw_answer or "").strip()

    # 1. Handle explicit unknown response for targeted field
    if target_field and is_unknown_response(clean_raw):
        field_obj = getattr(state, target_field, None)
        if field_obj is not None:
            field_obj.status = FieldStatus.UNKNOWN
            field_obj.value = "Unknown / Not remembered"
            logger.info(f"[STATE] Target field '{target_field}' marked as UNKNOWN from answer: '{clean_raw}'")

    # 2. Handle ambiguous financial loss
    elif target_field == "financial_loss" and is_ambiguous_loss_response(clean_raw):
        state.financial_loss.status = FieldStatus.NEEDS_CLARIFICATION
        state.financial_loss.value = clean_raw
        state.financial_loss.clarification_note = "Loss mentioned without exact figure"
        logger.info(f"[STATE] Target field 'financial_loss' marked as NEEDS_CLARIFICATION from answer: '{clean_raw}'")

    # 3. Merge victim name
    v_name = extracted.get("victim_name")
    if v_name and state.victim_name.status != FieldStatus.COLLECTED:
        state.victim_name.value = v_name
        state.victim_name.status = FieldStatus.COLLECTED

    # 4. Merge incident description
    desc = extracted.get("incident_description")
    if desc and state.incident_description.status != FieldStatus.COLLECTED:
        state.incident_description.value = desc
        state.incident_description.status = FieldStatus.COLLECTED

    # 5. Merge primary category
    cat = extracted.get("primary_fraud_category")
    if cat and (state.primary_fraud_category.status != FieldStatus.COLLECTED or state.primary_fraud_category.value == "GENERAL_FRAUD"):
        state.primary_fraud_category.value = cat
        state.primary_fraud_category.status = FieldStatus.COLLECTED

    # Merge secondary category
    sec_cat = extracted.get("secondary_fraud_category")
    if sec_cat:
        state.secondary_fraud_category.value = sec_cat
        state.secondary_fraud_category.status = FieldStatus.COLLECTED

    # 6. Merge date & time
    i_date = extracted.get("incident_date")
    if i_date and state.incident_date.status != FieldStatus.COLLECTED:
        state.incident_date.value = i_date
        state.incident_date.status = FieldStatus.COLLECTED

    i_time = extracted.get("incident_time")
    if i_time and state.incident_time.status != FieldStatus.COLLECTED:
        state.incident_time.value = i_time
        state.incident_time.status = FieldStatus.COLLECTED

    # 7. Merge financial loss
    loss = extracted.get("financial_loss")
    if loss and state.financial_loss.status != FieldStatus.UNKNOWN:
        state.financial_loss.value = loss
        state.financial_loss.status = FieldStatus.COLLECTED

    # 8. Merge payment method
    pm = extracted.get("payment_method")
    if pm and state.payment_method.status != FieldStatus.COLLECTED:
        state.payment_method.value = pm
        state.payment_method.status = FieldStatus.COLLECTED

    # 9. Merge bank name
    b_name = extracted.get("bank_name")
    if b_name and state.bank_name.status != FieldStatus.UNKNOWN:
        state.bank_name.value = b_name
        state.bank_name.status = FieldStatus.COLLECTED

    # 10. Merge transaction reference
    txn = extracted.get("transaction_reference")
    if txn and state.transaction_reference.status != FieldStatus.UNKNOWN:
        state.transaction_reference.value = txn
        state.transaction_reference.status = FieldStatus.COLLECTED

    # 11. Merge suspect contact
    s_contact = extracted.get("suspect_contact")
    if s_contact and state.suspect_contact.status != FieldStatus.UNKNOWN:
        state.suspect_contact.value = s_contact
        state.suspect_contact.status = FieldStatus.COLLECTED

    # 12. If target field was explicitly answered and not marked unknown/clarification
    if target_field and clean_raw and not is_unknown_response(clean_raw):
        field_obj = getattr(state, target_field, None)
        if field_obj and field_obj.status == FieldStatus.MISSING:
            field_obj.value = clean_raw
            field_obj.status = FieldStatus.COLLECTED

    # 13. Recompute missing information based on category priorities
    category = state.primary_fraud_category.value or "GENERAL_FRAUD"
    priorities = CATEGORY_FIELD_PRIORITIES.get(category, CATEGORY_FIELD_PRIORITIES["GENERAL_FRAUD"])
    missing_list = []
    field_labels = {
        "financial_loss": "Financial loss amount",
        "bank_name": "Victim bank name",
        "suspect_contact": "Suspect phone number, UPI ID, or name",
        "transaction_reference": "Transaction UTR or Reference Number",
        "payment_method": "Payment method",
        "incident_date": "Incident date and time",
    }
    for f in priorities:
        f_val = getattr(state, f, None)
        if f_val and f_val.status == FieldStatus.MISSING:
            missing_list.append(field_labels.get(f, f))
    state.missing_information = missing_list

    return state


# ══════════════════════════════════════════════
#  PROMPT TEMPLATES
# ══════════════════════════════════════════════
SYSTEM_PROMPT = """You are Rakshak AI's Cybercrime Legal & Incident Intelligence Specialist.
Your task is to analyze a cybercrime victim's statement and produce a structured, validated JSON output.

CRITICAL RULES:
1. STRICT TRUTHFULNESS & ZERO HALLUCINATION: Never invent names, dates, times, amounts, bank names, branch names, account numbers, or transaction IDs. If a field was not explicitly stated by the caller, set it to null or leave the list empty.
2. FRAUD CATEGORIES: Categorize strictly into one of:
   - OTP_FRAUD (Banking, KYC, OTP theft, SIM swap, fake bank manager, unauthorized debit)
   - OLX_SCAM (Marketplace, QR code scanning to receive money, army officer scam)
   - JOB_SCAM (Part-time job, Telegram tasks, prepaid review/YouTube like tasks, WFH)
   - LOAN_FRAUD (Instant loan apps, extortion, gallery/contact blackmail, processing fee)
   - PHISHING (Phishing links, malicious APKs, fake websites, account compromise)
   - GENERAL_FRAUD (Identity theft, other cybercrimes)
   If overlapping categories exist, record the primary in fraud_category and secondary in secondary_fraud_category.
3. SINGLE CONTEXT-AWARE QUESTION PER TURN:
   - Formulate EXACTLY ONE short, natural, conversational question in the caller's language.
   - Target ONLY the single highest-priority missing evidentiary detail based on category:
     * OTP_FRAUD / PHISHING: financial loss -> bank name -> transaction reference -> suspect contact -> date.
     * OLX / JOB / LOAN: financial loss / suspect contact -> payment method -> transaction reference -> date.
   - NEVER combine multiple requests into one question (do NOT ask for date AND bank AND account number AND suspect all together).
   - NEVER ask for OTPs, PINs, passwords, CVVs, or full account numbers/branch names.
   - If the caller previously stated they do not know or do not remember a detail, NEVER ask for it again; advance to the next missing detail.
   - If an answer is ambiguous (e.g. 'some money was debited'), ask one concise clarification question.
4. INCIDENT STATE & FIELD TRACKING:
   - Track fields with explicit status: COLLECTED, MISSING, UNKNOWN, NOT_APPLICABLE, NEEDS_CLARIFICATION.
5. FORMAL COMPLAINT DRAFT: Draft an official complaint narrative formatted for submission to India's National Cyber Crime Reporting Portal (cybercrime.gov.in). Use only verified statements provided by the victim. Incorporate incident date/time, victim's bank details, financial loss, UTR, and suspect details if available. Omit missing items without guessing.
6. SANITIZATION: Never output sensitive secret credentials like passwords or active 4-6 digit OTPs in plain text; redact them as [REDACTED].

Output MUST be a single, valid JSON object matching the requested schema. No conversational filler or markdown fences outside the JSON.
"""


# ══════════════════════════════════════════════
#  DETERMINISTIC FALLBACK ENGINE (OFFLINE MODE)
# ══════════════════════════════════════════════
def fallback_deterministic_analysis(
    story: str,
    details: str = "",
    language: str = "hi",
    caller_name: str = "नागरिक",
    existing_state: Optional[IncidentState] = None,
    target_field: Optional[str] = None,
) -> CybercrimeIncidentAnalysis:
    """
    Deterministic rule-based fallback when no LLM API key is configured
    or when external API calls fail. Ensures 100% availability and zero crashes.
    Extracts facts, tracks field statuses, and selects exactly one context-aware question.
    """
    combined = f"{story} {details}".strip()

    # Initialize or copy existing IncidentState
    state = existing_state.model_copy(deep=True) if existing_state else IncidentState()

    # Extract all facts from current inputs
    extracted = extract_facts_from_text(combined, language=language, caller_name=caller_name)

    # Merge extracted facts into state
    state = merge_extracted_facts(state, extracted, target_field=target_field, raw_answer=details)

    category = state.primary_fraud_category.value or "GENERAL_FRAUD"
    labels = {
        "OTP_FRAUD": ("ओटीपी / बैंकिंग धोखाधड़ी", "OTP / Banking Fraud"),
        "OLX_SCAM": ("ओएलएक्स / क्यूआर कोड धोखाधड़ी", "OLX / QR Code Scam"),
        "JOB_SCAM": ("फर्जी नौकरी / टेलीग्राम धोखाधड़ी", "Job / Telegram Scam"),
        "LOAN_FRAUD": ("फर्जी लोन / एक्सटॉर्शन धोखाधड़ी", "Instant Loan / Extortion Fraud"),
        "PHISHING": ("फ़िशिंग / खाता समझौता", "Phishing / Account Compromise"),
        "GENERAL_FRAUD": ("सामान्य साइबर अपराध", "General Cybercrime"),
    }
    cat_tuple = labels.get(category, labels["GENERAL_FRAUD"])
    cat_label = cat_tuple[0] if language == "hi" else cat_tuple[1]

    # Select single targeted question based on category priorities & missing fields
    next_target, single_question = select_next_follow_up_question(state, language=language)

    # Formal Complaint Draft
    clean_caller_name = state.victim_name.value or caller_name
    if clean_caller_name and clean_caller_name not in ["नागरिक", "Citizen"]:
        clean_caller_name = re.sub(r"^(?:मेरा\s*नाम\s*|my\s*name\s*is\s*|i\s*am\s*)", "", clean_caller_name, flags=re.I).strip(" .।हैहे")

    name_display = clean_caller_name if clean_caller_name and clean_caller_name not in ["नागरिक", "Citizen"] else "The Complainant"
    loss_display = state.financial_loss.value or "an unspecified sum"
    txn_ref = state.transaction_reference.value
    txn_display = f" under reference {txn_ref}" if txn_ref else ""
    inc_date = state.incident_date.value
    inc_time = state.incident_time.value
    date_display = f"{inc_date or 'Recent date'}" + (f" at {inc_time}" if inc_time else "")

    suspect_identifiers = []
    for p in extracted.get("suspect_phones", []):
        suspect_identifiers.append(f"Phone: {p}")
    for u in extracted.get("suspect_upis", []):
        suspect_identifiers.append(f"UPI ID: {u}")
    for n in extracted.get("suspect_names", []):
        suspect_identifiers.append(f"Name: {n}")
    for e in extracted.get("suspect_emails", []):
        suspect_identifiers.append(f"Email: {e}")
    for t in extracted.get("suspect_telegrams", []):
        suspect_identifiers.append(f"Telegram: @{t}")
    suspect_text = "; ".join(suspect_identifiers) if suspect_identifiers else "Unknown at time of recording"

    bank_name = state.bank_name.value
    bank_lines = ""
    if bank_name or extracted.get("account_number"):
        bank_lines = f"\nVictim Bank Information:\n- Bank Name: {bank_name or 'Not specified'}\n- Branch: {extracted.get('bank_branch') or 'Not specified'}\n- Account Number: {extracted.get('account_number') or 'Not specified'}\n"

    draft = (
        f"Subject: Formal Cybercrime Incident Statement — Suspected {cat_tuple[1]}\n\n"
        f"To: The Cyber Crime Police / Portal Officer\n\n"
        f"Sir/Madam,\n"
        f"I, {name_display}, wish to lodge a formal statement regarding a cyber fraud incident occurring on or around {date_display}.\n"
        f"Incident Overview: {story.strip()}\n"
    )
    if details.strip():
        draft += f"Additional Disclosures: {details.strip()}\n"
    if bank_lines:
        draft += bank_lines
    draft += (
        f"Estimated Financial Loss: {loss_display}{txn_display}.\n"
        f"Suspect Identifiers: {suspect_text}.\n\n"
        f"I request immediate action to trace the beneficiary account, freeze the fraudulent fund transfers, and take appropriate legal steps.\n"
        f"Respectfully,\n{name_display}"
    )

    bank_details_obj = BankDetails(
        bank_name=bank_name,
        bank_branch=extracted.get("bank_branch"),
        account_number=extracted.get("account_number"),
    )

    suspect_details_obj = SuspectDetails(
        names=extracted.get("suspect_names", []),
        phone_numbers=extracted.get("suspect_phones", []),
        upi_ids=extracted.get("suspect_upis", []),
        emails=extracted.get("suspect_emails", []),
        telegram_handles=extracted.get("suspect_telegrams", []),
    )

    return CybercrimeIncidentAnalysis(
        incident_summary=story.strip() or "Citizen reported unauthorized cyber incident.",
        fraud_category=category,
        secondary_fraud_category=state.secondary_fraud_category.value,
        fraud_category_label=cat_label,
        victim_name=clean_caller_name if clean_caller_name and clean_caller_name not in ["नागरिक", "Citizen"] else None,
        incident_date=inc_date,
        incident_time=inc_time,
        financial_loss=state.financial_loss.value,
        transaction_reference=txn_ref,
        payment_method=state.payment_method.value,
        bank_details=bank_details_obj,
        suspect_details=suspect_details_obj,
        missing_information=state.missing_information,
        follow_up_question=single_question,
        target_field=next_target,
        incident_state=state,
        formal_complaint_draft=draft,
        language_detected=language,
    )


# ══════════════════════════════════════════════
#  LLM INVOCATION WRAPPERS
# ══════════════════════════════════════════════
def _call_gemini_api(user_prompt: str) -> dict:
    """Call Google Gemini using google.generativeai with structured JSON output."""
    import google.generativeai as genai

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=SYSTEM_PROMPT,
        generation_config={
            "response_mime_type": "application/json",
            "temperature": 0.1,
        },
    )
    response = model.generate_content(user_prompt)
    return json.loads(response.text)


def _call_openai_api(user_prompt: str) -> dict:
    """Call OpenAI/Groq compatible API with JSON mode."""
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    content = response.choices[0].message.content
    return json.loads(content)


def analyze_incident_with_llm(
    story: str,
    details: str = "",
    language: str = "hi",
    caller_name: str = "नागरिक",
    existing_state: Optional[IncidentState] = None,
    target_field: Optional[str] = None,
) -> CybercrimeIncidentAnalysis:
    """
    Main entry point: Analyzes cybercrime statement using configured LLM.
    Automatically merges incident facts into IncidentState and selects
    exactly one targeted follow-up question. Falls back gracefully to
    deterministic engine if offline or on error.
    """
    if not story or len(story.strip()) < 3:
        return fallback_deterministic_analysis(
            story, details, language, caller_name, existing_state, target_field
        )

    # Initialize or copy state
    current_state = existing_state.model_copy(deep=True) if existing_state else IncidentState()

    state_json = json.dumps(current_state.model_dump(), ensure_ascii=False)
    user_prompt = f"""
CURRENT INCIDENT STATE:
{state_json}

VICTIM STATEMENT:
- Caller Name: {caller_name}
- Preferred Language: {language}
- Incident Description: {story}
- Latest Response / Follow-up Answer: {details or 'None yet'}
- Last Targeted Field: {target_field or 'None'}

INSTRUCTIONS:
1. Extract any newly provided facts and update the field statuses (COLLECTED, UNKNOWN, NEEDS_CLARIFICATION).
2. Choose EXACTLY ONE short, natural question in the caller's language targeting the single highest-priority missing detail.
3. NEVER ask for a detail that has already been collected or stated as unknown.
4. Return structured JSON matching the CybercrimeIncidentAnalysis schema.
"""

    parsed: Optional[CybercrimeIncidentAnalysis] = None

    # Check if Gemini key is present
    if GEMINI_API_KEY:
        try:
            logger.info("[LLM] Invoking Google Gemini 1.5 Flash...")
            raw_json = _call_gemini_api(user_prompt)
            parsed = CybercrimeIncidentAnalysis(**raw_json)
            logger.info(f"[LLM] Gemini analysis succeeded: Category={parsed.fraud_category}")
        except Exception as e:
            logger.warning(f"[LLM] Gemini API error ({e}), falling back to alternative or rule engine")

    # Check if OpenAI / Groq key is present
    if not parsed and OPENAI_API_KEY:
        try:
            logger.info("[LLM] Invoking OpenAI / Groq API...")
            raw_json = _call_openai_api(user_prompt)
            parsed = CybercrimeIncidentAnalysis(**raw_json)
            logger.info(f"[LLM] OpenAI analysis succeeded: Category={parsed.fraud_category}")
        except Exception as e:
            logger.warning(f"[LLM] OpenAI API error ({e}), falling back to rule engine")

    if parsed is not None:
        # Guarantee incident_state is merged and single question conforms to priorities
        extracted = extract_facts_from_text(f"{story} {details}".strip(), language=language, caller_name=caller_name)
        merged_state = merge_extracted_facts(current_state, extracted, target_field=target_field, raw_answer=details)
        parsed.incident_state = merged_state
        if not parsed.target_field:
            next_target, single_q = select_next_follow_up_question(merged_state, language=language)
            parsed.target_field = next_target
            if not parsed.follow_up_question or len(parsed.follow_up_question.split("?")) > 2:
                parsed.follow_up_question = single_q
        return parsed

    # Offline / Deterministic Fallback
    logger.info("[LLM] Using deterministic rule-based intelligence engine (offline fallback)")
    return fallback_deterministic_analysis(
        story, details, language, caller_name, current_state, target_field
    )
