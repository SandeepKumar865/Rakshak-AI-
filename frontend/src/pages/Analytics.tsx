import React from 'react';
import {
  BarChart3,
  TrendingUp,
  Languages,
  AlertTriangle,
  IndianRupee,
  RefreshCw,
  Layers,
} from 'lucide-react';
import { DashboardStats } from '../types';
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
  AreaChart,
  Area,
} from 'recharts';

interface AnalyticsProps {
  stats: DashboardStats | null;
  loading: boolean;
  onRefresh: () => void;
}

const CATEGORY_COLORS = ['#2563EB', '#0D9488', '#D97706', '#E11D48', '#7C3AED'];
const PRIORITY_COLORS: Record<string, string> = {
  Critical: '#E11D48',
  High: '#EA580C',
  Medium: '#D97706',
  Low: '#2563EB',
};
const LANGUAGE_COLORS = ['#2563EB', '#0D9488'];

export const Analytics: React.FC<AnalyticsProps> = ({ stats, loading, onRefresh }) => {
  const breakdowns = stats?.breakdowns;
  const categories = breakdowns?.categories || [];
  const priorities = breakdowns?.priorities || [];
  const languages = breakdowns?.languages || [];
  const timeline = breakdowns?.timeline || [];

  const formatCurrency = (val: number) => {
    if (val >= 100000) return `₹${(val / 100000).toFixed(1)}L`;
    if (val >= 1000) return `₹${(val / 1000).toFixed(0)}k`;
    return `₹${val}`;
  };

  return (
    <div className="space-y-6">
      {/* ── Page Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2.5">
            <BarChart3 className="w-6 h-6 text-blue-600" />
            <span>Cybercrime Threat & Operational Analytics</span>
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time visual telemetry calculated directly from all verified citizen reports.
          </p>
        </div>

        <button
          onClick={onRefresh}
          disabled={loading}
          className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 flex items-center gap-2 shadow-sm transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-blue-600 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Data</span>
        </button>
      </div>

      {/* ── Top Level Metric Tiles ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-card">
          <span className="text-xs font-semibold text-slate-500 uppercase block">Total Complaints</span>
          <span className="text-2xl font-extrabold text-slate-900 font-mono mt-1 block">
            {stats?.kpis?.total_complaints ?? 0}
          </span>
          <span className="text-[11px] text-blue-600 font-medium">Logged in repository</span>
        </div>

        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-card">
          <span className="text-xs font-semibold text-slate-500 uppercase block">Reported Loss</span>
          <span className="text-2xl font-extrabold text-rose-600 font-mono mt-1 block">
            {stats ? formatCurrency(stats.kpis.total_reported_loss) : '₹0'}
          </span>
          <span className="text-[11px] text-rose-600/80 font-medium">Reported by victims</span>
        </div>

        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-card">
          <span className="text-xs font-semibold text-slate-500 uppercase block">High / Critical Cases</span>
          <span className="text-2xl font-extrabold text-amber-600 font-mono mt-1 block">
            {stats?.kpis?.high_priority_cases ?? 0}
          </span>
          <span className="text-[11px] text-amber-600/80 font-medium">High financial exposure</span>
        </div>

        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-card">
          <span className="text-xs font-semibold text-slate-500 uppercase block">Official PDF Reports</span>
          <span className="text-2xl font-extrabold text-emerald-600 font-mono mt-1 block">
            {stats?.kpis?.reports_generated ?? 0}
          </span>
          <span className="text-[11px] text-emerald-600/80 font-medium">Compiled dossiers</span>
        </div>
      </div>

      {/* ── Charts Grid Row 1: Category & Timeline ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 1. Complaints by Category */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-card">
          <div className="mb-4">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Layers className="w-4 h-4 text-blue-600" />
              <span>Complaints by Fraud Category</span>
            </h2>
            <p className="text-xs text-slate-500">
              Taxonomy classification of scam vectors
            </p>
          </div>

          {categories.length > 0 ? (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={categories} margin={{ top: 10, right: 10, left: -20, bottom: 25 }}>
                  <XAxis
                    dataKey="name"
                    stroke="#94A3B8"
                    fontSize={11}
                    interval={0}
                    angle={-15}
                    textAnchor="end"
                  />
                  <YAxis stroke="#94A3B8" fontSize={11} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#FFFFFF',
                      borderColor: '#E2E8F0',
                      borderRadius: '8px',
                      color: '#0F172A',
                      fontSize: '12px',
                      boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
                    }}
                  />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {categories.map((_, idx) => (
                      <Cell key={idx} fill={CATEGORY_COLORS[idx % CATEGORY_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-slate-400">
              No category data available
            </div>
          )}
        </div>

        {/* 2. Complaints Over Time Timeline */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-card">
          <div className="mb-4">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-blue-600" />
              <span>Complaints Intake Over Time</span>
            </h2>
            <p className="text-xs text-slate-500">
              Daily trend of registered cybercrime calls
            </p>
          </div>

          {timeline.length > 0 ? (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={timeline} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                  <defs>
                    <linearGradient id="blueGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563EB" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#2563EB" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="date" stroke="#94A3B8" fontSize={11} />
                  <YAxis stroke="#94A3B8" fontSize={11} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#FFFFFF',
                      borderColor: '#E2E8F0',
                      borderRadius: '8px',
                      color: '#0F172A',
                      fontSize: '12px',
                      boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="count"
                    stroke="#2563EB"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#blueGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-slate-400">
              No timeline records available yet
            </div>
          )}
        </div>
      </div>

      {/* ── Charts Grid Row 2: Loss, Language & Priority ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* 3. Reported Financial Loss by Date */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-card flex flex-col">
          <div className="mb-4">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <IndianRupee className="w-4 h-4 text-purple-600" />
              <span>Financial Loss Trend</span>
            </h2>
            <p className="text-xs text-slate-500">
              Reported victim financial losses
            </p>
          </div>

          {timeline.length > 0 ? (
            <div className="h-56 w-full flex-1">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={timeline} margin={{ top: 10, right: 10, left: -10, bottom: 20 }}>
                  <XAxis dataKey="date" stroke="#94A3B8" fontSize={10} />
                  <YAxis
                    stroke="#94A3B8"
                    fontSize={10}
                    tickFormatter={(v) => formatCurrency(v)}
                  />
                  <Tooltip
                    formatter={(val: any) => [`₹${Number(val).toLocaleString('en-IN')}`, 'Loss']}
                    contentStyle={{
                      backgroundColor: '#FFFFFF',
                      borderColor: '#E2E8F0',
                      borderRadius: '8px',
                      color: '#0F172A',
                      fontSize: '12px',
                      boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
                    }}
                  />
                  <Bar dataKey="loss" fill="#7C3AED" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-56 flex items-center justify-center text-slate-400">
              No financial loss data
            </div>
          )}
        </div>

        {/* 4. Language Distribution */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-card flex flex-col">
          <div className="mb-4">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Languages className="w-4 h-4 text-teal-600" />
              <span>Caller Language Breakdown</span>
            </h2>
            <p className="text-xs text-slate-500">
              Hindi vs English IVR language selection
            </p>
          </div>

          {languages.length > 0 ? (
            <div className="h-56 w-full flex flex-col justify-center">
              <div className="h-40 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={languages}
                      dataKey="count"
                      nameKey="language"
                      cx="50%"
                      cy="50%"
                      innerRadius={40}
                      outerRadius={60}
                      paddingAngle={4}
                    >
                      {languages.map((_, idx) => (
                        <Cell
                          key={idx}
                          fill={LANGUAGE_COLORS[idx % LANGUAGE_COLORS.length]}
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
                        boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="flex items-center justify-around pt-3 border-t border-slate-100 text-xs">
                {languages.map((item, idx) => (
                  <div key={item.language} className="flex items-center gap-2">
                    <span
                      className="w-2.5 h-2.5 rounded-full"
                      style={{
                        backgroundColor:
                          LANGUAGE_COLORS[idx % LANGUAGE_COLORS.length],
                      }}
                    />
                    <span className="text-slate-600 font-medium">
                      {item.language}: <strong className="text-slate-900 font-mono">{item.count}</strong>
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="h-56 flex items-center justify-center text-slate-400">
              No language data
            </div>
          )}
        </div>

        {/* 5. Case Priority Distribution */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-card flex flex-col">
          <div className="mb-4">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-600" />
              <span>Priority Rating Breakdown</span>
            </h2>
            <p className="text-xs text-slate-500">
              Severity rating assigned to registered cases
            </p>
          </div>

          {priorities.length > 0 ? (
            <div className="h-56 w-full flex flex-col justify-center">
              <div className="h-40 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={priorities}
                      dataKey="count"
                      nameKey="priority"
                      cx="50%"
                      cy="50%"
                      innerRadius={40}
                      outerRadius={60}
                      paddingAngle={4}
                    >
                      {priorities.map((item) => (
                        <Cell
                          key={item.priority}
                          fill={PRIORITY_COLORS[item.priority] || '#2563EB'}
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
                        boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="grid grid-cols-2 gap-2 pt-3 border-t border-slate-100 text-xs">
                {priorities.map((item) => (
                  <div key={item.priority} className="flex items-center justify-between">
                    <span className="text-slate-500">{item.priority}:</span>
                    <strong className="text-slate-900 font-mono">{item.count}</strong>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="h-56 flex items-center justify-center text-slate-400">
              No priority data
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
