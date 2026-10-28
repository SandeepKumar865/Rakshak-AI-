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
    # 1. OTP_FRAUD: amount lost -> date/time -> bank -> transaction reference -> suspect contact
    otp_state = IncidentState()
    otp_state.primary_fraud_category = FieldValue(value="OTP_FRAUD", status=FieldStatus.COLLECTED)
    target, q = select_next_follow_up_question(otp_state, language="hi")
    assert target == "financial_loss"
    assert "नुकसान" in q

    # 2. LOAN_FRAUD: app name -> amount paid/demanded -> threats received -> suspect contact
    loan_state = IncidentState()
    loan_state.primary_fraud_category = FieldValue(value="LOAN_FRAUD", status=FieldStatus.COLLECTED)
    target_loan, q_loan = select_next_follow_up_question(loan_state, language="hi")
    assert target_loan == "app_name"
    assert "लोन ऐप" in q_loan

    # 3. OLX_SCAM: platform -> item -> payment made -> amount -> transaction reference -> suspect contact
    olx_state = IncidentState()
    olx_state.primary_fraud_category = FieldValue(value="OLX_SCAM", status=FieldStatus.COLLECTED)
    target_olx, q_olx = select_next_follow_up_question(olx_state, language="en")
    assert target_olx == "platform"
    assert "platform" in q_olx.lower()

    # 4. JOB_SCAM: job platform -> recruiter contact -> amount paid -> promised work -> payment proof
    job_state = IncidentState()
    job_state.primary_fraud_category = FieldValue(value="JOB_SCAM", status=FieldStatus.COLLECTED)
    target_job, q_job = select_next_follow_up_question(job_state, language="hi")
    assert target_job == "platform"

    # 5. PHISHING without bank name but with loss -> asks for bank name
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

    # Next question must NOT ask for financial loss again! It should ask for incident_date (priority #2 in OTP fraud)
    next_target, next_q = select_next_follow_up_question(state, language="hi")
    assert next_target == "incident_date"
    assert "तारीख" in next_q


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
    en_state.primary_fraud_category = FieldValue(value="OTP_FRAUD", status=FieldStatus.COLLECTED)
    target, q_en = select_next_follow_up_question(en_state, language="en")
    assert target == "financial_loss"
    assert "lost" in q_en.lower() or "amount" in q_en.lower() or "debited" in q_en.lower()


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
            "SpeechResult": "धोखाधड़ी करने वाले का फोन नंबर 9876500000 था और कोई UTR नंबर नहीं है",
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


