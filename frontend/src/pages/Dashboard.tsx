import React, { useState } from 'react';
import {
  FileText,
  Clock,
  AlertTriangle,
  IndianRupee,
  Layers,
  ArrowRight,
  TrendingUp,
  Download,
  Eye,
  Send,
  Sparkles,
  ExternalLink,
  ShieldCheck,
  CheckCircle,
} from 'lucide-react';
import { KPICard } from '../components/KPICard';
import { StatusBadge } from '../components/StatusBadge';
import { PriorityBadge } from '../components/PriorityBadge';
import { CategoryBadge } from '../components/CategoryBadge';
import { CaseSummary, DashboardStats } from '../types';
import { api } from '../services/api';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  PieChart,
  Pie,
} from 'recharts';

interface DashboardProps {
  stats: DashboardStats | null;
  cases: CaseSummary[];
  loading: boolean;
  onSelectCase: (caseId: string) => void;
  onNavigateTab: (tab: string) => void;
  onRefresh: () => void;
}

const CATEGORY_COLORS = ['#2563EB', '#0D9488', '#D97706', '#E11D48', '#7C3AED'];
const PRIORITY_COLORS: Record<string, string> = {
  Critical: '#E11D48',
  High: '#EA580C',
  Medium: '#D97706',
  Low: '#2563EB',
};

