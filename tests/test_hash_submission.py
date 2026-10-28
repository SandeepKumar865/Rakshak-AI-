"""
Automated Test Suite for Rakshak AI — Phase 1: Hash (#) Key Answer Submission
Validates:
1. Spoken answer collection with '#' key submission (finishOnKey="#", input="speech dtmf").
2. Next question is asked ONLY after the current answer is processed and validated.
3. Empty / unintelligible answer detection and polite retry prompts.
4. Max retry exhaustion with graceful fallback (no infinite loops).
5. Full bilingual support (Hindi & English) for questions, retries, and '#' instructions.
6. Twilio CallSid session isolation across concurrent callers.
7. Webhook idempotency protection against duplicate requests.
8. Telephony/STT error resilience and graceful recovery.
9. Confirmation via '#' key to generate official PDF & JSON reports.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock

from main import (
    sessions,
    incoming_call,
    select_language,
    step1_name,
    step2_story,
    step3_details,
    confirm_interview,
    auto_save,
    speech_gather_or_record,
    clean_caller_name,
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
    """Mock FastAPI Request providing a dictionary for request.form()."""
    def __init__(self, data: dict):
        self._data = data

    async def form(self):
        return self._data


@pytest.fixture(autouse=True)
def reset_sessions():
    """Ensure clean session state for each test."""
    sessions.clear()
    yield
    sessions.clear()


# ══════════════════════════════════════════════════════════
#  TEST 1: TWIML GATHER CONFIGURATION & HASH (#) SUPPORT
# ══════════════════════════════════════════════════════════
def test_speech_gather_or_record_has_speech_dtmf_and_finish_on_key():
    """Verify speech_gather_or_record produces input='speech dtmf' and finishOnKey='#'."""
    twiml_hi = speech_gather_or_record("/step1-name", language="hi", max_speech_time=15, max_record_len=15)
    assert 'input="speech dtmf"' in twiml_hi
    assert 'finishOnKey="#"' in twiml_hi
    assert 'language="hi-IN"' in twiml_hi
    assert 'speechTimeout="auto"' in twiml_hi
    assert '<Record' in twiml_hi

    twiml_en = speech_gather_or_record("/step2-story", language="en", max_speech_time=60, max_record_len=60)
    assert 'input="speech dtmf"' in twiml_en
    assert 'finishOnKey="#"' in twiml_en
    assert 'language="en-IN"' in twiml_en
    assert '<Record' in twiml_en


# ══════════════════════════════════════════════════════════
#  TEST 2: HINDI SPOKEN NAME SUBMISSION WITH '#' KEY
# ══════════════════════════════════════════════════════════
def test_hindi_name_submission_with_hash():
    """Caller speaks name in Hindi and presses # to finish."""
    sid = "CA_HASH_HI_01"
    sessions[sid] = {"call_sid": sid, "language": "hi"}

    # Caller speaks name and presses # (Twilio delivers SpeechResult and Digits="#")
    req = FakeFormRequest({
        "CallSid": sid,
        "SpeechResult": "मेरा नाम आशीष मौर्य है",
        "Digits": "#",
    })
    res = run_coro(step1_name(req))

    assert res.status_code == 200
    xml = res.body.decode("utf-8")

    # 1. Answer processed and cleaned
    assert sessions[sid]["name"] == "आशीष मौर्य"
    assert sessions[sid]["step1_completed"] is True

    # 2. Next question (Incident Story) is prompted only after answer processed
    assert "धन्यवाद, आशीष मौर्य जी।" in xml
    assert "बीप के बाद कृपया विस्तार से बताएं" in xml
    assert 'हैश (#) दबाएं' in xml
    assert 'action="/step2-story"' in xml
    assert 'finishOnKey="#"' in xml
    assert 'input="speech dtmf"' in xml