# ══════════════════════════════════════════════
#  TEST 10: STEP-BY-STEP QUESTION ADVANCEMENT ACROSS 4 FRAUD CATEGORIES
# ══════════════════════════════════════════════
def test_four_categories_step_by_step_turn_progression():
    """Verify each of the 4 categories asks exactly one question at a time and advances sequentially."""
    # ── Category 1: OTP / Banking Fraud ──
    otp_state = IncidentState()
    otp_state.primary_fraud_category = FieldValue(value="OTP_FRAUD", status=FieldStatus.COLLECTED)

    # Q1: Amount lost
    t1, q1 = select_next_follow_up_question(otp_state, "hi")
    assert t1 == "financial_loss"
    assert "नुकसान" in q1
    otp_state.financial_loss = FieldValue(value="₹20000", status=FieldStatus.COLLECTED)

    # Q2: Date/time
    t2, q2 = select_next_follow_up_question(otp_state, "hi")
    assert t2 == "incident_date"
    assert "तारीख" in q2
    otp_state.incident_date = FieldValue(value="28 Oct 2026", status=FieldStatus.COLLECTED)

    # Q3: Bank
    t3, q3 = select_next_follow_up_question(otp_state, "hi")
    assert t3 == "bank_name"
    assert "बैंक का नाम" in q3
    otp_state.bank_name = FieldValue(value="HDFC Bank", status=FieldStatus.COLLECTED)

    # Q4: Transaction reference
    t4, q4 = select_next_follow_up_question(otp_state, "hi")
    assert t4 == "transaction_reference"
    assert "UTR" in q4
    otp_state.transaction_reference = FieldValue(value="UTR987654", status=FieldStatus.COLLECTED)

    # Q5: Suspected contact details
    t5, q5 = select_next_follow_up_question(otp_state, "hi")
    assert t5 == "suspect_contact"
    assert "फोन नंबर" in q5
    otp_state.suspect_contact = FieldValue(value="9876543210", status=FieldStatus.COLLECTED)

    # All collected
    t_end, q_end = select_next_follow_up_question(otp_state, "hi")
    assert t_end == "all_collected"

    # ── Category 2: OLX / Marketplace Scam ──
    olx_state = IncidentState()
    olx_state.primary_fraud_category = FieldValue(value="OLX_SCAM", status=FieldStatus.COLLECTED)

    # Q1: Platform
    t1, q1 = select_next_follow_up_question(olx_state, "en")
    assert t1 == "platform"
    assert "platform" in q1.lower()
    olx_state.platform = FieldValue(value="OLX", status=FieldStatus.COLLECTED)

    # Q2: Item
    t2, q2 = select_next_follow_up_question(olx_state, "en")
    assert t2 == "item"
    assert "item" in q2.lower()
    olx_state.item = FieldValue(value="Used iPhone", status=FieldStatus.COLLECTED)

    # Q3: Payment method
    t3, q3 = select_next_follow_up_question(olx_state, "en")
    assert t3 == "payment_method"
    assert "payment" in q3.lower() or "qr" in q3.lower()
    olx_state.payment_method = FieldValue(value="QR Code", status=FieldStatus.COLLECTED)

    # Q4: Amount
    t4, q4 = select_next_follow_up_question(olx_state, "en")
    assert t4 == "financial_loss"
    assert "lost" in q4.lower() or "amount" in q4.lower()
    olx_state.financial_loss = FieldValue(value="₹15000", status=FieldStatus.COLLECTED)

    # Q5: Transaction reference
    t5, q5 = select_next_follow_up_question(olx_state, "en")
    assert t5 == "transaction_reference"
    assert "utr" in q5.lower() or "reference" in q5.lower()
    olx_state.transaction_reference = FieldValue(value="TXN112233", status=FieldStatus.COLLECTED)

    # Q6: Suspect contact
    t6, q6 = select_next_follow_up_question(olx_state, "en")
    assert t6 == "suspect_contact"
    assert "contact" in q6.lower() or "phone" in q6.lower()

    # ── Category 3: Job / Task Scam ──
    job_state = IncidentState()
    job_state.primary_fraud_category = FieldValue(value="JOB_SCAM", status=FieldStatus.COLLECTED)

    # Q1: Job platform
    t1, q1 = select_next_follow_up_question(job_state, "hi")
    assert t1 == "platform"
    assert "प्लेटफॉर्म" in q1
    job_state.platform = FieldValue(value="Telegram", status=FieldStatus.COLLECTED)

    # Q2: Recruiter contact
    t2, q2 = select_next_follow_up_question(job_state, "hi")
    assert t2 == "suspect_contact"
    assert "फोन नंबर" in q2 or "नाम" in q2
    job_state.suspect_contact = FieldValue(value="@fake_hr_recruiter", status=FieldStatus.COLLECTED)

    # Q3: Amount paid
    t3, q3 = select_next_follow_up_question(job_state, "hi")
    assert t3 == "financial_loss"
    assert "भुगतान" in q3 or "रुपये" in q3
    job_state.financial_loss = FieldValue(value="₹50000", status=FieldStatus.COLLECTED)

    # Q4: Promised work
    t4, q4 = select_next_follow_up_question(job_state, "hi")
    assert t4 == "promised_work"
    assert "काम या टास्क" in q4
    job_state.promised_work = FieldValue(value="YouTube video likes", status=FieldStatus.COLLECTED)

    # Q5: Payment proof / transaction reference
    t5, q5 = select_next_follow_up_question(job_state, "hi")
    assert t5 == "transaction_reference"
    assert "UTR" in q5 or "भुगतान" in q5

    # ── Category 4: Loan App Fraud ──
    loan_state = IncidentState()
    loan_state.primary_fraud_category = FieldValue(value="LOAN_FRAUD", status=FieldStatus.COLLECTED)

    # Q1: App name
    t1, q1 = select_next_follow_up_question(loan_state, "hi")
    assert t1 == "app_name"
    assert "लोन ऐप" in q1
    loan_state.app_name = FieldValue(value="Speed Loan Pro", status=FieldStatus.COLLECTED)

    # Q2: Amount paid or demanded
    t2, q2 = select_next_follow_up_question(loan_state, "hi")
    assert t2 == "financial_loss"
    assert "मांग" in q2 or "भुगतान" in q2
    loan_state.financial_loss = FieldValue(value="₹8000 demanded", status=FieldStatus.COLLECTED)

    # Q3: Threats received
    t3, q3 = select_next_follow_up_question(loan_state, "hi")
    assert t3 == "threats_received"
    assert "धमकियां" in q3
    loan_state.threats_received = FieldValue(value="Abusive calls to family contacts", status=FieldStatus.COLLECTED)

    # Q4: Relevant contact details
    t4, q4 = select_next_follow_up_question(loan_state, "hi")
    assert t4 == "suspect_contact"
    assert "फोन नंबर" in q4 or "यूपीआई" in q4


