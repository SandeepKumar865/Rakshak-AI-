"""
Phase 2 Test Suite: Context-Aware Follow-Up Question Engine
Validates:
1. Multi-fact extraction from a single turn.
2. Skipping already collected / validated fields.
3. Generating exactly ONE single short, natural question per turn.
4. Category-specific question priorities (OTP, OLX, Job, Loan, Phishing, General).
5. Unknown / not remembered response handling ("याद नहीं", "don't know") without looping.
6. Ambiguous response handling (e.g., "कुछ पैसे कट गए") prompting concise clarification.
7. Hindi, English, and Hinglish support.
8. Accumulated IncidentState flowing into final reports and drafts.
9. CallSid session isolation and webhook idempotency.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

from llm_analyzer import (
    FieldStatus,
    FieldValue,
    IncidentState,
    CybercrimeIncidentAnalysis,
    fallback_deterministic_analysis,
    analyze_incident_with_llm,
    select_next_follow_up_question,
    merge_extracted_facts,
    extract_facts_from_text,
    is_unknown_response,
    is_ambiguous_loss_response,
    CATEGORY_FIELD_PRIORITIES,
    SINGLE_QUESTIONS,
)
from main import app, sessions, step1_name, step2_story, step3_details, confirm_interview, generate_pdf_report


def run_coro(coro):
    """Direct synchronous runner for coroutines without requiring loopback socket binding."""
    try:
        while True:
            coro.send(None)
    except StopIteration as e:
        return e.value


class FakeFormRequest:
    def __init__(self, form_data: dict):
        self._data = form_data
        self.headers = {"host": "localhost:8000"}
        self.query_params = {}

    async def form(self):
        return self._data

    async def json(self):
        return self._data


# ══════════════════════════════════════════════
#  TEST 1: MULTI-FACT EXTRACTION FROM SINGLE TURN
# ══════════════════════════════════════════════
def test_single_answer_multiple_facts_extracted():
    """A single utterance providing name, date, bank, loss, and suspect contact extracts all facts."""
    utterance = "मेरा नाम राहुल शर्मा है, कल दोपहर एसबीआई बैंक खाते से 35000 रुपये कट गए। फ्रॉड कॉलर का नंबर 9876543210 था।"
    extracted = extract_facts_from_text(utterance, language="hi")

    assert extracted["primary_fraud_category"] == "OTP_FRAUD"
    assert "राहुल" in extracted["victim_name"]
    assert "कल" in extracted["incident_date"]
    assert "दोपहर" in extracted["incident_time"]
    assert "SBI" in extracted["bank_name"] or "State Bank of India" in extracted["bank_name"]
    assert "35000" in extracted["financial_loss"]
    assert "9876543210" in extracted["suspect_phones"]

    # Verify merging into IncidentState
    state = IncidentState()
    state = merge_extracted_facts(state, extracted)

    assert state.victim_name.status == FieldStatus.COLLECTED
    assert state.incident_date.status == FieldStatus.COLLECTED
    assert state.incident_time.status == FieldStatus.COLLECTED
    assert state.bank_name.status == FieldStatus.COLLECTED
    assert state.financial_loss.status == FieldStatus.COLLECTED
    assert state.suspect_contact.status == FieldStatus.COLLECTED


# ══════════════════════════════════════════════
#  TEST 2: ANSWERED FIELDS ARE SKIPPED BY QUESTION SELECTOR
# ══════════════════════════════════════════════
def test_answered_fields_are_skipped():
    """If financial loss, bank name, and suspect are already known, question engine asks for remaining field (e.g. UTR)."""
    state = IncidentState()
    state.primary_fraud_category = FieldValue(value="OTP_FRAUD", status=FieldStatus.COLLECTED)
    state.financial_loss = FieldValue(value="₹25000", status=FieldStatus.COLLECTED)
    state.bank_name = FieldValue(value="HDFC Bank", status=FieldStatus.COLLECTED)
    state.suspect_contact = FieldValue(value="9876543210", status=FieldStatus.COLLECTED)
    state.incident_date = FieldValue(value="Yesterday", status=FieldStatus.COLLECTED)

    # Next missing in priority is transaction_reference
    target_field, question = select_next_follow_up_question(state, language="hi")
    assert target_field == "transaction_reference"
    assert "UTR" in question or "ट्रांजेक्शन आईडी" in question

    # Now collect transaction reference as well
    state.transaction_reference = FieldValue(value="UTR123456789", status=FieldStatus.COLLECTED)
    target_field_2, question_2 = select_next_follow_up_question(state, language="hi")
    assert target_field_2 in ["payment_method", "all_collected"]


# ══════════════════════════════════════════════
#  TEST 3: EXACTLY ONE QUESTION PER TURN
# ══════════════════════════════════════════════
def test_exactly_one_question_per_turn():
    """Verify follow-up question contains exactly ONE question mark and is concise."""
    scenarios = [
        ("मेरे बैंक खाते से पैसे कट गए", "hi"),
        ("Someone scammed me on OLX", "en"),
        ("Telegram task scam took 50000 rupees", "en"),
        ("फर्जी लोन ऐप वाले ब्लैकमेल कर रहे हैं", "hi"),
    ]
    for story, lang in scenarios:
        analysis = fallback_deterministic_analysis(story, language=lang)
        q = analysis.follow_up_question
        assert q is not None and len(q) > 0
        # Exactly one question mark or concise single-question sentence
        assert q.count("?") <= 1
        # Does NOT bundle multiple disjoint questions
        if lang == "hi":
            assert not ("तारीख और समय" in q and "बैंक का नाम" in q and "फोन नंबर" in q)
        else:
            assert not ("date and time" in q.lower() and "bank name" in q.lower() and "phone number" in q.lower())


# ══════════════════════════════════════════════
#  TEST 4: CATEGORY-SPECIFIC QUESTION SELECTION
# ══════════════════════════════════════════════
def test_category_specific_question_selection():
    """Different fraud categories prioritize different initial follow-up questions."""
    # 1. OTP_FRAUD without loss -> asks for financial loss
    otp_state = IncidentState()
    otp_state.primary_fraud_category = FieldValue(value="OTP_FRAUD", status=FieldStatus.COLLECTED)
    target, q = select_next_follow_up_question(otp_state, language="hi")
    assert target == "financial_loss"
    assert "नुकसान" in q

    # 2. LOAN_FRAUD without suspect -> asks for suspect / app details first
    loan_state = IncidentState()
    loan_state.primary_fraud_category = FieldValue(value="LOAN_FRAUD", status=FieldStatus.COLLECTED)
    target_loan, q_loan = select_next_follow_up_question(loan_state, language="hi")
    assert target_loan == "suspect_contact"
    assert "फोन नंबर" in q_loan or "यूपीआई" in q_loan or "नाम" in q_loan

    # 3. PHISHING without bank name but with loss -> asks for bank name
    phish_state = IncidentState()
    phish_state.primary_fraud_category = FieldValue(value="PHISHING", status=FieldStatus.COLLECTED)
    phish_state.financial_loss = FieldValue(value="₹15000", status=FieldStatus.COLLECTED)
    target_phish, q_phish = select_next_follow_up_question(phish_state, language="en")
    assert target_phish == "bank_name"
    assert "bank" in q_phish.lower()


# ══════════════════════════════════════════════
#  TEST 5: UNKNOWN / NOT REMEMBERED ANSWERS DO NOT LOOP
# ══════════════════════════════════════════════
def test_unknown_response_marks_field_unknown_and_advances():
    """If caller says 'याद नहीं' or 'don't know', field is marked UNKNOWN and next field is asked."""
    # Test unknown detection helper
    assert is_unknown_response("याद नहीं है")
    assert is_unknown_response("पता नहीं")
    assert is_unknown_response("I don't know")
    assert is_unknown_response("cannot remember")
    assert is_unknown_response("pata nahi")

    state = IncidentState()
    state.primary_fraud_category = FieldValue(value="OTP_FRAUD", status=FieldStatus.COLLECTED)
    # Target was financial loss, caller said "पता नहीं"
    state = merge_extracted_facts(state, {}, target_field="financial_loss", raw_answer="मुझे याद नहीं है")

    assert state.financial_loss.status == FieldStatus.UNKNOWN
    assert state.financial_loss.value == "Unknown / Not remembered"

    # Next question must NOT ask for financial loss again! It should ask for bank_name
    next_target, next_q = select_next_follow_up_question(state, language="hi")
    assert next_target == "bank_name"
    assert "बैंक का नाम" in next_q


