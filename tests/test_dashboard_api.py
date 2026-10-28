"""
Unit and integration tests for Rakshak AI Officer Dashboard & Telephony APIs.
Directly invokes endpoint coroutines using run_coro without requiring loopback socket binding.
"""

import pytest
import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock
from fastapi import HTTPException

from main import (
    health,
    list_cases,
    get_case_details,
    update_case_status,
    get_dashboard_stats,
    officer_login,
    officer_logout,
    initiate_demo_call,
    list_calls,
    get_call_status,
    serve_frontend_root,
    serve_dashboard,
    REPORTS_DIR,
    StatusUpdateRequest,
    OfficerLoginRequest,
    CallInitiateRequest,
)


def run_coro(coro):
    """Direct synchronous runner for coroutines without requiring loopback socket binding."""
    try:
        while True:
            coro.send(None)
    except StopIteration as e:
        return e.value


class MockRequest:
    def __init__(self, json_data=None, query_params=None):
        self._json_data = json_data or {}
        self.headers = {"host": "localhost:8000", "x-forwarded-proto": "http"}
        self.query_params = query_params or {}

    async def json(self):
        return self._json_data


def test_health_endpoints():
    """Verify health returns healthy and api_connected=True."""
    res = run_coro(health())
    assert res["status"] == "healthy"
    assert res.get("api_connected") is True
    assert "reports_generated" in res


def test_frontend_serving():
    """Verify root / and /dashboard return FileResponse for index.html."""
    res_root = run_coro(serve_frontend_root())
    assert hasattr(res_root, "status_code") or hasattr(res_root, "path")

    res_dash = run_coro(serve_dashboard())
    assert hasattr(res_dash, "status_code") or hasattr(res_dash, "path")


def test_officer_login_and_logout():
    """Verify officer authentication generates valid session token and logout succeeds."""
    # 1. Valid login
    login_req = OfficerLoginRequest(
        badge_number="CYBER-4091",
        password="TestPassword",
        role="Cyber Crime Officer",
    )
    res = run_coro(officer_login(login_req))
    assert res["status"] == "success"
    officer = res["officer"]
    assert officer["badge_number"] == "CYBER-4091"
    assert officer["name"] == "Inspector R. Sharma"
    assert officer["session_token"].startswith("RAK-SEC-")

    # 2. Empty badge fails
    with pytest.raises(HTTPException) as exc:
        run_coro(officer_login(OfficerLoginRequest(badge_number="  ")))
    assert exc.value.status_code == 400

    # 3. Logout
    res_logout = run_coro(officer_logout())
    assert res_logout["status"] == "success"


def test_list_cases_and_get_case_detail():
    """Verify list_cases returns all complaints and get_case_details retrieves case dossier."""
    test_id = f"RAK-TEST-{uuid.uuid4().hex[:6].upper()}"
    test_file = REPORTS_DIR / f"Data_{test_id}.json"
    dummy_case = {
        "report_id": test_id,
        "call_sid": f"CA_{test_id}",
        "caller_phone": "+919528818624",
        "name": "Integration Test User",
        "language": "hi",
        "scenario": "OTP_FRAUD",
        "scenario_label": "OTP / Banking Fraud",
        "financial_loss": "₹55,000",
        "story": "Bank manager pretending caller asked for OTP",
        "details": "Lost money via UPI transfer",
        "status": "New",
        "started_at": "2026-10-28T10:00:00Z",
    }
    test_file.write_text(json.dumps(dummy_case), encoding="utf-8")

    try:
        req = MockRequest()
        # 1. List cases
        res = run_coro(list_cases(req))
        assert res["status"] == "success"
        assert "cases" in res
        assert any(c["report_id"] == test_id for c in res["cases"])

        # 2. Get case details
        d_data = run_coro(get_case_details(test_id, req))
        assert d_data["status"] == "success"
        case = d_data["case"]
        assert case["id"] == test_id
        assert case["priority"] in ["Critical", "High", "Medium", "Low"]
        assert case["financial_loss_numeric"] == 55000.0

        # 3. Nonexistent case 404
        with pytest.raises(HTTPException) as exc:
            run_coro(get_case_details("NONEXISTENT_99999", req))
        assert exc.value.status_code == 404
    finally:
        if test_file.exists():
            test_file.unlink()


def test_case_status_update():
    """Verify updating case status persists change and validates allowed statuses."""
    test_id = f"RAK-TEST-{uuid.uuid4().hex[:6].upper()}"
    test_file = REPORTS_DIR / f"Data_{test_id}.json"
    dummy_case = {
        "report_id": test_id,
        "name": "Status Tester",
        "status": "New",
    }
    test_file.write_text(json.dumps(dummy_case), encoding="utf-8")

    try:
        # 1. Valid update to 'Investigating'
        payload = StatusUpdateRequest(status="Investigating")
        res = run_coro(update_case_status(test_id, payload))
        assert res["status"] == "success"
        assert res["new_status"] == "Investigating"

        # Verify disk persistence
        updated_data = json.loads(test_file.read_text(encoding="utf-8"))
        assert updated_data["status"] == "Investigating"

        # 2. Invalid status rejected
        with pytest.raises(HTTPException) as exc:
            run_coro(update_case_status(test_id, StatusUpdateRequest(status="InvalidStatus")))
        assert exc.value.status_code == 400
    finally:
        if test_file.exists():
            test_file.unlink()


def test_dashboard_stats_kpis():
    """Verify get_dashboard_stats calculates real KPIs, categories, priorities, statuses, and timeline."""
    res = run_coro(get_dashboard_stats())
    assert res["status"] == "success"

    kpis = res["kpis"]
    assert "total_complaints" in kpis
    assert "today_complaints" in kpis
    assert "pending_unreviewed" in kpis
    assert "high_priority_cases" in kpis
    assert "total_reported_loss" in kpis
    assert "reports_generated" in kpis

    breakdowns = res["breakdowns"]
    assert "categories" in breakdowns
    assert "priorities" in breakdowns
    assert "statuses" in breakdowns
    assert "languages" in breakdowns
    assert "timeline" in breakdowns


def test_call_initiation_and_status_tracking():
    """Verify demo call initiation (simulation mode) registers session and live status."""
    payload = CallInitiateRequest(
        destination_number="+91 98765 43210",
        language="hi",
        officer_badge="CYBER-99",
        simulation=True,
    )
    req = MockRequest()
    res = run_coro(initiate_demo_call(payload, req))
    assert res["status"] == "success"
    call_sid = res["call_sid"]
    assert call_sid.startswith("CA")
    assert res["is_live_telephony"] is False

    # Check status endpoint
    st_data = run_coro(get_call_status(call_sid))
    assert st_data["call_sid"] == call_sid
    assert st_data["status"] in ["initiated", "in-progress", "ringing"]

    # Check list calls
    calls_res = run_coro(list_calls())
    assert calls_res["status"] == "success"
    calls = calls_res["calls"]
    assert any(c.get("call_sid") == call_sid for c in calls)