# ══════════════════════════════════════════════════════════
#  TEST 3: ENGLISH SPOKEN NAME SUBMISSION WITH '#' KEY
# ══════════════════════════════════════════════════════════
def test_english_name_submission_with_hash():
    """Caller speaks name in English and presses # to finish."""
    sid = "CA_HASH_EN_01"
    sessions[sid] = {"call_sid": sid, "language": "en"}

    req = FakeFormRequest({
        "CallSid": sid,
        "SpeechResult": "My name is Priya Sharma",
        "Digits": "#",
    })
    res = run_coro(step1_name(req))

    assert res.status_code == 200
    xml = res.body.decode("utf-8")

    assert sessions[sid]["name"] == "Priya Sharma"
    assert sessions[sid]["step1_completed"] is True
    assert "Thank you, Priya Sharma." in xml
    assert "describe in detail what happened and press hash (#) when finished" in xml
    assert 'action="/step2-story"' in xml
    assert 'finishOnKey="#"' in xml


# ══════════════════════════════════════════════════════════
#  TEST 4: EMPTY ANSWER DETECTION & RETRY BEHAVIOR
# ══════════════════════════════════════════════════════════
def test_empty_answer_retry_prompt_step1():
    """If caller presses '#' with silence or unintelligible speech, system politely asks again."""
    sid = "CA_EMPTY_01"
    sessions[sid] = {"call_sid": sid, "language": "hi"}

    # Attempt 1: Caller pressed # immediately with no speech
    req1 = FakeFormRequest({"CallSid": sid, "SpeechResult": "", "Digits": "#"})
    res1 = run_coro(step1_name(req1))

    assert res1.status_code == 200
    xml1 = res1.body.decode("utf-8")
    assert "हमें आपका नाम सुनाई नहीं दिया" in xml1
    assert 'action="/step1-name"' in xml1
    assert sessions[sid].get("name_retries") == 1
    assert sessions[sid].get("step1_completed") is not True

    # Attempt 2: Still empty
    req2 = FakeFormRequest({"CallSid": sid, "SpeechResult": "   ", "Digits": "#"})
    res2 = run_coro(step1_name(req2))
    assert res2.status_code == 200
    assert sessions[sid].get("name_retries") == 2
    assert sessions[sid].get("step1_completed") is not True

    # Attempt 3: Caller now speaks name
    req3 = FakeFormRequest({"CallSid": sid, "SpeechResult": "विकास सिंह", "Digits": "#"})
    res3 = run_coro(step1_name(req3))
    assert res3.status_code == 200
    assert sessions[sid]["name"] == "विकास सिंह"
    assert sessions[sid]["step1_completed"] is True
    assert "धन्यवाद, विकास सिंह जी।" in res3.body.decode("utf-8")


# ══════════════════════════════════════════════════════════
#  TEST 5: EXCEEDING RETRY LIMIT FALLS BACK SAFELY
# ══════════════════════════════════════════════════════════
def test_max_retries_fallback_without_infinite_loop():
    """When caller exceeds maximum retries, system assigns default name and proceeds to Question 2."""
    sid = "CA_MAX_RETRY_01"
    sessions[sid] = {"call_sid": sid, "language": "en"}

    # Send 3 empty inputs
    req_empty = FakeFormRequest({"CallSid": sid, "SpeechResult": "#", "Digits": "#"})
    run_coro(step1_name(req_empty))  # retry 1
    run_coro(step1_name(req_empty))  # retry 2
    res3 = run_coro(step1_name(req_empty))  # retry 3 -> fallback

    assert res3.status_code == 200
    xml = res3.body.decode("utf-8")
    assert sessions[sid]["name"] == "Citizen"
    assert sessions[sid]["step1_completed"] is True
    assert "Thank you, Citizen." in xml
    assert 'action="/step2-story"' in xml


# ══════════════════════════════════════════════════════════
#  TEST 6: INCIDENT STORY SUBMISSION & FRAUD CLASSIFICATION
# ══════════════════════════════════════════════════════════
def test_incident_story_submission_with_hash():
    """Caller speaks incident story, presses #, and LLM intelligence analyzes before asking Question 3."""
    sid = "CA_STORY_01"
    sessions[sid] = {
        "call_sid": sid,
        "language": "hi",
        "name": "राजेश",
        "step1_completed": True,
    }

    story_text = "मुझे 9876543210 से फोन आया कि बैंक खाता केवाईसी के लिए ओटीपी बताएं और मेरे 30000 रुपये कट गए"
    req = FakeFormRequest({
        "CallSid": sid,
        "SpeechResult": story_text,
        "Digits": "#",
    })

    with patch("asyncio.to_thread", side_effect=lambda func, *args, **kwargs: func(*args, **kwargs)):
        res = run_coro(step2_story(req))

    assert res.status_code == 200
    xml = res.body.decode("utf-8")

    assert sessions[sid]["story"] == story_text
    assert sessions[sid]["scenario"] == "OTP_FRAUD"
    assert sessions[sid]["step2_completed"] is True
    assert "30000" in sessions[sid]["financial_loss"]
    assert 'action="/step3-details"' in xml
    assert 'finishOnKey="#"' in xml
    assert 'हैश (#) दबाएं' in xml