# ══════════════════════════════════════════════
#  TEST 6: AMBIGUOUS RESPONSE PROMPTS CONCISE CLARIFICATION
# ══════════════════════════════════════════════
def test_ambiguous_loss_prompts_clarification():
    """If caller provides ambiguous response ('कुछ पैसे कट गए'), asks concise clarification."""
    assert is_ambiguous_loss_response("कुछ पैसे कट गए")
    assert is_ambiguous_loss_response("some money was debited")
    assert not is_ambiguous_loss_response("25000 रुपये कट गए")
    assert not is_ambiguous_loss_response("twenty thousand rupees")

    state = IncidentState()
    state.primary_fraud_category = FieldValue(value="OTP_FRAUD", status=FieldStatus.COLLECTED)
    state = merge_extracted_facts(state, {}, target_field="financial_loss", raw_answer="कुछ पैसे कट गए")

    assert state.financial_loss.status == FieldStatus.NEEDS_CLARIFICATION

    # Engine selects clarification question
    target, q = select_next_follow_up_question(state, language="hi")
    assert target == "financial_loss"
    assert "लगभग" in q and "नुकसान" in q


# ══════════════════════════════════════════════
#  TEST 7: HINDI, ENGLISH & HINGLISH SUPPORT
# ══════════════════════════════════════════════
def test_bilingual_and_hinglish_handling():
    """Verify proper detection and question selection across Hindi, English, and Hinglish."""
    # Hinglish statement
    hinglish_text = "Mera SBI account se 12000 rupaye debit ho gaye kal sham ko"
    extracted = extract_facts_from_text(hinglish_text, language="hi")

    assert "12000" in extracted["financial_loss"]
    assert "SBI" in extracted["bank_name"]
    assert "कल" in extracted["incident_date"] or "sham" in extracted["incident_time"] or "शाम" in extracted["incident_time"]

    # English question selection
    en_state = IncidentState()
    en_state.primary_fraud_category = FieldValue(value="JOB_SCAM", status=FieldStatus.COLLECTED)
    target, q_en = select_next_follow_up_question(en_state, language="en")
    assert "loss" in q_en.lower() or "amount" in q_en.lower()


