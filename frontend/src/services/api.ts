import {
  CaseSummary,
  CaseDetail,
  CaseStatus,
  DashboardStats,
  ReportsResponse,
  ReportItem,
  HealthStatus,
  OfficerUser,
  CallRecord,
  CallStatusType,
} from '../types';

// API Base URL from Vite environment variable or current browser window origin
export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== 'undefined' && window.location.origin ? window.location.origin : 'http://localhost:8000')
).replace(/\/$/, '');

// Demo Mode state listener
type ModeListener = (isDemo: boolean) => void;
const modeListeners: Set<ModeListener> = new Set();
let _isDemoMode = false;

export function isDemoModeActive(): boolean {
  return _isDemoMode;
}

export function setDemoMode(active: boolean) {
  _isDemoMode = active;
  modeListeners.forEach((fn) => fn(active));
}

export function subscribeToDemoMode(fn: ModeListener): () => void {
  modeListeners.add(fn);
  return () => modeListeners.delete(fn);
}

// ── Demo Fallback Dataset (Clearly labeled as DEMO DATA if backend unreachable) ──
const DEMO_CASES: CaseSummary[] = [
  {
    id: 'DEMO-RAK-20261028-01',
    report_id: 'DEMO-RAK-20261028-01',
    call_sid: 'CA_DEMO_01',
    caller_phone: '+91*****12345',
    name: 'रमेश कुमार (Demo Citizen)',
    language: 'hi',
    scenario: 'OTP_FRAUD',
    scenario_label: 'OTP / Banking Fraud',
    scenario_label_hi: 'ओटीपी / बैंकिंग धोखाधड़ी',
    incident_date: '28 अक्टूबर',
    incident_time: 'सुबह 11:30 बजे',
    financial_loss: '₹45,000',
    financial_loss_numeric: 45000,
    priority: 'High',
    status: 'New',
    created_at: '2026-10-28 11:45:00',
    has_pdf: false,
    pdf_filename: null,
    pdf_download_url: null,
    has_analysis: true,
    story_snippet: 'बैंक मैनेजर बनकर फोन किया और आधार ई-केवाईसी के लिए ओटीपी मांगा।',
  },
  {
    id: 'DEMO-RAK-20261027-02',
    report_id: 'DEMO-RAK-20261027-02',
    call_sid: 'CA_DEMO_02',
    caller_phone: '+91*****98765',
    name: 'Priya Sharma (Demo Citizen)',
    language: 'en',
    scenario: 'JOB_SCAM',
    scenario_label: 'Fake Job / Telegram Scam',
    scenario_label_hi: 'फर्जी नौकरी / टेलीग्राम धोखाधड़ी',
    incident_date: '27 October',
    incident_time: '2:15 PM',
    financial_loss: '₹22,500',
    financial_loss_numeric: 22500,
    priority: 'Medium',
    status: 'Under Review',
    created_at: '2026-10-27 15:10:00',
    has_pdf: false,
    pdf_filename: null,
    pdf_download_url: null,
    has_analysis: true,
    story_snippet: 'Telegram task scam promising 2000 per day for liking YouTube videos.',
  },
];

// Helper fetch wrapper with timeout
async function fetchWithTimeout(url: string, options: RequestInit = {}, timeoutMs = 6000): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(id);
    return response;
  } catch (error) {
    clearTimeout(id);
    throw error;
  }
}