# ══════════════════════════════════════════════════════════
#  TEST 7: DETAILS SUBMISSION & SUMMARY CONFIRMATION
# ═══════════════════════════════════════════════
def test_details_submission_and_confirmation_prompt():
    """Caller provides follow-up details and system presents confirmation menu accepting '1' or '#'."""
    sid = "CA_DETAILS_01"
    sessions[sid] = {
        "call_sid": sid,
        "language": "en",
        "name": "Alex",
        "story": "OLX seller scam using QR code",
        "scenario": "OLX_SCAM",
        "scenario_label": "OLX / QR Code Scam",
        "follow_up_question": "What was the suspect UPI ID or phone number?",
        "step2_completed": True,
    }

    req = FakeFormRequest({
        "CallSid": sid,
        "SpeechResult": "The suspect UPI ID was scammer@okhdfcbank and phone was 9123456789",
        "Digits": "#",
    })

    with patch("asyncio.to_thread", side_effect=lambda func, *args, **kwargs: func(*args, **kwargs)):
        res = run_coro(step3_details(req))

    assert res.status_code == 200
    xml = res.body.decode("utf-8")

    assert sessions[sid]["step3_completed"] is True
    assert "scammer@okhdfcbank" in sessions[sid]["details"]
    assert 'action="/confirm-interview"' in xml
    assert "Press 1 or hash (#) to generate your report" in xml


