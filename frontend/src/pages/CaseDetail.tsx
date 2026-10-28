import React, { useState, useEffect } from 'react';
import {
  ArrowLeft,
  Download,
  ExternalLink,
  ShieldAlert,
  Copy,
  Check,
  Building,
  UserCheck,
  AlertCircle,
  FileCheck2,
  Calendar,
  Clock,
  Printer,
  Landmark,
  MessageSquare,
} from 'lucide-react';
import { CaseDetail as CaseDetailType, CaseStatus } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { PriorityBadge } from '../components/PriorityBadge';
import { CategoryBadge } from '../components/CategoryBadge';
import { api } from '../services/api';

interface CaseDetailProps {
  caseId: string;
  onBack: () => void;
  onRefreshList: () => void;
}

export const CaseDetail: React.FC<CaseDetailProps> = ({
  caseId,
  onBack,
  onRefreshList,
}) => {
  const [caseData, setCaseData] = useState<CaseDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [copiedDraft, setCopiedDraft] = useState(false);
  const [copiedId, setCopiedId] = useState(false);

  useEffect(() => {
    let mounted = true;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await api.getCaseById(caseId);
        if (mounted) setCaseData(data);
      } catch (err: any) {
        if (mounted) setError(err.message || 'Failed to load case investigation');
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => {
      mounted = false;
    };
  }, [caseId]);

  const handleStatusChange = async (newStatus: CaseStatus) => {
    if (!caseData) return;
    setUpdatingStatus(true);
    try {
      await api.updateCaseStatus(caseData.id || caseId, newStatus);
      setCaseData((prev) => (prev ? { ...prev, status: newStatus } : null));
      onRefreshList();
    } catch (err: any) {
      alert(`Status update failed: ${err.message || 'Error'}`);
    } finally {
      setUpdatingStatus(false);
    }
  };

  const copyToClipboard = (text: string, type: 'draft' | 'id') => {
    navigator.clipboard.writeText(text);
    if (type === 'draft') {
      setCopiedDraft(true);
      setTimeout(() => setCopiedDraft(false), 2000);
    } else {
      setCopiedId(true);
      setTimeout(() => setCopiedId(false), 2000);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  if (loading) {
    return (
      <div className="p-16 text-center space-y-4">
        <div className="inline-block w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-sm text-slate-500">Loading case dossier #{caseId}...</p>
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="p-12 bg-white border border-slate-200 rounded-2xl text-center space-y-4 shadow-card">
        <AlertCircle className="w-12 h-12 text-rose-500 mx-auto" />
        <h2 className="text-lg font-bold text-slate-900">Case Record Not Found</h2>
        <p className="text-xs text-slate-500 max-w-md mx-auto">
          {error || `The requested case #${caseId} could not be retrieved from the database.`}
        </p>
        <button
          onClick={onBack}
          className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-800 transition-colors"
        >
          Return to Complaints
        </button>
      </div>
    );
  }

  const llm = caseData.llm_analysis;
  const bank = caseData.bank_details || llm?.bank_details;
  const suspect = caseData.suspect_details || llm?.suspect_details;
  const missingInfo = caseData.missing_information || llm?.missing_information || [];
  const formalDraft = caseData.formal_complaint_draft || llm?.formal_complaint_draft;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* ── Action Top Bar ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 no-print">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-2 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors group"
        >
          <ArrowLeft className="w-4 h-4 text-blue-600 group-hover:-translate-x-1 transition-transform" />
          <span>Back to Complaints</span>
        </button>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Status Update Dropdown */}
          <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-xl px-3 py-1.5 shadow-sm">
            <span className="text-xs text-slate-500 font-medium">Case Status:</span>
            <select
              value={caseData.status}
              disabled={updatingStatus}
              onChange={(e) => handleStatusChange(e.target.value as CaseStatus)}
              className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-xs font-semibold text-slate-800 focus:outline-none focus:border-blue-500 cursor-pointer disabled:opacity-50"
            >
              <option value="New">New</option>
              <option value="Under Review">Under Review</option>
              <option value="Investigating">Investigating</option>
              <option value="Resolved">Resolved</option>
              <option value="Closed">Closed</option>
            </select>
          </div>

          {/* Print Button */}
          <button
            onClick={handlePrint}
            className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 flex items-center gap-1.5 shadow-sm transition-colors"
            title="Print Case Investigation Record"
          >
            <Printer className="w-3.5 h-3.5 text-slate-500" />
            <span>Print Dossier</span>
          </button>

          {/* PDF Buttons */}
          {caseData.pdf_download_url ? (
            <>
              <a
                href={caseData.pdf_download_url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 flex items-center gap-1.5 shadow-sm transition-colors"
                title="Preview PDF in browser tab"
              >
                <ExternalLink className="w-3.5 h-3.5 text-slate-500" />
                <span>Open Report</span>
              </a>

              <a
                href={caseData.pdf_download_url}
                download
                className="px-4 py-2 rounded-xl text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white flex items-center gap-2 shadow-sm transition-colors"
                title="Download verified official bilingual PDF"
              >
                <Download className="w-4 h-4" />
                <span>Download Official Report</span>
              </a>
            </>
          ) : (
            <span className="text-xs text-slate-400 px-3 py-1.5 rounded-lg bg-slate-100 border border-slate-200">
              PDF report not generated yet
            </span>
          )}
        </div>
      </div>

      {/* ── Case Header Banner ── */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-card">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="text-xs font-mono text-blue-700 font-bold bg-blue-50 px-2.5 py-1 rounded-md border border-blue-200 flex items-center gap-1.5">
                <span>{caseData.report_id || caseData.id}</span>
                <button
                  onClick={() => copyToClipboard(caseData.report_id || caseData.id, 'id')}
                  title="Copy Case ID"
                  className="hover:text-blue-900"
                >
                  {copiedId ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3 text-slate-400" />}
                </button>
              </span>
              <PriorityBadge priority={caseData.priority} />
              <StatusBadge status={caseData.status} />
              <CategoryBadge
                category={caseData.scenario || 'GENERAL_FRAUD'}
                label={caseData.scenario_label}
                labelHi={caseData.scenario_label_hi}
              />
            </div>

            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Case #{caseData.report_id || caseData.id}: {caseData.name || 'Anonymous Citizen'}
            </h1>
            <p className="text-xs text-slate-500 mt-1 font-mono">
              Intake Logged: {caseData.started_at || caseData.created_at || 'Recent session'} • Telephony SID:{' '}
              {caseData.call_sid || 'Direct Outbound'}
            </p>
          </div>

          <div className="border-t lg:border-t-0 lg:border-l border-slate-200 pt-3 lg:pt-0 lg:pl-6">
            <span className="text-xs text-slate-500 uppercase font-semibold block">
              Estimated Financial Loss
            </span>
            <span className="text-xl lg:text-2xl font-extrabold text-rose-600 font-mono">
              {caseData.financial_loss || 'Not specified'}
            </span>
          </div>
        </div>
      </div>

      {/* ── Grid: Citizen & Evidentiary Details ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Citizen Particulars & Emergency Directives */}
        <div className="space-y-6">
          {/* Citizen Information Card */}
          <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-card space-y-4">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2 border-b border-slate-100 pb-3">
              <UserCheck className="w-4 h-4 text-blue-600" />
              <span>Citizen Information</span>
            </h2>

            <div className="space-y-3 text-xs">
              <div>
                <span className="text-slate-500 block mb-0.5">Caller / Victim Name:</span>
                <span className="text-sm font-semibold text-slate-900">
                  {caseData.name || 'Anonymous Citizen'}
                </span>
              </div>

              <div>
                <span className="text-slate-500 block mb-0.5">Contact Number:</span>
                <span className="font-mono text-slate-900 font-semibold">
                  {caseData.caller_phone_masked || caseData.caller_phone || 'Masked for privacy'}
                </span>
              </div>

              <div>
                <span className="text-slate-500 block mb-0.5">Interview Language:</span>
                <span className="text-slate-800 font-medium">
                  {caseData.language === 'hi' ? 'Hindi (हिन्दी)' : 'English'}
                </span>
              </div>

              <div>
                <span className="text-slate-500 block mb-0.5">Twilio Call SID:</span>
                <span className="font-mono text-slate-600 text-[11px] break-all">
                  {caseData.call_sid || 'Direct Session'}
                </span>
              </div>
            </div>
          </div>

          {/* Emergency Directive Checklist */}
          <div className="bg-blue-50/70 border border-blue-200 rounded-2xl p-5 shadow-card space-y-3">
            <h2 className="text-xs font-bold text-blue-900 uppercase tracking-wider flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-blue-700" />
              <span>Emergency Action Checklist</span>
            </h2>

            <ol className="text-xs text-slate-700 space-y-2.5 list-decimal list-inside">
              <li>
                <strong className="text-slate-900">Dial 1930 Helpline:</strong> Instruct victim to call National Cybercrime Helpline immediately for transaction freeze.
              </li>
              <li>
                <strong className="text-slate-900">Notify Compromised Bank:</strong> Request an immediate freeze of cards, netbanking credentials, and UPI handles.
              </li>
              <li>
                <strong className="text-slate-900">Submit to cybercrime.gov.in:</strong> File the formal statement on India&apos;s official portal using the draft below.
              </li>
            </ol>
          </div>
        </div>

        {/* Right 2 Columns: Incident Statement, Evidence, and Official Complaint Draft */}
        <div className="lg:col-span-2 space-y-6">
          {/* Victim Spoken Narrative */}
          <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-card space-y-4">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2 border-b border-slate-100 pb-3">
              <MessageSquare className="w-4 h-4 text-blue-600" />
              <span>Victim Recorded Statement & Narrative</span>
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-slate-50 p-3.5 rounded-xl border border-slate-200/70 text-xs">
              <div>
                <span className="text-slate-500 flex items-center gap-1.5 mb-0.5">
                  <Calendar className="w-3.5 h-3.5 text-blue-600" />
                  Incident Occurrence Date:
                </span>
                <span className="font-semibold text-slate-800">
                  {caseData.incident_date || 'Stated in call narrative'}
                </span>
              </div>
              <div>
                <span className="text-slate-500 flex items-center gap-1.5 mb-0.5">
                  <Clock className="w-3.5 h-3.5 text-blue-600" />
                  Incident Occurrence Time:
                </span>
                <span className="font-semibold text-slate-800">
                  {caseData.incident_time || 'Stated in call narrative'}
                </span>
              </div>
            </div>

            <div>
              <span className="text-xs font-semibold uppercase text-slate-500 block mb-1.5">
                Spoken Statement (Speech-to-Text Transcription):
              </span>
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-slate-800 text-sm leading-relaxed whitespace-pre-wrap font-sans">
                {caseData.story || 'No statement transcription recorded.'}
              </div>
            </div>

            <div>
              <span className="text-xs font-semibold uppercase text-slate-500 block mb-1.5">
                Targeted Follow-up Question & Citizen Answer:
              </span>
              <div className="bg-slate-50/70 p-4 rounded-xl border border-slate-200 space-y-2 text-xs">
                {caseData.follow_up_question && (
                  <p className="text-amber-900 font-medium">
                    <strong>Question: </strong> {caseData.follow_up_question}
                  </p>
                )}
                <p className="text-slate-700">
                  <strong className="text-slate-900">Answer: </strong>{' '}
                  {caseData.details || 'No follow-up details provided.'}
                </p>
              </div>
            </div>
          </div>

          {/* Evidentiary Particulars: Bank & Suspect Identifiers */}
          <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-card space-y-4">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2 border-b border-slate-100 pb-3">
              <Landmark className="w-4 h-4 text-blue-600" />
              <span>Evidentiary Particulars & Suspect Identifiers</span>
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Victim Bank Info */}
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs space-y-2">
                <span className="font-bold text-blue-800 uppercase tracking-wide block mb-1 flex items-center gap-1.5">
                  <Building className="w-3.5 h-3.5 text-blue-600" />
                  Victim Bank Particulars
                </span>
                <div>
                  <span className="text-slate-500">Bank Name: </span>
                  <span className="text-slate-900 font-semibold">
                    {bank?.bank_name || 'Not specified'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">Branch: </span>
                  <span className="text-slate-900 font-semibold">
                    {bank?.bank_branch || 'Not specified'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">Account Number: </span>
                  <span className="font-mono text-slate-900 font-semibold">
                    {bank?.account_number
                      ? `XXXX${bank.account_number.slice(-4)}`
                      : 'Not specified'}
                  </span>
                </div>
              </div>

              {/* Suspect Identifiers */}
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs space-y-2">
                <span className="font-bold text-rose-800 uppercase tracking-wide block mb-1 flex items-center gap-1.5">
                  <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
                  Accused / Suspect Identifiers
                </span>
                {suspect?.names?.length ? (
                  <div>
                    <span className="text-slate-500">Names / Aliases: </span>
                    <span className="text-slate-900 font-semibold">{suspect.names.join(', ')}</span>
                  </div>
                ) : null}
                {suspect?.phone_numbers?.length ? (
                  <div>
                    <span className="text-slate-500">Phone Numbers: </span>
                    <span className="font-mono text-blue-700 font-bold">
                      {suspect.phone_numbers.join(', ')}
                    </span>
                  </div>
                ) : null}
                {suspect?.upi_ids?.length ? (
                  <div>
                    <span className="text-slate-500">UPI IDs: </span>
                    <span className="font-mono text-amber-700 font-semibold">{suspect.upi_ids.join(', ')}</span>
                  </div>
                ) : null}
                {suspect?.emails?.length ? (
                  <div>
                    <span className="text-slate-500">Email: </span>
                    <span className="text-slate-800">{suspect.emails.join(', ')}</span>
                  </div>
                ) : null}
                {!suspect?.names?.length &&
                  !suspect?.phone_numbers?.length &&
                  !suspect?.upi_ids?.length &&
                  !suspect?.emails?.length && (
                    <p className="text-slate-500 italic">
                      No explicit suspect identifiers mentioned during phone call.
                    </p>
                  )}
              </div>
            </div>

            {/* Missing Info Flags */}
            {missingInfo.length > 0 && (
              <div className="pt-2">
                <span className="text-xs font-semibold text-amber-800 block mb-1.5">
                  Missing Evidentiary Information:
                </span>
                <div className="flex flex-wrap gap-2">
                  {missingInfo.map((item, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-md text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200"
                    >
                      • {item}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* AI Analysis & Formal Complaint Draft Section */}
          <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-card space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <FileCheck2 className="w-4 h-4 text-blue-600" />
                <span>AI Investigation Summary & Formal Complaint Draft</span>
              </h2>
              {formalDraft && (
                <button
                  onClick={() => copyToClipboard(formalDraft, 'draft')}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 flex items-center gap-1.5 transition-colors"
                >
                  {copiedDraft ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-600" />
                      <span>Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>Copy Draft</span>
                    </>
                  )}
                </button>
              )}
            </div>

            {llm?.incident_summary && (
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs space-y-1">
                <span className="text-slate-500 font-semibold uppercase block">
                  AI Incident Summary:
                </span>
                <p className="text-slate-800 leading-relaxed font-sans">
                  {llm.incident_summary}
                </p>
              </div>
            )}

            {formalDraft ? (
              <div>
                <span className="text-xs font-semibold uppercase text-slate-500 block mb-2">
                  Official Statement for National Cyber Crime Portal (cybercrime.gov.in):
                </span>
                <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-slate-800 text-xs font-mono leading-relaxed whitespace-pre-wrap">
                  {formalDraft}
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-400 italic">
                Formal complaint draft was not compiled during this session.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
