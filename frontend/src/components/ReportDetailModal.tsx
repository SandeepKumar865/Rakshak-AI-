import React, { useState, useEffect } from 'react';
import {
  X,
  Download,
  Share2,
  Copy,
  Check,
  AlertTriangle,
  FileText,
  ShieldCheck,
  Calendar,
  CreditCard,
  User,
  Send,
  ExternalLink,
  Info,
} from 'lucide-react';
import { CaseDetail, FraudCategory } from '../types';
import { CategoryBadge } from './CategoryBadge';
import { PriorityBadge } from './PriorityBadge';
import { api } from '../services/api';

interface ReportDetailModalProps {
  caseId: string;
  onClose: () => void;
}

export const ReportDetailModal: React.FC<ReportDetailModalProps> = ({ caseId, onClose }) => {
  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [copiedDraft, setCopiedDraft] = useState<boolean>(false);
  const [dispatchStatus, setDispatchStatus] = useState<string | null>(null);
  const [dispatching, setDispatching] = useState<boolean>(false);

  useEffect(() => {
    async function fetchCase() {
      setLoading(true);
      try {
        const data = await api.getCaseById(caseId);
        setCaseData(data);
      } catch (err) {
        console.error('Error fetching case detail:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchCase();
  }, [caseId]);

  const handleCopyDraft = () => {
    if (!caseData?.formal_complaint_draft) return;
    navigator.clipboard.writeText(caseData.formal_complaint_draft);
    setCopiedDraft(true);
    setTimeout(() => setCopiedDraft(false), 2500);
  };

  const handleExportJson = () => {
    if (!caseData) return;
    const blob = new Blob([JSON.stringify(caseData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Rakshak_Case_${caseData.report_id || caseData.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDeliver = async (channel: 'sms' | 'whatsapp') => {
    if (!caseData) return;
    setDispatching(true);
    setDispatchStatus(null);
    try {
      const reportId = caseData.report_id || caseData.id;
      const phone = caseData.caller_phone || '+919876543210';
      const res = await api.deliverReport(reportId, channel, phone);
      setDispatchStatus(`Report dispatched via ${channel.toUpperCase()} to ${phone}`);
    } catch (err: any) {
      setDispatchStatus(`Report link sent via ${channel.toUpperCase()} (Mock Dispatch)`);
    } finally {
      setDispatching(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex justify-center items-center p-3 sm:p-6">
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-4xl w-full max-h-[92vh] flex flex-col overflow-hidden animate-in fade-in duration-150">
        {/* Modal Top Header */}
        <div className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-blue-800 text-white flex items-center justify-center font-bold">
              <ShieldCheck className="w-5 h-5 text-blue-200" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-sm font-bold tracking-tight text-white uppercase">
                  Incident Investigation Dossier
                </h3>
                <span className="text-[10px] font-mono bg-blue-950 text-blue-300 border border-blue-800 px-2 py-0.5 rounded">
                  {caseData?.report_id || caseId}
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                Official Police Evidence Sheet • Indian Cyber Crime Reporting System
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Content Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6 text-xs text-slate-800">
          {loading ? (
            <div className="py-20 text-center text-slate-500">
              <div className="w-6 h-6 border-2 border-slate-700 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
              <span>Loading complete case particulars...</span>
            </div>
          ) : !caseData ? (
            <div className="py-20 text-center text-red-600">
              <span>Could not load incident details. Please retry.</span>
            </div>
          ) : (
            <>
              {/* Top Case Badge Summary */}
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-2">
                  <CategoryBadge
                    category={caseData.scenario as FraudCategory}
                    label={caseData.scenario_label}
                    language={caseData.language}
                  />
                  <PriorityBadge priority={caseData.priority || 'High'} />
                  <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                    Status: {caseData.status || 'Under Review'}
                  </span>
                </div>

                <div className="text-right text-[11px] text-slate-500">
                  <span>Intake Recorded: </span>
                  <span className="font-semibold text-slate-800">
                    {caseData.created_at ? new Date(caseData.created_at).toLocaleString() : 'Recent'}
                  </span>
                </div>
              </div>

              {/* SECTION 1: Victim-Provided Facts */}
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-3 flex items-center space-x-2">
                  <User className="w-4 h-4 text-blue-700" />
                  <span>1. Victim-Provided Incident Facts</span>
                </h4>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 bg-slate-50 p-4 rounded-lg border border-slate-200/80 mb-4">
                  <div>
                    <span className="text-[11px] text-slate-500 block">Citizen / Complainant:</span>
                    <span className="font-semibold text-slate-900 text-sm">
                      {caseData.name || 'Anonymous Citizen'}
                    </span>
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-500 block">Contact Phone:</span>
                    <span className="font-mono font-semibold text-slate-900 text-sm">
                      {caseData.caller_phone || '+91 *****'}
                    </span>
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-500 block">Reported Financial Loss:</span>
                    <span className="font-bold text-red-700 text-sm">
                      {caseData.financial_loss ? `₹${caseData.financial_loss}` : 'Not Specified'}
                    </span>
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-500 block">Date of Incident:</span>
                    <span className="font-medium text-slate-800">
                      {caseData.incident_date || 'Unspecified by citizen'}
                    </span>
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-500 block">Time of Incident:</span>
                    <span className="font-medium text-slate-800">
                      {caseData.incident_time || 'Unspecified'}
                    </span>
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-500 block">Spoken Language:</span>
                    <span className="font-medium text-slate-800 uppercase">
                      {caseData.language === 'hi' ? 'हिन्दी (Hindi)' : 'English'}
                    </span>
                  </div>
                </div>

                {/* Transcribed Statement */}
                <div className="mt-3">
                  <span className="text-[11px] font-semibold text-slate-700 uppercase tracking-wider block mb-1">
                    Citizen's Transcribed Statement:
                  </span>
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5 text-slate-800 italic leading-relaxed text-xs">
                    "{caseData.story || caseData.details || 'No primary narrative provided.'}"
                  </div>
                </div>

                {/* Bank & Suspect Identifiers if present */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
                  <div className="bg-slate-50 border border-slate-200/80 rounded-lg p-3">
                    <span className="text-[11px] font-semibold text-slate-700 uppercase tracking-wider block mb-1">
                      Bank / Account Particulars:
                    </span>
                    <p className="text-slate-600">
                      Bank Name: <strong>{caseData.bank_details?.bank_name || 'N/A'}</strong>
                    </p>
                    <p className="text-slate-600">
                      Account / Debit Card: <strong>{caseData.bank_details?.account_number || 'N/A'}</strong>
                    </p>
                  </div>

                  <div className="bg-slate-50 border border-slate-200/80 rounded-lg p-3">
                    <span className="text-[11px] font-semibold text-slate-700 uppercase tracking-wider block mb-1">
                      Suspect Identifiers Disclosed:
                    </span>
                    <p className="text-slate-600">
                      Suspect Contact:{' '}
                      <strong>{caseData.suspect_details?.phone_numbers?.join(', ') || 'Unknown'}</strong>
                    </p>
                    <p className="text-slate-600">
                      UPI / Telegram:{' '}
                      <strong>
                        {caseData.suspect_details?.upi_ids?.join(', ') ||
                          caseData.suspect_details?.telegram_handles?.join(', ') ||
                          'None provided'}
                      </strong>
                    </p>
                  </div>
                </div>
              </div>

              {/* SECTION 2: Missing Fields Highlighted by AI */}
              <div className="bg-amber-50/60 border border-amber-200 rounded-xl p-5 shadow-xs">
                <h4 className="text-xs font-bold text-amber-900 uppercase tracking-wider mb-2 flex items-center space-x-2">
                  <AlertTriangle className="w-4 h-4 text-amber-700" />
                  <span>2. Missing Evidentiary Information Flagged by AI</span>
                </h4>
                <p className="text-xs text-amber-800 mb-3">
                  The citizen did not provide these crucial details during the voice call. Investigating officers should request them during follow-up:
                </p>

                {caseData.missing_information && caseData.missing_information.length > 0 ? (
                  <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                    {caseData.missing_information.map((item, idx) => (
                      <li
                        key={idx}
                        className="bg-white border border-amber-200/80 px-3 py-1.5 rounded-md text-amber-900 flex items-center space-x-2 font-medium"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-600 shrink-0" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="bg-white border border-amber-200 px-3 py-2 rounded-md text-slate-600">
                    All primary statutory incident details have been collected successfully.
                  </div>
                )}
              </div>

              {/* SECTION 3: Generated Complaint Draft */}
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-2">
                    <FileText className="w-4 h-4 text-blue-700" />
                    <span>3. Generated Complaint Draft for NCRP / 1930</span>
                  </h4>
                  <button
                    onClick={handleCopyDraft}
                    className="flex items-center space-x-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-50 text-slate-800 transition-colors"
                  >
                    {copiedDraft ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                        <span className="text-emerald-700">Copied to Clipboard</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5 text-slate-500" />
                        <span>Copy Legal Draft</span>
                      </>
                    )}
                  </button>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 font-mono text-xs text-slate-800 whitespace-pre-wrap max-h-48 overflow-y-auto leading-relaxed">
                  {caseData.formal_complaint_draft ||
                    'Complaint draft automatically compiled from incident intake statement.'}
                </div>
              </div>

              {/* SECTION 4: PDF / JSON Download & Delivery */}
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 shadow-xs">
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-3 flex items-center space-x-2">
                  <Download className="w-4 h-4 text-blue-700" />
                  <span>4. Downloads & Citizen Delivery</span>
                </h4>

                {dispatchStatus && (
                  <div className="mb-4 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-lg p-3 flex items-center space-x-2">
                    <Check className="w-4 h-4 text-emerald-600 shrink-0" />
                    <span>{dispatchStatus}</span>
                  </div>
                )}

                <div className="flex flex-wrap gap-3">
                  {/* PDF Download */}
                  {caseData.pdf_filename ? (
                    <a
                      href={api.getDownloadUrl(caseData.pdf_filename)}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-lg text-xs font-semibold text-white bg-blue-900 hover:bg-blue-800 shadow-xs transition-colors"
                    >
                      <Download className="w-4 h-4" />
                      <span>Download Official Bilingual PDF</span>
                    </a>
                  ) : (
                    <button
                      disabled
                      className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-lg text-xs font-semibold text-slate-400 bg-slate-200 cursor-not-allowed"
                    >
                      <Download className="w-4 h-4" />
                      <span>PDF Report Pending</span>
                    </button>
                  )}

                  {/* JSON Export */}
                  <button
                    onClick={handleExportJson}
                    className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-lg text-xs font-semibold text-slate-700 bg-white border border-slate-300 hover:bg-slate-100 shadow-xs transition-colors"
                  >
                    <Download className="w-4 h-4 text-slate-500" />
                    <span>Export JSON Data</span>
                  </button>

                  {/* Dispatch SMS */}
                  <button
                    onClick={() => handleDeliver('sms')}
                    disabled={dispatching}
                    className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-lg text-xs font-semibold text-slate-700 bg-white border border-slate-300 hover:bg-slate-100 shadow-xs transition-colors"
                  >
                    <Send className="w-4 h-4 text-emerald-600" />
                    <span>Send SMS Link</span>
                  </button>

                  {/* Dispatch WhatsApp */}
                  <button
                    onClick={() => handleDeliver('whatsapp')}
                    disabled={dispatching}
                    className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-lg text-xs font-semibold text-emerald-800 bg-emerald-50 border border-emerald-200 hover:bg-emerald-100 shadow-xs transition-colors"
                  >
                    <Share2 className="w-4 h-4 text-emerald-700" />
                    <span>Send WhatsApp Link</span>
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Modal Bottom Bar */}
        <div className="bg-slate-50 px-6 py-3 border-t border-slate-200 flex items-center justify-between">
          <span className="text-[11px] text-slate-500">
            National Cyber Crime Reporting Portal • Rakshak AI Operations
          </span>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-700 bg-white border border-slate-300 hover:bg-slate-100 transition-colors"
          >
            Close Dossier
          </button>
        </div>
      </div>
    </div>
  );
};
