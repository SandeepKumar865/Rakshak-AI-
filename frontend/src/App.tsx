import React, { useState, useEffect, useCallback } from 'react';
import { OfficerHeader } from './components/OfficerHeader';
import { OfficerLogin } from './components/OfficerLogin';
import { DemoCallSection } from './components/DemoCallSection';
import { CallStatusSection } from './components/CallStatusSection';
import { ReportListSection } from './components/ReportListSection';
import { ReportDetailModal } from './components/ReportDetailModal';
import { OfficerUser, CallRecord, CaseSummary, HealthStatus } from './types';
import { api } from './services/api';

const SESSION_STORAGE_KEY = 'rakshak_officer_session';

export function App() {
  // ── Session Management (Module 1: Login) ──
  const [officer, setOfficer] = useState<OfficerUser | null>(() => {
    try {
      const stored = localStorage.getItem(SESSION_STORAGE_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  // ── Call State (Module 2 & 3: Demo Call & Call Status) ──
  const [currentCall, setCurrentCall] = useState<CallRecord | null>(null);

  // ── Reports State (Module 4: Report List) ──
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [loadingCases, setLoadingCases] = useState<boolean>(true);

  // ── Report Detail Modal State (Module 5: Report Detail) ──
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);

  // ── Telephony & Backend Connectivity ──
  const [isBackendConnected, setIsBackendConnected] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  // Load cases and check health
  const refreshData = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const [casesRes, healthRes] = await Promise.all([
        api.getCases(),
        api.getHealth(),
      ]);
      setCases(casesRes);
      setIsBackendConnected(healthRes.api_connected);
    } catch (err) {
      console.warn('Dashboard data fetch warning:', err);
      setIsBackendConnected(false);
    } finally {
      setLoadingCases(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    refreshData();
    // Auto-refresh cases every 20 seconds
    const interval = setInterval(refreshData, 20000);
    return () => clearInterval(interval);
  }, [refreshData]);

  // Handle Login
  const handleLoginSuccess = (user: OfficerUser) => {
    setOfficer(user);
    try {
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(user));
    } catch (e) {
      // ignore
    }
  };

  // Handle Logout
  const handleLogout = async () => {
    await api.logout();
    setOfficer(null);
    setCurrentCall(null);
    setSelectedCaseId(null);
    try {
      localStorage.removeItem(SESSION_STORAGE_KEY);
    } catch (e) {
      // ignore
    }
  };

  // Handle Call Initiation from Module 2
  const handleCallInitiated = (newCall: CallRecord) => {
    setCurrentCall(newCall);
    // If call completed or has a report id, refresh case list so it reflects in Module 4
    refreshData();
  };

  // If officer is not authenticated, render Login view (Module 1)
  if (!officer) {
    return <OfficerLogin onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col font-sans">
      {/* ── Official Officer Header ── */}
      <OfficerHeader
        officer={officer}
        onLogout={handleLogout}
        isBackendConnected={isBackendConnected}
        onRefresh={refreshData}
        isRefreshing={isRefreshing}
      />

      {/* ── Officer Dashboard Main Content ── */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {/* Core Operations Grid: Module 2 (Demo Call) & Module 3 (Call Status) */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
          {/* Module 2: Demo Call */}
          <DemoCallSection
            officer={officer}
            onCallInitiated={handleCallInitiated}
          />

          {/* Module 3: Call Status */}
          <CallStatusSection
            currentCall={currentCall}
            onViewReport={(reportId) => setSelectedCaseId(reportId)}
            onUpdateCallStatus={(updated) => {
              setCurrentCall(updated);
              if (updated.status === 'completed') {
                refreshData();
              }
            }}
          />
        </div>

        {/* Module 4: Report List with Search & Filters */}
        <ReportListSection
          cases={cases}
          loading={loadingCases}
          onSelectCase={(caseId) => setSelectedCaseId(caseId)}
          onRefresh={refreshData}
        />
      </main>

      {/* Module 5: Report Detail (Dossier Investigation View / Modal) */}
      {selectedCaseId && (
        <ReportDetailModal
          caseId={selectedCaseId}
          onClose={() => setSelectedCaseId(null)}
        />
      )}

      {/* Department Footer */}
      <footer className="bg-white border-t border-slate-200 py-4 px-6 text-center text-xs text-slate-500 mt-auto">
        <p>
          भारतीय साइबर अपराध समन्वय केंद्र (I4C) • Indian Cyber Crime Reporting Portal • Rakshak AI Operations Desk
        </p>
      </footer>
    </div>
  );
}

export default App;