# ══════════════════════════════════════════════════════════
#  TEST 8: CONFIRMATION WITH HASH (#) GENERATES PDF/JSON
# ══════════════════════════════════════════════════════════
def test_confirm_interview_with_hash_generates_reports():
    """Pressing '#' at confirmation step successfully generates official bilingual reports."""
    sid = "CA_CONFIRM_HASH_01"
    sessions[sid] = {
        "call_sid": sid,
        "language": "hi",
        "name": "सुरेश कुमार",
        "story": "टेलीग्राम पर पार्ट टाइम जॉब के नाम पर 25000 रुपये ठग लिए",
        "scenario": "JOB_SCAM",
        "scenario_label": "फर्जी नौकरी / टेलीग्राम टास्क धोखाधड़ी",
        "details": "यूपीआई से पैसे भेजे थे",
        "financial_loss": "25000 रुपये",
        "step3_completed": True,
    }

    req = FakeFormRequest({
        "CallSid": sid,
        "Digits": "#",
    })

    with patch("asyncio.to_thread", side_effect=lambda func, *args, **kwargs: func(*args, **kwargs)):
        res = run_coro(confirm_interview(req))

    assert res.status_code == 200
    xml = res.body.decode("utf-8")

    assert sessions[sid]["status"] == "COMPLETED"
    assert "<Hangup/>" in xml
    assert "1930" in xml

    pdf_path = sessions[sid].get("pdf_path")
    json_path = sessions[sid].get("json_path")

    assert pdf_path is not None and os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 1000  # Valid non-empty PDF
    assert json_path is not None and os.path.exists(json_path)

    with open(json_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["name"] == "सुरेश कुमार"
    assert meta["scenario"] == "JOB_SCAM"


# ══════════════════════════════════════════════════════════
#  TEST 9: IDEMPOTENCY — DUPLICATE WEBHOOK REQUESTS
# ══════════════════════════════════════════════════════════
def test_idempotency_prevents_duplicate_processing():
    """Re-sent webhook requests for already completed steps do not advance turn or re-run LLM."""
    sid = "CA_IDEMPOTENT_01"
    sessions[sid] = {"call_sid": sid, "language": "hi"}

    # First delivery: processes name
    req1 = FakeFormRequest({"CallSid": sid, "SpeechResult": "नीता वर्मा", "Digits": "#"})
    res1 = run_coro(step1_name(req1))
    assert res1.status_code == 200
    assert sessions[sid]["name"] == "नीता वर्मा"
    assert sessions[sid]["step1_completed"] is True

    # Duplicate delivery of Step 1: should re-serve Question 2 prompt without error
    req_dup = FakeFormRequest({"CallSid": sid, "SpeechResult": "नीता वर्मा duplicate", "Digits": "#"})
    res_dup = run_coro(step1_name(req_dup))
    assert res_dup.status_code == 200
    # Name must NOT be overwritten by duplicate request
    assert sessions[sid]["name"] == "नीता वर्मा"
    assert "धन्यवाद, नीता वर्मा जी।" in res_dup.body.decode("utf-8")


# ══════════════════════════════════════════════════════════
#  TEST 10: CALLSID SESSION ISOLATION
# ══════════════════════════════════════════════════════════
def test_call_sid_session_isolation():
    """Multiple callers on different CallSids maintain completely isolated states."""
    sid1 = "CA_CALL_A"
    sid2 = "CA_CALL_B"

    sessions[sid1] = {"call_sid": sid1, "language": "hi"}
    sessions[sid2] = {"call_sid": sid2, "language": "en"}

    req1 = FakeFormRequest({"CallSid": sid1, "SpeechResult": "मनोज शर्मा", "Digits": "#"})
    req2 = FakeFormRequest({"CallSid": sid2, "SpeechResult": "Sarah Connor", "Digits": "#"})

    run_coro(step1_name(req1))
    run_coro(step1_name(req2))

    assert sessions[sid1]["name"] == "मनोज शर्मा"
    assert sessions[sid1]["language"] == "hi"

    assert sessions[sid2]["name"] == "Sarah Connor"
    assert sessions[sid2]["language"] == "en"


# ══════════════════════════════════════════════════════════
#  TEST 11: DISCONNECT & TRANSCRIPTION FAILURE SAFETY
# ══════════════════════════════════════════════════════════
def test_transcription_failure_and_disconnect_safety():
    """Failed transcription or unexpected audio error does not crash the system."""
    sid = "CA_CRASH_TEST_01"
    sessions[sid] = {"call_sid": sid, "language": "en"}

    # Mock transcribe_audio_async returning empty string (e.g. timeout or inaudible)
    with patch("main.transcribe_audio_async", return_value=""):
        req = FakeFormRequest({"CallSid": sid, "RecordingUrl": "http://mock/error.wav"})
        res = run_coro(step1_name(req))

    assert res.status_code == 200
    # Should trigger retry prompt, not crash
    assert "We could not hear your name" in res.body.decode("utf-8")
    assert sessions[sid]["name_retries"] == 1


# ══════════════════════════════════════════════════════════
#  TEST 12: AUTO-SAVE PRESERVES COLLECTED DATA ON TIMEOUT
# ══════════════════════════════════════════════════════════
def test_auto_save_fallback_on_caller_timeout():
    """If caller hangs up or times out during confirmation, auto-save secures reports."""
    sid = "CA_AUTOSAVE_01"
    sessions[sid] = {
        "call_sid": sid,
        "language": "hi",
        "name": "सुरेश",
        "story": "ओटीपी फ्रॉड हुआ 10000 रुपये का",
        "scenario": "OTP_FRAUD",
        "scenario_label": "ओटीपी धोखाधड़ी",
        "details": "अज्ञात नंबर से कॉल आई थी",
    }

    req = FakeFormRequest({"CallSid": sid})
    with patch("asyncio.to_thread", side_effect=lambda func, *args, **kwargs: func(*args, **kwargs)):
        res = run_coro(auto_save(req, CallSid=sid))

    assert res.status_code == 200
    xml = res.body.decode("utf-8")
    assert "<Hangup/>" in xml
    assert sessions[sid]["status"] == "COMPLETED"
    assert sessions[sid].get("pdf_path") is not None