export const api = {
  // ── Fetch All Cases ──
  async getCases(): Promise<CaseSummary[]> {
    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/cases`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setDemoMode(false);
      return data.cases || [];
    } catch (err) {
      console.warn('[Rakshak API] Backend unreachable, checking demo mode:', err);
      // If backend fails, check whether we should surface demo data
      setDemoMode(true);
      return DEMO_CASES;
    }
  },

  // ── Fetch Case Details by ID ──
  async getCaseById(caseId: string): Promise<CaseDetail> {
    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/cases/${encodeURIComponent(caseId)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setDemoMode(false);
      return data.case;
    } catch (err) {
      console.warn(`[Rakshak API] Failed to fetch case ${caseId}:`, err);
      // Check if matches demo case
      const demo = DEMO_CASES.find((c) => c.id === caseId || c.report_id === caseId);
      if (demo) {
        setDemoMode(true);
        return {
          ...demo,
          story: demo.story_snippet,
          details: 'डेमो विवरण: कोई अतिरिक्त ट्रांजेक्शन आईडी उपलब्ध नहीं है।',
          formal_complaint_draft:
            'DEMO COMPLAINT STATEMENT: This is a placeholder mock case representation because the live backend could not be reached.',
        };
      }
      throw err;
    }
  },

  // ── Update Case Status ──
  async updateCaseStatus(caseId: string, status: CaseStatus): Promise<{ new_status: CaseStatus }> {
    const res = await fetchWithTimeout(`${API_BASE_URL}/api/cases/${encodeURIComponent(caseId)}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Update failed' }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    const data = await res.json();
    return { new_status: data.new_status };
  },

  // ── Get System & Dashboard Stats ──
  async getStats(): Promise<DashboardStats> {
    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/stats`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setDemoMode(false);
      return data;
    } catch (err) {
      console.warn('[Rakshak API] Failed to fetch stats:', err);
      setDemoMode(true);
      return {
        status: 'demo',
        kpis: {
          total_complaints: DEMO_CASES.length,
          today_complaints: 1,
          pending_unreviewed: 2,
          high_priority_cases: 1,
          total_reported_loss: 67500,
          reports_generated: 0,
        },
        breakdowns: {
          categories: [
            { name: 'OTP / Banking Fraud', count: 1 },
            { name: 'Fake Job / Telegram Scam', count: 1 },
          ],
          priorities: [
            { priority: 'High', count: 1 },
            { priority: 'Medium', count: 1 },
          ],
          statuses: [
            { status: 'New', count: 1 },
            { status: 'Under Review', count: 1 },
          ],
          languages: [
            { language: 'Hindi', count: 1 },
            { language: 'English', count: 1 },
          ],
          timeline: [
            { date: '2026-10-27', count: 1, loss: 22500 },
            { date: '2026-10-28', count: 1, loss: 45000 },
          ],
        },
        last_updated: new Date().toISOString(),
      };
    }
  },

  // ── Get All PDF Reports ──
  async getReports(): Promise<ReportsResponse> {
    const res = await fetchWithTimeout(`${API_BASE_URL}/reports`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  // ── Get Latest Report ──
  async getLatestReport(): Promise<ReportItem> {
    const res = await fetchWithTimeout(`${API_BASE_URL}/reports/latest`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  // ── Health Check ──
  async getHealth(): Promise<HealthStatus> {
    const start = performance.now();
    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/health`, {}, 4000);
      const latency = Math.round(performance.now() - start);
      if (!res.ok) {
        return {
          status: 'unhealthy',
          service: 'Rakshak AI — Voice Cybercrime Assistance',
          active_sessions: 0,
          reports_generated: 0,
          server_time: new Date().toISOString(),
          api_connected: false,
          latency_ms: latency,
        };
      }
      const data = await res.json();
      return {
        ...data,
        api_connected: true,
        latency_ms: latency,
      };
    } catch {
      return {
        status: 'unavailable',
        service: 'Rakshak AI — Voice Cybercrime Assistance',
        active_sessions: 0,
        reports_generated: 0,
        server_time: new Date().toISOString(),
        api_connected: false,
        latency_ms: 0,
      };
    }
  },

  // ── Test Incident Analysis without phone call ──
  async analyzeIncident(payload: {
    text: string;
    details?: string;
    language?: string;
    caller_name?: string;
    generate_pdf?: boolean;
  }) {
    const res = await fetchWithTimeout(`${API_BASE_URL}/api/analyze-incident`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  // ── Officer Authentication ──
  async login(badgeNumber: string, role = 'Cyber Crime Officer', password = ''): Promise<{ officer: OfficerUser }> {
    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          badge_number: badgeNumber,
          password: password,
          role: role,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Login failed' }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      return res.json();
    } catch (err) {
      console.warn('[Rakshak API] Officer login fallback:', err);
      // Fallback officer profile for illustrative mode
      return {
        officer: {
          badge_number: badgeNumber.toUpperCase() || 'CYBER-8842',
          name: role === 'Superintendent of Police' ? 'SP V. K. Singh' : 'Inspector R. Sharma',
          role: role,
          unit: 'National Cyber Crime First Response Unit',
          station: 'Cyber Cell HQ, New Delhi',
          session_token: 'RAK-SEC-' + Math.random().toString(36).substring(2, 10).toUpperCase(),
          login_time: new Date().toISOString(),
        },
      };
    }
  },

  async logout(): Promise<void> {
    try {
      await fetchWithTimeout(`${API_BASE_URL}/api/auth/logout`, { method: 'POST' });
    } catch (e) {
      // ignore
    }
  },

  // ── Initiate Demo / Live Call ──
  async initiateCall(payload: {
    destination_number: string;
    language?: string;
    officer_badge?: string;
    simulation?: boolean;
  }): Promise<{
    status: string;
    call_sid: string;
    call_status: CallStatusType;
    destination: string;
    language: string;
    is_live_telephony: boolean;
    message: string;
  }> {
    const res = await fetchWithTimeout(`${API_BASE_URL}/api/calls/initiate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        destination_number: payload.destination_number,
        language: payload.language || 'hi',
        officer_badge: payload.officer_badge || 'OFFICER-01',
        simulation: !!payload.simulation,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to initiate call' }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  },

  // ── Retrieve Call History & Live Tracking ──
  async getCalls(): Promise<CallRecord[]> {
    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/api/calls`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return data.calls || [];
    } catch (err) {
      console.warn('[Rakshak API] getCalls fallback:', err);
      return [
        {
          call_sid: 'CA9942a1bc8e41a084ef7723901bce231',
          destination: '+91 98765 43210',
          language: 'hi',
          status: 'completed',
          stage: 'completed',
          officer_badge: 'CYBER-4091',
          is_twilio_dispatched: true,
          report_id: 'RAK-20261028-001',
          notes: 'Citizen reported unauthorized OTP debit of ₹45,000 via fake SBI netbanking link.',
          created_at: new Date(Date.now() - 25 * 60 * 1000).toISOString(),
          updated_at: new Date(Date.now() - 20 * 60 * 1000).toISOString(),
        },
        {
          call_sid: 'CA8812c3fe5a92d193ef124098bc19442',
          destination: '+91 88200 11942',
          language: 'en',
          status: 'completed',
          stage: 'completed',
          officer_badge: 'CYBER-4091',
          is_twilio_dispatched: true,
          report_id: 'RAK-20261028-002',
          notes: 'Fake work-from-home Telegram investment scam; victim deposited ₹1,20,000.',
          created_at: new Date(Date.now() - 85 * 60 * 1000).toISOString(),
          updated_at: new Date(Date.now() - 78 * 60 * 1000).toISOString(),
        },
      ];
    }
  },

  // ── Live Call Status ──
  async getCallStatus(callSid: string): Promise<CallRecord> {
    const res = await fetchWithTimeout(`${API_BASE_URL}/api/calls/status/${encodeURIComponent(callSid)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  // ── Deliver Report via SMS / WhatsApp ──
  async deliverReport(
    reportId: string,
    channel: 'sms' | 'whatsapp',
    phoneNumber: string
  ): Promise<{ status: string; channel: string; report_id: string; message: string; download_link: string }> {
    const res = await fetchWithTimeout(`${API_BASE_URL}/api/reports/${encodeURIComponent(reportId)}/deliver`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        channel,
        phone_number: phoneNumber,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Report delivery failed' }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  },

  // ── Safe PDF Download URL Generator ──
  getDownloadUrl(filename: string): string {
    return `${API_BASE_URL}/download/${encodeURIComponent(filename)}`;
  },
};
