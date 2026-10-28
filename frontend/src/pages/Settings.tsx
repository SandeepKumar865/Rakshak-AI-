import React, { useState } from 'react';
import {
  Settings as SettingsIcon,
  Server,
  Check,
  PhoneCall,
  Radio,
} from 'lucide-react';
import { API_BASE_URL } from '../services/api';

interface SettingsProps {
  pollingInterval: number;
  onSetPollingInterval: (ms: number) => void;
  isDemoMode: boolean;
  onToggleDemoMode: (val: boolean) => void;
}

export const Settings: React.FC<SettingsProps> = ({
  pollingInterval,
  onSetPollingInterval,
  isDemoMode,
  onToggleDemoMode,
}) => {
  const [savedAlert, setSavedAlert] = useState(false);

  const handleSaveNotification = () => {
    setSavedAlert(true);
    setTimeout(() => setSavedAlert(false), 2000);
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* ── Page Header ── */}
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2.5">
          <SettingsIcon className="w-6 h-6 text-blue-600" />
          <span>System & Telephony Settings</span>
        </h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Manage real-time polling cadence, backend API endpoints, and demonstration data settings.
        </p>
      </div>

      {savedAlert && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold flex items-center gap-2 shadow-sm">
          <Check className="w-4 h-4 text-emerald-600" />
          <span>Preferences updated successfully.</span>
        </div>
      )}

      {/* ── Connection Settings ── */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-card space-y-5">
        <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2 border-b border-slate-100 pb-3">
          <Server className="w-4 h-4 text-blue-600" />
          <span>Backend API Integration</span>
        </h2>

        <div className="space-y-4 text-xs">
          <div>
            <label className="text-slate-700 font-semibold block mb-1">
              API Base URL (bound via <code className="text-blue-700 font-mono">VITE_API_BASE_URL</code>):
            </label>
            <input
              type="text"
              readOnly
              value={API_BASE_URL}
              className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2 text-sm text-slate-900 font-mono focus:outline-none"
            />
            <p className="text-[11px] text-slate-500 mt-1">
              Configured in <code className="font-mono">frontend/.env</code>. Points to the active FastAPI server.
            </p>
          </div>

          <div>
            <label className="text-slate-700 font-semibold block mb-1">
              Real-time Polling & Live Intake Refresh Frequency:
            </label>
            <select
              value={pollingInterval}
              onChange={(e) => {
                onSetPollingInterval(Number(e.target.value));
                handleSaveNotification();
              }}
              className="bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2 text-xs font-semibold text-slate-800 focus:outline-none focus:border-blue-500 cursor-pointer"
            >
              <option value={10000}>Every 10 Seconds (High Activity)</option>
              <option value={30000}>Every 30 Seconds (Recommended)</option>
              <option value={60000}>Every 1 Minute</option>
              <option value={300000}>Every 5 Minutes</option>
              <option value={0}>Manual Refresh Only (Disabled)</option>
            </select>
            <p className="text-[11px] text-slate-500 mt-1">
              When a caller hangs up, the dashboard automatically pulls the newly compiled incident dossier after the interval.
            </p>
          </div>
        </div>
      </div>

      {/* ── Demo / Simulation Mode ── */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-card space-y-4">
        <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2 border-b border-slate-100 pb-3">
          <Radio className="w-4 h-4 text-amber-600" />
          <span>Demonstration / Offline Simulation Mode</span>
        </h2>

        <div className="flex items-center justify-between gap-4">
          <div>
            <span className="text-xs font-bold text-slate-900 block">
              Enable Demo Simulation Data
            </span>
            <p className="text-xs text-slate-500 mt-0.5">
              Displays mock cases when the FastAPI backend is disconnected. When enabled, a visible <code className="text-amber-700 font-bold">DEMO MODE</code> badge is displayed.
            </p>
          </div>
          <button
            onClick={() => onToggleDemoMode(!isDemoMode)}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-sm ${
              isDemoMode
                ? 'bg-amber-100 text-amber-900 border border-amber-300'
                : 'bg-slate-100 text-slate-600 hover:text-slate-900 hover:bg-slate-200 border border-slate-200'
            }`}
          >
            {isDemoMode ? 'DEMO ACTIVE' : 'REAL DATA ONLY'}
          </button>
        </div>
      </div>

      {/* ── Telephony & IVR Reference ── */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-card space-y-3">
        <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2 border-b border-slate-100 pb-3">
          <PhoneCall className="w-4 h-4 text-emerald-600" />
          <span>Telephony & IVR Hotlines</span>
        </h2>

        <div className="text-xs text-slate-700 space-y-2">
          <p>
            • <strong>Inbound Webhook:</strong> Point Twilio Voice Webhook to <code className="text-blue-700 font-mono">https://&lt;domain&gt;/incoming-call</code> (HTTP POST).
          </p>
          <p>
            • <strong>Language Menu:</strong> 1 for Hindi (<code className="text-blue-700 font-mono">hi-IN</code>), 2 for English (<code className="text-blue-700 font-mono">en-IN</code>).
          </p>
          <p>
            • <strong>Emergency Directive:</strong> Citizen is automatically instructed to dial <strong className="text-slate-900 font-mono">1930</strong> and freeze bank accounts upon interview conclusion.
          </p>
        </div>
      </div>
    </div>
  );
};