# ══════════════════════════════════════════════
#  TEST 11: END-TO-END OTP FRAUD CALL ASKS ALL 5 QUESTIONS IN SEQUENCE
# ══════════════════════════════════════════════
def test_otp_fraud_multi_turn_phone_call_asks_all_questions_in_sequence():
    """
    Simulates a live Twilio voice call for OTP fraud:
    - Step 1: Collects caller name.
    - Step 2: Collects incident story (contains loss amount).
    - Step 3 Turn 1: Asks Q2 Date/Time -> Caller answers Date/Time.
    - Step 3 Turn 2: Asks Q3 Bank -> Caller answers Bank.
    - Step 3 Turn 3: Asks Q4 UTR / Ref -> Caller says 'याद नहीं है'.
    - Step 3 Turn 4: Asks Q5 Suspect details -> Caller gives suspect phone.
    - Confirmation: After all 5 questions are handled, transitions to confirm-interview and creates report!
    """
    sid = "CA_OTP_FULL_INTERVIEW_99"
    sessions[sid] = {
        "call_sid": sid,
        "caller_phone": "+919988776655",
        "language": "hi",
        "incident_state": IncidentState().model_dump(),
        "status": "IN_PROGRESS",
    }

    with patch("llm_analyzer.GEMINI_API_KEY", ""), patch("llm_analyzer.OPENAI_API_KEY", ""), patch("asyncio.to_thread", side_effect=lambda func, *args, **kwargs: func(*args, **kwargs)):
        # ── 1. Name Step ──
        req_name = FakeFormRequest({"CallSid": sid, "SpeechResult": "मेरा नाम सक्षम है"})
        res_name = run_coro(step1_name(req_name))
        assert res_name.status_code == 200
        assert sessions[sid]["name"] == "सक्षम"

        # ── 2. Story Step (Provides financial loss) ──
        req_story = FakeFormRequest({
            "CallSid": sid,
            "SpeechResult": "मेरे बैंक से 25000 रुपये कट गए ओटीपी फ्रॉड में",
        })
        res_story = run_coro(step2_story(req_story))
        assert res_story.status_code == 200
        xml_story = res_story.body.decode("utf-8")

        # Amount is already extracted, so Q2 Date/Time must be asked!
        assert sessions[sid]["last_targeted_field"] == "incident_date"
        assert "तारीख" in xml_story
        assert 'action="/step3-details"' in xml_story

        # ── 3. Turn 1: Caller answers Date/Time ──
        req_turn1 = FakeFormRequest({
            "CallSid": sid,
            "SpeechResult": "कल दोपहर 2 बजे यह घटना हुई",
            "Digits": "#",
        })
        res_turn1 = run_coro(step3_details(req_turn1))
        assert res_turn1.status_code == 200
        xml_turn1 = res_turn1.body.decode("utf-8")

        # Must NOT exit! Must ask Q3 Bank Name!
        assert sessions[sid]["step3_completed"] is False
        assert sessions[sid]["last_targeted_field"] == "bank_name"
        assert "बैंक का नाम" in xml_turn1
        assert 'action="/step3-details"' in xml_turn1

        # ── 4. Turn 2: Caller answers Bank Name ──
        req_turn2 = FakeFormRequest({
            "CallSid": sid,
            "SpeechResult": "स्टेट बैंक ऑफ इंडिया (SBI) था",
            "Digits": "#",
        })
        res_turn2 = run_coro(step3_details(req_turn2))
        assert res_turn2.status_code == 200
        xml_turn2 = res_turn2.body.decode("utf-8")

        # Must NOT exit! Must ask Q4 Transaction Reference!
        assert sessions[sid]["step3_completed"] is False
        assert sessions[sid]["last_targeted_field"] == "transaction_reference"
        assert "UTR" in xml_turn2 or "ट्रांजेक्शन" in xml_turn2
        assert 'action="/step3-details"' in xml_turn2

        # ── 5. Turn 3: Caller does not remember UTR ──
        req_turn3 = FakeFormRequest({
            "CallSid": sid,
            "SpeechResult": "मुझे याद नहीं है, कोई यूटीआर नहीं मिला",
            "Digits": "#",
        })
        res_turn3 = run_coro(step3_details(req_turn3))
        assert res_turn3.status_code == 200
        xml_turn3 = res_turn3.body.decode("utf-8")

        # Must NOT exit! Must ask Q5 Suspect Contact!
        assert sessions[sid]["step3_completed"] is False
        assert sessions[sid]["last_targeted_field"] == "suspect_contact"
        assert "फोन नंबर" in xml_turn3 or "यूपीआई" in xml_turn3
        assert 'action="/step3-details"' in xml_turn3

        # ── 6. Turn 4: Caller answers Suspect Details ──
        req_turn4 = FakeFormRequest({
            "CallSid": sid,
            "SpeechResult": "धोखाधड़ी करने वाले का फोन नंबर 9876543210 था",
            "Digits": "#",
        })
        res_turn4 = run_coro(step3_details(req_turn4))
        assert res_turn4.status_code == 200
        xml_turn4 = res_turn4.body.decode("utf-8")

        # All 5 questions answered! Now must transition to confirmation!
        assert sessions[sid]["step3_completed"] is True
        assert 'action="/confirm-interview"' in xml_turn4
        assert "रिपोर्ट तैयार करने" in xml_turn4

        # ── 7. Confirmation Step ──
        req_confirm = FakeFormRequest({"CallSid": sid, "Digits": "1"})
        res_confirm = run_coro(confirm_interview(req_confirm))
        assert res_confirm.status_code == 200
        assert sessions[sid]["status"] == "COMPLETED"
        assert sessions[sid].get("pdf_path") is not None
        assert len(sessions[sid].get("qa_pairs", [])) == 4


