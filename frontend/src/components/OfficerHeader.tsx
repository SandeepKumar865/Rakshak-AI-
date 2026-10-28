import React from 'react';
import { ShieldCheck, LogOut, Radio, UserCheck } from 'lucide-react';
import { OfficerUser } from '../types';

interface OfficerHeaderProps {
  officer: OfficerUser;
  onLogout: () => void;
  isBackendConnected: boolean;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export const OfficerHeader: React.FC<OfficerHeaderProps> = ({
  officer,
  onLogout,
  isBackendConnected,
  onRefresh,
  isRefreshing,
}) => {
  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
      {/* Top Ministry / Department Banner */}
      <div className="bg-slate-900 text-slate-300 text-[11px] px-4 py-1.5 flex justify-between items-center font-medium tracking-wide">
        <div className="flex items-center space-x-2">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>गृह मंत्रालय | Ministry of Home Affairs — Indian Cyber Crime Coordination Centre (I4C)</span>
        </div>
        <div className="hidden md:flex items-center space-x-3 text-slate-400 text-[11px]">
          <span>National Cyber Crime Reporting Helpline: 1930</span>
          <span>•</span>
          <span>Portal: cybercrime.gov.in</span>
        </div>
      </div>

      {/* Main Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        {/* Brand identity */}
        <div className="flex items-center space-x-3.5">
          <div className="w-10 h-10 rounded-lg bg-blue-900 text-white flex items-center justify-center font-bold shadow-sm ring-1 ring-blue-800">
            <ShieldCheck className="w-6 h-6 text-blue-200" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-lg font-bold text-slate-900 tracking-tight leading-none">
                RAKSHAK AI
              </h1>
              <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200">
                Officer Desk
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1 leading-none">
              रक्षक एआई — AI-Powered Voice Cybercrime Assistance & Operations Console
            </p>
          </div>
        </div>

        {/* Officer Identity & Session Info */}
        <div className="flex items-center space-x-3 self-end md:self-center">
          {/* Backend link pill */}
          <div
            className={`flex items-center space-x-1.5 text-xs px-2.5 py-1 rounded-full border ${
              isBackendConnected
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : 'bg-amber-50 text-amber-700 border-amber-200'
            }`}
            title={isBackendConnected ? 'Connected to FastAPI Backend (port 8000)' : 'Backend link offline or fallback mode'}
          >
            <Radio className="w-3.5 h-3.5" />
            <span className="font-medium">
              {isBackendConnected ? 'Backend Live' : 'Illustrative Mode'}
            </span>
          </div>

          {/* Officer badge card */}
          <div className="flex items-center space-x-3 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-lg">
            <div className="w-8 h-8 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center font-bold text-xs">
              <UserCheck className="w-4 h-4 text-slate-700" />
            </div>
            <div className="text-left">
              <div className="text-xs font-semibold text-slate-900 flex items-center space-x-1.5">
                <span>{officer.name}</span>
                <span className="text-[10px] bg-slate-200 text-slate-700 px-1.5 py-0.2 rounded font-mono">
                  {officer.badge_number}
                </span>
              </div>
              <div className="text-[11px] text-slate-500 leading-tight">
                {officer.role} • {officer.station}
              </div>
            </div>
          </div>

          {/* Sign Out Button */}
          <button
            onClick={onLogout}
            className="flex items-center space-x-1.5 text-xs text-slate-600 hover:text-red-700 px-3 py-2 rounded-lg border border-slate-200 hover:border-red-200 hover:bg-red-50 transition-colors"
            title="Terminate officer session"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span className="hidden sm:inline font-medium">Sign Out</span>
          </button>
        </div>
      </div>
    </header>
  );
};