# ══════════════════════════════════════════════
#  TEST 8: MULTI-TURN STATE ACCUMULATION & REPORT GENERATION
# ══════════════════════════════════════════════
def test_full_call_flow_accumulates_state_into_final_report():
    """Simulates multi-turn Twilio session: Step 1 (name) -> Step 2 (story) -> Step 3 (details) -> Confirmation."""
    sid = "CA_PHASE2_FULL_01"
    sessions[sid] = {
        "call_sid": sid,
        "caller_phone": "+919876543210",
        "language": "hi",
        "incident_state": IncidentState().model_dump(),
        "status": "IN_PROGRESS",
    }

    with patch("llm_analyzer.GEMINI_API_KEY", ""), patch("llm_analyzer.OPENAI_API_KEY", ""):
        # Turn 1: Step 1 Name
        req1 = FakeFormRequest({"CallSid": sid, "SpeechResult": "मेरा नाम विक्रम सिंह है"})
        res1 = run_coro(step1_name(req1))
        assert res1.status_code == 200
        assert sessions[sid]["name"] == "विक्रम सिंह"
        st1 = IncidentState(**sessions[sid]["incident_state"])
        assert st1.victim_name.value == "विक्रम सिंह"

        # Turn 2: Step 2 Story
        req2 = FakeFormRequest({
            "CallSid": sid,
            "SpeechResult": "कल दोपहर को एक फर्जी कॉल आई और मेरे एसबीआई खाते से 45000 रुपये कट गए",
        })
        with patch("asyncio.to_thread", side_effect=lambda func, *args, **kwargs: func(*args, **kwargs)):
            res2 = run_coro(step2_story(req2))
        assert res2.status_code == 200
        st2 = IncidentState(**sessions[sid]["incident_state"])
        assert st2.financial_loss.value == "45000 रुपये"
        assert "SBI" in st2.bank_name.value
        # Next question targeted should be UTR or suspect details
        assert sessions[sid]["last_targeted_field"] in ["transaction_reference", "suspect_contact"]

        # Turn 3: Step 3 Details
        target = sessions[sid]["last_targeted_field"]
        req3 = FakeFormRequest({
            "CallSid": sid,
            "SpeechResult": "धोखाधड़ी करने वाले का फोन नंबर 9876500000 था",
        })
        with patch("asyncio.to_thread", side_effect=lambda func, *args, **kwargs: func(*args, **kwargs)):
            res3 = run_coro(step3_details(req3))
        assert res3.status_code == 200
        st3 = IncidentState(**sessions[sid]["incident_state"])
        assert st3.suspect_contact.status == FieldStatus.COLLECTED

        # Turn 4: Confirmation with '#'
        req4 = FakeFormRequest({"CallSid": sid, "Digits": "#"})
        with patch("asyncio.to_thread", side_effect=lambda func, *args, **kwargs: func(*args, **kwargs)):
            res4 = run_coro(confirm_interview(req4))
        assert res4.status_code == 200
        assert sessions[sid]["status"] == "COMPLETED"
        assert sessions[sid].get("pdf_path") is not None


# ══════════════════════════════════════════════
#  TEST 9: CALLSID SESSION ISOLATION & IDEMPOTENCY
# ══════════════════════════════════════════════
def test_callsid_isolation_and_idempotency():
    """Two simultaneous calls have isolated states; duplicate webhooks do not re-advance conversation."""
    sid_a = "CA_ISO_A"
    sid_b = "CA_ISO_B"

    sessions[sid_a] = {
        "call_sid": sid_a,
        "language": "hi",
        "name": "User A",
        "story": "OLX scam 10000 rupees",
        "incident_state": IncidentState().model_dump(),
        "step2_completed": True,
        "follow_up_question": "प्रश्न A?",
        "scenario_label": "OLX Scam",
    }
    sessions[sid_b] = {
        "call_sid": sid_b,
        "language": "en",
        "name": "User B",
        "story": "Job scam 50000 rupees",
        "incident_state": IncidentState().model_dump(),
        "step2_completed": True,
        "follow_up_question": "Question B?",
        "scenario_label": "Job Scam",
    }

    # Re-sending step 2 to sid_a should trigger idempotency without affecting sid_b
    req_dup = FakeFormRequest({"CallSid": sid_a, "SpeechResult": "Another duplicate story"})
    res_dup = run_coro(step2_story(req_dup))
    assert res_dup.status_code == 200
    xml_a = res_dup.body.decode("utf-8")
    assert "प्रश्न A?" in xml_a

    # Verify sid_b remains unaffected
    assert sessions[sid_b]["name"] == "User B"
    assert sessions[sid_b]["language"] == "en"