export const Dashboard: React.FC<DashboardProps> = ({
  stats,
  cases,
  loading,
  onSelectCase,
  onNavigateTab,
  onRefresh,
}) => {
  const [testText, setTestText] = useState('');
  const [testCaller, setTestCaller] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<any>(null);

  const formatCurrency = (amount: number) => {
    if (isNaN(amount) || amount === 0) return '₹0';
    if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(2)} Cr`;
    if (amount >= 100000) return `₹${(amount / 100000).toFixed(2)} Lakh`;
    return `₹${amount.toLocaleString('en-IN')}`;
  };

  const handleTestAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!testText.trim()) return;
    setAnalyzing(true);
    setAnalysisResult(null);
    try {
      const res = await api.analyzeIncident({
        text: testText,
        caller_name: testCaller || 'Citizen',
        language: 'hi',
        generate_pdf: true,
      });
      setAnalysisResult(res.analysis);
      onRefresh();
    } catch (err: any) {
      alert(`Simulation error: ${err.message || 'Failed'}`);
    } finally {
      setAnalyzing(false);
    }
  };

  const recentCases = cases.slice(0, 6);
  const kpis = stats?.kpis;

  return (
    <div className="space-y-6">
      {/* ── Top Header Card (Human-designed government/agency feel) ── */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-card flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
              National Cybercrime First Responder
            </span>
            <span className="text-xs text-slate-500 font-medium">
              Bilingual Telephony & IVR System
            </span>
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Cybercrime Complaints & Investigation Dashboard
          </h1>
          <p className="text-xs text-slate-600 max-w-2xl mt-1 leading-relaxed">
            Real-time monitoring of citizen emergency calls, automated fraud classification,
            tamper-evident evidence compilation, and official bilingual police complaint reports.
          </p>
        </div>

        <div className="flex items-center gap-2.5 shrink-0">
          <button
            onClick={() => onNavigateTab('cases')}
            className="px-4 py-2.5 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white flex items-center gap-2 shadow-sm transition-colors"
          >
            <span>View All Complaints</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* ── Top-Level KPI Cards (Requirement 3) ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <KPICard
          title="Total Complaints"
          value={kpis?.total_complaints ?? 'N/A'}
          subtitle="Registered intake cases"
          icon={Layers}
          colorTheme="blue"
          loading={loading}
        />

        <KPICard
          title="Today's Cases"
          value={kpis?.today_complaints ?? '0'}
          subtitle="Calls logged today"
          icon={Clock}
          colorTheme="cyan"
          trend={kpis && kpis.today_complaints > 0 ? 'Active' : 'No calls'}
          trendType={kpis && kpis.today_complaints > 0 ? 'positive' : 'neutral'}
          loading={loading}
        />

        <KPICard
          title="Pending / Review"
          value={kpis?.pending_unreviewed ?? 'N/A'}
          subtitle="Requires officer triage"
          icon={Clock}
          colorTheme="amber"
          trend="Action Needed"
          trendType="alert"
          loading={loading}
        />

        <KPICard
          title="High Priority"
          value={kpis?.high_priority_cases ?? 'N/A'}
          subtitle="Critical & High risk"
          icon={AlertTriangle}
          colorTheme="rose"
          trend="Urgent"
          trendType="alert"
          loading={loading}
        />

        <KPICard
          title="Reported Loss"
          value={kpis ? formatCurrency(kpis.total_reported_loss) : 'N/A'}
          subtitle="Stated by victims"
          icon={IndianRupee}
          colorTheme="purple"
          loading={loading}
        />

        <KPICard
          title="Reports Built"
          value={kpis?.reports_generated ?? 'N/A'}
          subtitle="Official bilingual PDFs"
          icon={FileText}
          colorTheme="emerald"
          loading={loading}
        />
      </div>

      {/* ── Charts & Visual Analytics Section ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Category Breakdown Chart */}
        <div className="lg:col-span-2 bg-white border border-slate-200/90 rounded-2xl p-6 shadow-card">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-blue-600" />
                <span>Complaints by Fraud Category</span>
              </h2>
              <p className="text-xs text-slate-500">
                AI and keyword fraud taxonomy breakdown
              </p>
            </div>
            <button
              onClick={() => onNavigateTab('analytics')}
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1"
            >
              <span>Full Analytics</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {stats?.breakdowns?.categories?.length ? (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={stats.breakdowns.categories}
                  margin={{ top: 10, right: 10, left: -20, bottom: 25 }}
                >
                  <XAxis
                    dataKey="name"
                    stroke="#94A3B8"
                    fontSize={11}
                    tickLine={false}
                    interval={0}
                    angle={-15}
                    textAnchor="end"
                  />
                  <YAxis
                    stroke="#94A3B8"
                    fontSize={11}
                    tickLine={false}
                    allowDecimals={false}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#FFFFFF',
                      borderColor: '#E2E8F0',
                      borderRadius: '8px',
                      color: '#0F172A',
                      fontSize: '12px',
                      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                    }}
                    cursor={{ fill: 'rgba(241, 245, 249, 0.6)' }}
                  />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {stats.breakdowns.categories.map((_, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={CATEGORY_COLORS[index % CATEGORY_COLORS.length]}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex flex-col items-center justify-center text-slate-400">
              <Layers className="w-10 h-10 mb-2 opacity-50" />
              <p className="text-sm">No categorical fraud data available yet.</p>
            </div>
          )}
        </div>

        {/* Priority Rating Distribution */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-card flex flex-col">
          <div className="mb-4">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-600" />
              <span>Priority & Threat Rating</span>
            </h2>
            <p className="text-xs text-slate-500">
              Case severity based on financial loss & threat indicators
            </p>
          </div>

          {stats?.breakdowns?.priorities?.length ? (
            <div className="flex-1 flex flex-col justify-center">
              <div className="h-44 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={stats.breakdowns.priorities}
                      dataKey="count"
                      nameKey="priority"
                      cx="50%"
                      cy="50%"
                      innerRadius={45}
                      outerRadius={65}
                      paddingAngle={4}
                    >
                      {stats.breakdowns.priorities.map((entry) => (
                        <Cell
                          key={`cell-${entry.priority}`}
                          fill={PRIORITY_COLORS[entry.priority] || '#2563EB'}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#FFFFFF',
                        borderColor: '#E2E8F0',
                        borderRadius: '8px',
                        color: '#0F172A',
                        fontSize: '12px',
                        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              {/* Legend List */}
              <div className="grid grid-cols-2 gap-2 mt-2 pt-3 border-t border-slate-100 text-xs">
                {stats.breakdowns.priorities.map((item) => (
                  <div
                    key={item.priority}
                    className="flex items-center justify-between p-1.5 rounded bg-slate-50 border border-slate-100"
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className="w-2.5 h-2.5 rounded-full"
                        style={{
                          backgroundColor:
                            PRIORITY_COLORS[item.priority] || '#2563EB',
                        }}
                      />
                      <span className="text-slate-700 font-medium">
                        {item.priority}
                      </span>
                    </div>
                    <span className="font-mono font-bold text-slate-900">
                      {item.count}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-400">
              <p className="text-sm">No priority stats available.</p>
            </div>
          )}
        </div>
      </div>

      {/* ── Recent Complaints Table (Requirement 4 & 19) ── */}
      <div className="bg-white border border-slate-200/90 rounded-2xl shadow-card overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Layers className="w-4 h-4 text-blue-600" />
              <span>Recent Cybercrime Complaints</span>
            </h2>
            <p className="text-xs text-slate-500">
              Latest citizen voice complaints transcribed and structured by Rakshak AI
            </p>
          </div>
          <button
            onClick={() => onNavigateTab('cases')}
            className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1.5"
          >
            <span>View All ({cases.length}) Complaints</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {loading ? (
          <div className="p-8 text-center">
            <div className="inline-block w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mb-3"></div>
            <p className="text-sm text-slate-500">Loading complaint records...</p>
          </div>
        ) : recentCases.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-slate-800">
              No Cybercrime Complaints Registered Yet
            </h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              Complaints logged via Twilio phone calls or the intake simulation tool will appear here immediately.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 text-xs uppercase font-semibold">
                <tr>
                  <th className="py-3 px-4">Case ID</th>
                  <th className="py-3 px-4">Citizen</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Reported Loss</th>
                  <th className="py-3 px-4">Priority</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Logged At</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {recentCases.map((c) => (
                  <tr
                    key={c.id}
                    className="hover:bg-slate-50/80 transition-colors cursor-pointer group"
                    onClick={() => onSelectCase(c.id)}
                  >
                    <td className="py-3.5 px-4 font-mono text-xs font-bold text-blue-600 group-hover:underline">
                      {c.report_id || c.id}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-900">{c.name}</div>
                      <div className="text-[11px] text-slate-500 font-mono">
                        {c.caller_phone || 'Direct Caller'}
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <CategoryBadge
                        category={c.scenario}
                        label={c.scenario_label}
                        labelHi={c.scenario_label_hi}
                      />
                    </td>
                    <td className="py-3.5 px-4 font-mono text-xs font-semibold text-slate-900">
                      {c.financial_loss || 'Not specified'}
                    </td>
                    <td className="py-3.5 px-4">
                      <PriorityBadge priority={c.priority} size="sm" />
                    </td>
                    <td className="py-3.5 px-4">
                      <StatusBadge status={c.status} size="sm" />
                    </td>
                    <td className="py-3.5 px-4 text-xs text-slate-500 font-mono whitespace-nowrap">
                      {c.created_at}
                    </td>
                    <td className="py-3.5 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => onSelectCase(c.id)}
                          title="Open Case Investigation"
                          className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        {c.pdf_download_url && (
                          <a
                            href={c.pdf_download_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            download
                            title="Download Official PDF Report"
                            className="p-1.5 rounded-lg text-blue-600 hover:text-blue-800 hover:bg-blue-50 transition-colors"
                          >
                            <Download className="w-4 h-4" />
                          </a>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Officer Incident Intake & Verification Tool ── */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-card space-y-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-blue-50 text-blue-600 border border-blue-100">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <span>Duty Officer Incident Intake Simulation</span>
              <span className="px-2 py-0.5 text-[10px] uppercase font-bold rounded bg-slate-100 text-slate-600 border border-slate-200">
                Testing Tool
              </span>
            </h2>
            <p className="text-xs text-slate-500">
              Directly input verbal disclosures to test transcription analysis, fraud categorization, and PDF report compilation.
            </p>
          </div>
        </div>

        <form onSubmit={handleTestAnalyze} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Citizen Name
              </label>
              <input
                type="text"
                placeholder="e.g. राजेश कुमार or Jane Doe"
                value={testCaller}
                onChange={(e) => setTestCaller(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Citizen Incident Statement (Hindi or English)
              </label>
              <input
                type="text"
                placeholder="e.g. कल बैंक से कॉल आया था और ओटीपी मांग कर मेरे खाते से 25000 रुपये निकाल लिए।"
                value={testText}
                onChange={(e) => setTestText(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="flex items-center justify-between pt-1">
            <span className="text-xs text-slate-500 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-blue-600" />
              Runs anti-hallucination analysis & builds official bilingual PDF dossier.
            </span>
            <button
              type="submit"
              disabled={analyzing || !testText.trim()}
              className="px-4 py-2 rounded-xl text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white flex items-center gap-2 shadow-sm transition-colors disabled:opacity-50"
            >
              <Send className={`w-3.5 h-3.5 ${analyzing ? 'animate-spin' : ''}`} />
              <span>{analyzing ? 'Analyzing...' : 'Simulate Intake'}</span>
            </button>
          </div>
        </form>

        {/* Live Analysis Output */}
        {analysisResult && (
          <div className="mt-4 p-4 rounded-xl bg-blue-50/60 border border-blue-200 space-y-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-600" />
                <span className="text-xs font-bold text-slate-900 uppercase">
                  Incident Parsed:
                </span>
                <span className="px-2 py-0.5 rounded text-xs bg-white border border-slate-200 font-semibold text-slate-800">
                  {analysisResult.fraud_category_label || analysisResult.fraud_category}
                </span>
                {analysisResult.financial_loss && (
                  <span className="px-2 py-0.5 rounded text-xs bg-rose-50 text-rose-700 border border-rose-200 font-mono font-semibold">
                    Loss: {analysisResult.financial_loss}
                  </span>
                )}
              </div>
              {analysisResult.pdf_download_url && (
                <a
                  href={analysisResult.pdf_download_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1"
                >
                  <span>Download Report PDF</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              )}
            </div>

            <p className="text-xs text-slate-700">
              <strong className="text-slate-900">Summary: </strong>
              {analysisResult.incident_summary}
            </p>

            {analysisResult.follow_up_question && (
              <p className="text-xs text-amber-900 bg-amber-50 p-2.5 rounded-lg border border-amber-200">
                <strong>Follow-up Question formulated: </strong>
                {analysisResult.follow_up_question}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
