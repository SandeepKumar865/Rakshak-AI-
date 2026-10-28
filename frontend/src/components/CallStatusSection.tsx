import React, { useState, useEffect } from 'react';
import {
  Radio,
  Clock,
  CheckCircle2,
  AlertTriangle,
  PhoneForwarded,
  FileText,
  Volume2,
  ChevronRight,
  Sparkles,
  PhoneOff,
} from 'lucide-react';
import { CallRecord, CallStatusType } from '../types';

interface CallStatusSectionProps {
  currentCall: CallRecord | null;
  onViewReport: (reportId: string) => void;
  onUpdateCallStatus?: (updated: CallRecord) => void;
}

const STAGES: { key: CallStatusType; label: string }[] = [
  { key: 'initiated', label: 'Initiated' },
  { key: 'ringing', label: 'Ringing' },
  { key: 'in-progress', label: 'In Progress' },
  { key: 'completed', label: 'Completed' },
];

export const CallStatusSection: React.FC<CallStatusSectionProps> = ({
  currentCall,
  onViewReport,
  onUpdateCallStatus,
}) => {
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);

  // Timer when call is active
  useEffect(() => {
    if (!currentCall || currentCall.status === 'completed' || currentCall.status === 'failed') {
      return;
    }
    const timer = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [currentCall]);

  const formatTimer = (totalSeconds: number) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Helper for status index
  const getStageIndex = (status: CallStatusType) => {
    switch (status) {
      case 'initiated':
        return 0;
      case 'ringing':
        return 1;
      case 'in-progress':
        return 2;
      case 'completed':
        return 3;
      case 'failed':
        return -1;
      default:
        return 0;
    }
  };

  const currentIndex = currentCall ? getStageIndex(currentCall.status) : -1;

  // Manual demo stage advance helper for illustrative demonstration
  const handleAdvanceSimulation = () => {
    if (!currentCall || !onUpdateCallStatus) return;
    if (currentCall.status === 'initiated') {
      onUpdateCallStatus({ ...currentCall, status: 'ringing', stage: 'ringing' });
    } else if (currentCall.status === 'ringing') {
      onUpdateCallStatus({ ...currentCall, status: 'in-progress', stage: 'incident_narrative' });
    } else if (currentCall.status === 'in-progress') {
      const generatedReportId = currentCall.report_id || 'RAK-20261028-211CBC';
      onUpdateCallStatus({
        ...currentCall,
        status: 'completed',
        stage: 'completed',
        report_id: generatedReportId,
      });
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5 lg:p-6 flex flex-col justify-between">
      <div>
        {/* Module Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center justify-center font-bold">
              <Radio className="w-5 h-5 text-emerald-700 animate-pulse" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 leading-tight">
                Live Call Status Pipeline
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Real-time IVR state machine & progress telemetry
              </p>
            </div>
          </div>
          <span className="text-[11px] font-semibold uppercase px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
            Module 3
          </span>
        </div>

        {/* 5-Stage Visual Stepper */}
        <div className="mt-5">
          <div className="flex items-center justify-between relative">
            {/* Connecting line */}
            <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-slate-200 -translate-y-1/2 z-0" />

            {STAGES.map((s, idx) => {
              const isPassed = currentIndex > idx;
              const isCurrent = currentIndex === idx;
              const isFailed = currentCall?.status === 'failed';

              let circleClass = 'bg-white border-2 border-slate-300 text-slate-400';
              if (isFailed && isCurrent) {
                circleClass = 'bg-red-600 border-2 border-red-600 text-white';
              } else if (isPassed || (isCurrent && s.key === 'completed')) {
                circleClass = 'bg-emerald-600 border-2 border-emerald-600 text-white';
              } else if (isCurrent) {
                circleClass = 'bg-blue-600 border-2 border-blue-600 text-white ring-4 ring-blue-100';
              }

              return (
                <div key={s.key} className="flex flex-col items-center relative z-10">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${circleClass}`}
                  >
                    {isPassed || (isCurrent && s.key === 'completed') ? (
                      <CheckCircle2 className="w-4 h-4 text-white" />
                    ) : (
                      idx + 1
                    )}
                  </div>
                  <span
                    className={`text-[11px] font-semibold mt-1.5 whitespace-nowrap ${
                      isCurrent
                        ? isFailed
                          ? 'text-red-700'
                          : 'text-blue-900'
                        : isPassed
                        ? 'text-slate-800'
                        : 'text-slate-400'
                    }`}
                  >
                    {s.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Active Call Details or Standby Card */}
        {currentCall ? (
          <div className="mt-6 bg-slate-50 border border-slate-200 rounded-xl p-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200/60">
              <div className="flex items-center space-x-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping" />
                <span className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                  Active Intake Session
                </span>
              </div>
              <div className="flex items-center space-x-1.5 text-xs text-slate-600 font-mono bg-white px-2 py-0.5 rounded border border-slate-200">
                <Clock className="w-3.5 h-3.5 text-slate-500" />
                <span>{formatTimer(elapsedSeconds)}</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 mt-3 text-xs">
              <div>
                <span className="text-slate-500 block text-[11px]">Destination:</span>
                <span className="font-mono font-semibold text-slate-900">
                  {currentCall.destination}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block text-[11px]">Language:</span>
                <span className="font-semibold text-slate-900 uppercase">
                  {currentCall.language === 'hi' ? 'हिन्दी (Hindi)' : 'English'}
                </span>
              </div>
              <div className="col-span-2">
                <span className="text-slate-500 block text-[11px]">Call SID:</span>
                <span className="font-mono text-[11px] text-slate-700 break-all">
                  {currentCall.call_sid}
                </span>
              </div>
            </div>

            {/* Simulated Audio Frequency Indicator when in progress */}
            {currentCall.status === 'in-progress' && (
              <div className="mt-3 bg-white border border-slate-200 rounded-lg p-2.5 flex items-center justify-between">
                <div className="flex items-center space-x-2 text-xs text-blue-900 font-medium">
                  <Volume2 className="w-4 h-4 text-blue-700 animate-bounce" />
                  <span>Transcribing Voice (# Submission Active)...</span>
                </div>
                <div className="flex items-center space-x-1">
                  <span className="w-1 h-3 bg-blue-600 rounded-full animate-pulse" />
                  <span className="w-1 h-5 bg-blue-700 rounded-full animate-pulse delay-75" />
                  <span className="w-1 h-4 bg-blue-500 rounded-full animate-pulse delay-150" />
                  <span className="w-1 h-6 bg-blue-800 rounded-full animate-pulse delay-100" />
                  <span className="w-1 h-2 bg-blue-400 rounded-full animate-pulse delay-200" />
                </div>
              </div>
            )}

            {/* Completed Banner with Direct Dossier Link */}
            {currentCall.status === 'completed' && (
              <div className="mt-3 bg-emerald-50 border border-emerald-200 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2 text-xs font-semibold text-emerald-900">
                    <CheckCircle2 className="w-4 h-4 text-emerald-700" />
                    <span>Complaint Intake Complete!</span>
                  </div>
                  {currentCall.report_id && (
                    <button
                      onClick={() => onViewReport(currentCall.report_id!)}
                      className="flex items-center space-x-1.5 text-xs font-semibold bg-emerald-700 hover:bg-emerald-800 text-white px-3 py-1.5 rounded-md shadow-xs transition-colors"
                    >
                      <FileText className="w-3.5 h-3.5" />
                      <span>View Report {currentCall.report_id}</span>
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Illustrative Walkthrough Step Button */}
            {currentCall.status !== 'completed' && currentCall.status !== 'failed' && (
              <div className="mt-3 pt-2 border-t border-slate-200/60 flex items-center justify-between">
                <span className="text-[11px] text-slate-500">
                  Status: <strong className="uppercase text-slate-800">{currentCall.status}</strong>
                </span>
                <button
                  onClick={handleAdvanceSimulation}
                  className="text-xs text-blue-700 hover:text-blue-900 font-semibold flex items-center space-x-1 bg-blue-50 hover:bg-blue-100 px-2.5 py-1 rounded border border-blue-200 transition-colors"
                >
                  <span>Step To Next Stage</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="mt-6 bg-slate-50 border border-dashed border-slate-300 rounded-xl p-6 text-center">
            <PhoneForwarded className="w-8 h-8 text-slate-400 mx-auto" />
            <h4 className="text-xs font-bold text-slate-800 mt-2 uppercase tracking-wide">
              Awaiting Outbound Call Trigger
            </h4>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              Enter a destination number in Module 2 to initiate a first-responder session. Call progression will update here automatically.
            </p>
          </div>
        )}
      </div>

      <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
        <span>Telephony Engine: Twilio Voice + Google STT</span>
        <span>Isolated Sessions by CallSid</span>
      </div>
    </div>
  );
};