# ══════════════════════════════════════════════
#  TEST 12: OTP FRAUD WITHOUT LOSS IN STORY ASKS ALL 5 FROM Q1 TO Q5
# ══════════════════════════════════════════════
def test_otp_fraud_when_loss_not_in_story_asks_all_five_questions():
    """If story does NOT mention amount, engine asks Q1(Loss)->Q2(Date)->Q3(Bank)->Q4(UTR)->Q5(Suspect)."""
    sid = "CA_OTP_STORY_NOLOSS_100"
    sessions[sid] = {
        "call_sid": sid,
        "caller_phone": "+919988776655",
        "language": "hi",
        "incident_state": IncidentState().model_dump(),
        "status": "IN_PROGRESS",
    }

    with patch("llm_analyzer.GEMINI_API_KEY", ""), patch("llm_analyzer.OPENAI_API_KEY", ""), patch("asyncio.to_thread", side_effect=lambda func, *args, **kwargs: func(*args, **kwargs)):
        # Step 1: Name
        run_coro(step1_name(FakeFormRequest({"CallSid": sid, "SpeechResult": "मेरा नाम अमित है"})))

        # Step 2: Story (No amount mentioned)
        res_story = run_coro(step2_story(FakeFormRequest({
            "CallSid": sid,
            "SpeechResult": "मेरे खाते से ओटीपी पूछकर पैसे निकाल लिए गए हैं",
        })))
        assert sessions[sid]["last_targeted_field"] == "financial_loss"
        assert "नुकसान" in res_story.body.decode("utf-8")

        # Step 3 Turn 1: Loss answer -> Next is Date/Time
        res_t1 = run_coro(step3_details(FakeFormRequest({
            "CallSid": sid,
            "SpeechResult": "कुल 50000 रुपये का नुकसान हुआ है",
            "Digits": "#",
        })))
        assert sessions[sid]["last_targeted_field"] == "incident_date"
        assert "तारीख" in res_t1.body.decode("utf-8")

        # Step 3 Turn 2: Date answer -> Next is Bank
        res_t2 = run_coro(step3_details(FakeFormRequest({
            "CallSid": sid,
            "SpeechResult": "आज सुबह 10 बजे हुआ था",
            "Digits": "#",
        })))
        assert sessions[sid]["last_targeted_field"] == "bank_name"
        assert "बैंक का नाम" in res_t2.body.decode("utf-8")

        # Step 3 Turn 3: Bank answer -> Next is UTR
        res_t3 = run_coro(step3_details(FakeFormRequest({
            "CallSid": sid,
            "SpeechResult": "पंजाब नेशनल बैंक (PNB)",
            "Digits": "#",
        })))
        assert sessions[sid]["last_targeted_field"] == "transaction_reference"
        assert "UTR" in res_t3.body.decode("utf-8")

        # Step 3 Turn 4: UTR answer -> Next is Suspect
        res_t4 = run_coro(step3_details(FakeFormRequest({
            "CallSid": sid,
            "SpeechResult": "UTR नंबर 9988776655 है",
            "Digits": "#",
        })))
        assert sessions[sid]["last_targeted_field"] == "suspect_contact"
        assert "फोन नंबर" in res_t4.body.decode("utf-8") or "यूपीआई" in res_t4.body.decode("utf-8")

        # Step 3 Turn 5: Suspect answer -> Confirmation
        res_t5 = run_coro(step3_details(FakeFormRequest({
            "CallSid": sid,
            "SpeechResult": "कॉल करने वाले का नंबर 9876500000 था",
            "Digits": "#",
        })))
        assert sessions[sid]["step3_completed"] is True
        assert 'action="/confirm-interview"' in res_t5.body.decode("utf-8")

        # Step 4: Confirm
        res_conf = run_coro(confirm_interview(FakeFormRequest({"CallSid": sid, "Digits": "#"})))
        assert res_conf.status_code == 200
        assert sessions[sid]["status"] == "COMPLETED"
        assert len(sessions[sid].get("qa_pairs", [])) == 5


