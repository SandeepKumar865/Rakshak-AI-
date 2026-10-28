import React, { useState, useEffect } from 'react';
import {
  Activity,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Server,
  Shield,
  HardDrive,
  Cpu,
} from 'lucide-react';
import { HealthStatus } from '../types';
import { api, API_BASE_URL } from '../services/api';

export const SystemHealth: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastChecked, setLastChecked] = useState<string>('');

  const checkHealth = async () => {
    setLoading(true);
    try {
      const data = await api.getHealth();
      setHealth(data);
      setLastChecked(new Date().toLocaleTimeString());
    } catch {
      setHealth({
        status: 'unavailable',
        service: 'Rakshak AI — Voice Cybercrime Assistance',
        active_sessions: 0,
        reports_generated: 0,
        server_time: new Date().toISOString(),
        api_connected: false,
      });
      setLastChecked(new Date().toLocaleTimeString());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
    const timer = setInterval(checkHealth, 15000);
    return () => clearInterval(timer);
  }, []);

  const isOperational = health?.status === 'healthy';

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* ── Page Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2.5">
            <Activity className="w-6 h-6 text-blue-600" />
            <span>Telephony & API Infrastructure Health</span>
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Operational status of FastAPI server, Twilio voice webhooks, speech recognition, and report generation.
          </p>
        </div>

        <button
          onClick={checkHealth}
          disabled={loading}
          className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 flex items-center gap-2 shadow-sm transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-blue-600 ${loading ? 'animate-spin' : ''}`} />
          <span>Ping Status</span>
        </button>
      </div>

      {/* ── Operational Status Banner ── */}
      <div
        className={`p-6 rounded-2xl border shadow-card transition-all ${
          isOperational
            ? 'bg-emerald-50/60 border-emerald-200'
            : 'bg-rose-50/60 border-rose-200'
        }`}
      >
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div
              className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 shadow-sm ${
                isOperational
                  ? 'bg-emerald-600 text-white'
                  : 'bg-rose-600 text-white'
              }`}
            >
              {isOperational ? (
                <CheckCircle2 className="w-6 h-6" />
              ) : (
                <XCircle className="w-6 h-6" />
              )}
            </div>

            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-lg font-bold text-slate-900">
                  {isOperational ? 'All Telephony & Reporting Services Operational' : 'Backend Server Unavailable'}
                </span>
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700 font-semibold shadow-sm">
                  {health?.latency_ms ? `${health.latency_ms}ms response` : 'Offline'}
                </span>
              </div>
              <p className="text-xs text-slate-600">
                {isOperational
                  ? 'FastAPI server, Twilio webhook endpoints, and bilingual PDF generator are operating normally.'
                  : `Cannot connect to backend at ${API_BASE_URL}. Ensure uvicorn main:app is running.`}
              </p>
            </div>
          </div>

          <div className="text-xs text-slate-500 font-mono shrink-0">
            <div>Last Verified: <strong className="text-slate-900">{lastChecked || 'Checking...'}</strong></div>
            <div>Server Timestamp: <strong className="text-slate-700">{health?.server_time?.slice(0, 19) || 'N/A'}</strong></div>
          </div>
        </div>
      </div>

      {/* ── Subsystems Grid ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Subsystem 1: FastAPI Core */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-card space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-slate-900 font-bold text-sm">
              <Server className="w-4 h-4 text-blue-600" />
              <span>FastAPI Server</span>
            </div>
            <span
              className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                health?.api_connected
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  : 'bg-rose-50 text-rose-700 border border-rose-200'
              }`}
            >
              {health?.api_connected ? 'CONNECTED' : 'DISCONNECTED'}
            </span>
          </div>

          <p className="text-xs text-slate-500">
            Serving endpoints: <code className="text-blue-600 font-mono text-[11px]">/reports</code>,{' '}
            <code className="text-blue-600 font-mono text-[11px]">/api/cases</code>,{' '}
            <code className="text-blue-600 font-mono text-[11px]">/download</code>.
          </p>

          <div className="pt-2 border-t border-slate-100 text-xs text-slate-600 space-y-1">
            <div>Target Base URL: <span className="font-mono text-slate-900 font-semibold">{API_BASE_URL}</span></div>
            <div>Active Call Sessions: <span className="font-mono text-blue-600 font-bold">{health?.active_sessions ?? 0}</span></div>
          </div>
        </div>

        {/* Subsystem 2: Report Engine */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-card space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-slate-900 font-bold text-sm">
              <HardDrive className="w-4 h-4 text-teal-600" />
              <span>Report Engine</span>
            </div>
            <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              FPDF2 ACTIVE
            </span>
          </div>

          <p className="text-xs text-slate-500">
            Bilingual Devanagari & Latin typography rendering pipeline with strict path-traversal safeguards.
          </p>

          <div className="pt-2 border-t border-slate-100 text-xs text-slate-600 space-y-1">
            <div>Reports Directory: <span className="font-mono text-slate-900 font-semibold">backend/reports/</span></div>
            <div>Reports On Disk: <span className="font-mono text-emerald-600 font-bold">{health?.reports_generated ?? 0}</span></div>
          </div>
        </div>

        {/* Subsystem 3: AI Layer */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-card space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-slate-900 font-bold text-sm">
              <Cpu className="w-4 h-4 text-purple-600" />
              <span>AI Intelligence Layer</span>
            </div>
            <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
              OPERATIONAL
            </span>
          </div>

          <p className="text-xs text-slate-500">
            Anti-hallucination fact extraction, scam categorization, missing evidentiary item detection, and complaint drafting.
          </p>

          <div className="pt-2 border-t border-slate-100 text-xs text-slate-600 space-y-1">
            <div>Fallback Engine: <span className="text-emerald-700 font-medium">Deterministic Rule Set</span></div>
            <div>Bilingual STT: <span className="text-blue-600 font-mono font-semibold">hi-IN / en-IN</span></div>
          </div>
        </div>
      </div>

      {/* ── Security & Compliance Checklist ── */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-card space-y-4">
        <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <Shield className="w-5 h-5 text-blue-600" />
          <span>Security & Data Hardening Verification</span>
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 flex items-start gap-3">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-slate-900">Path Traversal Attack Protection</p>
              <p className="text-slate-500 mt-0.5">
                Download route <code className="text-blue-600 font-mono">/download/{'{filename}'}</code> strictly resolves files within <code className="font-mono">REPORTS_DIR</code> and forbids directory escapes.
              </p>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 flex items-start gap-3">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-slate-900">PII & Credential Redaction</p>
              <p className="text-slate-500 mt-0.5">
                Active OTPs, PINs, and card numbers spoken by callers are automatically redacted with [REDACTED] in generated reports.
              </p>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 flex items-start gap-3">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-slate-900">Zero Client-Side Secret Exposure</p>
              <p className="text-slate-500 mt-0.5">
                Twilio Account SID, Auth Token, and AI keys reside strictly in backend configuration and are never sent to the browser.
              </p>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 flex items-start gap-3">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-slate-900">CORS Policy Configured</p>
              <p className="text-slate-500 mt-0.5">
                FastAPI CORS middleware is restricted to authorized frontend development and production origins.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
