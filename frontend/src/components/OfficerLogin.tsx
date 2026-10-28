import React, { useState } from 'react';
import { Shield, Lock, BadgeCheck, AlertCircle, ArrowRight, KeyRound } from 'lucide-react';
import { OfficerUser, OfficerRole } from '../types';
import { api } from '../services/api';

interface OfficerLoginProps {
  onLoginSuccess: (officer: OfficerUser) => void;
}

export const OfficerLogin: React.FC<OfficerLoginProps> = ({ onLoginSuccess }) => {
  const [badgeNumber, setBadgeNumber] = useState<string>('CYBER-4091');
  const [password, setPassword] = useState<string>('••••••••');
  const [role, setRole] = useState<OfficerRole>('Cyber Crime Officer');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!badgeNumber.trim()) {
      setError('Please enter your official Officer Badge Number');
      return;
    }

    setLoading(true);
    try {
      const res = await api.login(badgeNumber.trim(), role, password);
      onLoginSuccess(res.officer);
    } catch (err: any) {
      setError(err?.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickDemoFill = (selectedRole: OfficerRole, badge: string) => {
    setBadgeNumber(badge);
    setRole(selectedRole);
    setPassword('Rakshak@2026');
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      {/* Official Government Top Seal */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="mx-auto w-16 h-16 rounded-2xl bg-blue-900 text-white flex items-center justify-center shadow-md ring-4 ring-blue-100">
          <Shield className="w-10 h-10 text-blue-200" />
        </div>
        <h2 className="mt-4 text-2xl font-bold tracking-tight text-slate-900">
          RAKSHAK AI — CYBERCELL DESK
        </h2>
        <p className="mt-1 text-xs text-slate-500 font-medium uppercase tracking-wider">
          National Cyber Crime Reporting Portal • First Responder Operations
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 shadow-sm border border-slate-200 rounded-2xl sm:px-10">
          <div className="mb-6 pb-4 border-b border-slate-100">
            <h3 className="text-base font-semibold text-slate-900 flex items-center space-x-2">
              <BadgeCheck className="w-5 h-5 text-blue-700" />
              <span>Officer Authentication</span>
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Restricted portal for verified cybercell investigating officers and duty desk personnel.
            </p>
          </div>

          {error && (
            <div className="mb-5 bg-red-50 border border-red-200 text-red-800 text-xs rounded-lg p-3 flex items-start space-x-2">
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Officer Badge Number */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                Officer Badge Number / ID
              </label>
              <div className="mt-1.5 relative rounded-md">
                <input
                  type="text"
                  value={badgeNumber}
                  onChange={(e) => setBadgeNumber(e.target.value)}
                  placeholder="e.g. CYBER-4091"
                  required
                  className="block w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm font-mono text-slate-900 placeholder:text-slate-400 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700"
                />
              </div>
            </div>

            {/* Officer Role Selection (Role-Based Access) */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                Designation / Assigned Role
              </label>
              <div className="mt-1.5">
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value as OfficerRole)}
                  className="block w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 bg-white focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700 font-medium"
                >
                  <option value="Cyber Crime Officer">Cyber Crime Officer (First Responder Desk)</option>
                  <option value="Investigating Officer (IO)">Investigating Officer (IO - Evidence & Docket)</option>
                  <option value="Superintendent of Police">Superintendent of Police (Supervisory)</option>
                </select>
              </div>
            </div>

            {/* Password / Security Key */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                Department PIN / Security Token
              </label>
              <div className="mt-1.5 relative">
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="block w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm font-mono text-slate-900 placeholder:text-slate-400 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700"
                />
              </div>
            </div>

            {/* Login button */}
            <div className="pt-2">
              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center items-center py-2.5 px-4 rounded-lg text-sm font-semibold text-white bg-slate-900 hover:bg-slate-800 shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-900 disabled:opacity-50 transition-colors"
              >
                {loading ? (
                  <span className="flex items-center space-x-2">
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                    <span>Verifying Credentials...</span>
                  </span>
                ) : (
                  <span className="flex items-center space-x-2">
                    <span>Sign In to Cybercell Console</span>
                    <ArrowRight className="w-4 h-4" />
                  </span>
                )}
              </button>
            </div>
          </form>

          {/* Quick Demo Credentials for Evaluation */}
          <div className="mt-6 pt-5 border-t border-slate-100">
            <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
              <KeyRound className="w-3.5 h-3.5 text-slate-400" />
              <span>Quick Evaluation Roles (Click to load):</span>
            </p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                onClick={() => handleQuickDemoFill('Cyber Crime Officer', 'CYBER-4091')}
                className="px-2.5 py-1.5 text-left rounded border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 font-medium transition-colors"
              >
                <span className="block font-semibold text-slate-900">Desk Officer</span>
                <span className="text-[10px] text-slate-500">CYBER-4091</span>
              </button>
              <button
                type="button"
                onClick={() => handleQuickDemoFill('Investigating Officer (IO)', 'IO-VERMA-104')}
                className="px-2.5 py-1.5 text-left rounded border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 font-medium transition-colors"
              >
                <span className="block font-semibold text-slate-900">Investigating IO</span>
                <span className="text-[10px] text-slate-500">IO-VERMA-104</span>
              </button>
            </div>
          </div>

          {/* Compliance & Security notice */}
          <div className="mt-5 text-center">
            <div className="flex items-center justify-center space-x-1 text-[11px] text-slate-400">
              <Lock className="w-3 h-3 text-slate-400" />
              <span>Official Department System • IT Act 2000 Section 43/66</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