# ══════════════════════════════════════════════
#  TEST 13: EXACT WORD-FOR-WORD BILINGUAL QUESTION VERIFICATION
# ══════════════════════════════════════════════
def test_exact_category_questions_word_for_word():
    """Verifies that all 4 categories formulate the exact questions specified by user in Hindi and English."""
    from llm_analyzer import CATEGORY_QUESTIONS

    # 1. OTP / Banking Fraud
    otp_q = CATEGORY_QUESTIONS["OTP_FRAUD"]
    assert otp_q["financial_loss"]["hi"] == "कृपया बताएं कि इस धोखाधड़ी में आपका कुल कितने रुपये का नुकसान हुआ है?"
    assert otp_q["financial_loss"]["en"] == "Please state the total amount of money lost or debited from your account."
    assert otp_q["incident_date"]["hi"] == "यह घटना किस तारीख और लगभग किस समय पर हुई थी?"
    assert otp_q["incident_date"]["en"] == "On what date and approximately what time did this incident occur?"
    assert otp_q["bank_name"]["hi"] == "धोखाधड़ी किस बैंक के खाते से हुई है, कृपया अपने बैंक का नाम बताएं?"
    assert otp_q["bank_name"]["en"] == "Which bank was your affected account with? Please state your bank's name."
    assert otp_q["transaction_reference"]["hi"] == "क्या आपके पास बैंक संदेश या ऐप में आया हुआ कोई UTR नंबर या ट्रांजेक्शन आईडी है?"
    assert otp_q["transaction_reference"]["en"] == "Do you have the bank UTR number, transaction reference ID, or payment proof?"
    assert otp_q["suspect_contact"]["hi"] == "क्या आपके पास धोखाधड़ी करने वाले का फोन नंबर, नाम या यूपीआई आईडी है?"
    assert otp_q["suspect_contact"]["en"] == "Do you have any contact details of the suspect, such as their phone number, UPI ID, or name?"

    # 2. OLX / Marketplace Scam
    olx_q = CATEGORY_QUESTIONS["OLX_SCAM"]
    assert olx_q["platform"]["hi"] == "यह धोखाधड़ी किस ऑनलाइन प्लेटफॉर्म पर हुई, जैसे ओएलएक्स, फेसबुक मार्केटप्लेस, या क्विकर?"
    assert olx_q["platform"]["en"] == "Which platform did this occur on, such as OLX, Facebook Marketplace, or Quikr?"
    assert olx_q["item"]["hi"] == "आप किस सामान या वस्तु को खरीदने या बेचने का प्रयास कर रहे थे?"
    assert olx_q["item"]["en"] == "What specific item or product were you attempting to buy or sell?"
    assert olx_q["payment_method"]["hi"] == "पैसे किस माध्यम से भेजे या कटे थे, जैसे क्यूआर कोड स्कैन करके या यूपीआई ऐप से?"
    assert olx_q["payment_method"]["en"] == "How was the payment made, for example by scanning a QR code or via a UPI app?"
    assert olx_q["financial_loss"]["hi"] == "कृपया बताएं कि इस धोखाधड़ी में आपका कुल कितने रुपये का नुकसान हुआ है?"
    assert olx_q["financial_loss"]["en"] == "Please state the total amount of money lost or debited from your account."
    assert olx_q["transaction_reference"]["hi"] == "क्या आपके पास बैंक संदेश या ऐप में आया हुआ कोई UTR नंबर या ट्रांजेक्शन आईडी है?"
    assert olx_q["transaction_reference"]["en"] == "Do you have the bank UTR number, transaction reference ID, or payment proof?"
    assert olx_q["suspect_contact"]["hi"] == "क्या आपके पास धोखाधड़ी करने वाले का फोन नंबर, नाम या यूपीआई आईडी है?"
    assert olx_q["suspect_contact"]["en"] == "Do you have any contact details of the suspect, such as their phone number, UPI ID, or name?"

    # 3. Job / Task Scam
    job_q = CATEGORY_QUESTIONS["JOB_SCAM"]
    assert job_q["platform"]["hi"] == "नौकरी या टास्क का ऑफर आपको किस प्लेटफॉर्म पर मिला था, जैसे टेलीग्राम या व्हाट्सएप?"
    assert job_q["platform"]["en"] == "On which platform was this job or task offered, such as Telegram or WhatsApp?"
    assert job_q["suspect_contact"]["hi"] == "क्या आपके पास उस रिक्रूटर या एडमिन का फोन नंबर, नाम, या टेलीग्राम हैंडल है?"
    assert job_q["suspect_contact"]["en"] == "Do you have any contact details of the recruiter, such as their phone number, Telegram handle, or name?"
    assert job_q["financial_loss"]["hi"] == "आपने प्रीपेड टास्क या रजिस्ट्रेशन के नाम पर कुल कितने रुपये का भुगतान किया था?"
    assert job_q["financial_loss"]["en"] == "What was the total amount you deposited or paid for the tasks or registration?"
    assert job_q["promised_work"]["hi"] == "आपको किस प्रकार के काम या टास्क का वादा किया गया था, जैसे यूट्यूब लाइक, रिव्यू या डेटा एंट्री?"
    assert job_q["promised_work"]["en"] == "What type of work or earnings were promised, such as YouTube likes, reviews, or data entry tasks?"
    assert job_q["transaction_reference"]["hi"] == "क्या आपके पास किए गए भुगतान का कोई UTR नंबर, ट्रांजेक्शन आईडी या स्क्रीनशॉट का विवरण है?"
    assert job_q["transaction_reference"]["en"] == "Do you have the transaction UTR number or payment proof for the transfers you made?"

    # 4. Loan App Fraud
    loan_q = CATEGORY_QUESTIONS["LOAN_FRAUD"]
    assert loan_q["app_name"]["hi"] == "उस फर्जी लोन ऐप का नाम क्या है जिससे आपने लोन लिया या अप्लाई किया था?"
    assert loan_q["app_name"]["en"] == "What is the exact name of the loan application you downloaded or applied through?"
    assert loan_q["financial_loss"]["hi"] == "आपसे कुल कितने रुपये की मांग की जा रही है या आपने कितना भुगतान किया है?"
    assert loan_q["financial_loss"]["en"] == "What is the total amount demanded from you or already paid as fees?"
    assert loan_q["threats_received"]["hi"] == "आपको किस प्रकार की धमकियां या ब्लैकमेलिंग का सामना करना पड़ा है, जैसे कॉन्टैक्ट लिस्ट पर कॉल करना?"
    assert loan_q["threats_received"]["en"] == "What specific threats or extortion have you experienced, such as contact list misuse or harassment?"
    assert loan_q["suspect_contact"]["hi"] == "क्या आपके पास धमकी देने वाले एजेंटों का फोन नंबर, नाम, या बैंक/यूपीआई विवरण है?"
    assert loan_q["suspect_contact"]["en"] == "Do you have the phone numbers, UPI IDs, or details of the recovery agents contacting you?"
