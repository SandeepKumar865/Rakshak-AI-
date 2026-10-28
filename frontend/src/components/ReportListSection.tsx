import React, { useState, useMemo } from 'react';
import {
  Search,
  Filter,
  FileText,
  Download,
  Share2,
  Calendar,
  XCircle,
  Eye,
  ArrowUpDown,
  FileCheck,
} from 'lucide-react';
import { CaseSummary, FraudCategory, CallStatusType } from '../types';
import { CategoryBadge } from './CategoryBadge';
import { api } from '../services/api';

interface ReportListSectionProps {
  cases: CaseSummary[];
  loading: boolean;
  onSelectCase: (caseId: string) => void;
  onRefresh: () => void;
}

export const ReportListSection: React.FC<ReportListSectionProps> = ({
  cases,
  loading,
  onSelectCase,
  onRefresh,
}) => {
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [selectedDateFilter, setSelectedDateFilter] = useState<string>('ALL');
  const [sortField, setSortField] = useState<'date' | 'loss'>('date');
  const [sortAsc, setSortAsc] = useState<boolean>(false);

  // Category labels mapping
  const CATEGORIES = [
    { value: 'ALL', label: 'All Categories' },
    { value: 'OTP_FRAUD', label: 'OTP / Banking Fraud' },
    { value: 'JOB_SCAM', label: 'Fake Job / Telegram Scam' },
    { value: 'OLX_SCAM', label: 'OLX / QR Code Scam' },
    { value: 'LOAN_FRAUD', label: 'Instant Loan / Extortion' },
    { value: 'GENERAL_FRAUD', label: 'General Cybercrime' },
  ];

  const CALL_STATUSES = [
    { value: 'ALL', label: 'All Call Statuses' },
    { value: 'completed', label: 'Completed' },
    { value: 'in-progress', label: 'In Progress' },
    { value: 'ringing', label: 'Ringing' },
    { value: 'initiated', label: 'Initiated' },
    { value: 'failed', label: 'Failed' },
  ];

  // Filter & Search Logic
  const filteredCases = useMemo(() => {
    return cases.filter((c) => {
      // 1. Search Query
      if (searchTerm.trim()) {
        const query = searchTerm.toLowerCase();
        const matchesId = (c.report_id || c.id || '').toLowerCase().includes(query);
        const matchesName = (c.name || '').toLowerCase().includes(query);
        const matchesPhone = (c.caller_phone || '').toLowerCase().includes(query);
        const matchesStory = (c.story_snippet || '').toLowerCase().includes(query);
        if (!matchesId && !matchesName && !matchesPhone && !matchesStory) {
          return false;
        }
      }

      // 2. Category Filter
      if (selectedCategory !== 'ALL') {
        const cat = (c.scenario || '').toUpperCase();
        if (cat !== selectedCategory) return false;
      }

      // 3. Status Filter (maps case status / call status)
      if (selectedStatus !== 'ALL') {
        const st = (c.status || '').toLowerCase();
        if (selectedStatus === 'completed' && !['closed', 'resolved', 'investigating', 'completed', 'new', 'under review'].includes(st)) {
          return false;
        }
      }

      // 4. Date Filter
      if (selectedDateFilter !== 'ALL') {
        const itemDate = new Date(c.created_at || Date.now());
        const now = new Date();
        if (selectedDateFilter === 'TODAY') {
          if (itemDate.toDateString() !== now.toDateString()) return false;
        } else if (selectedDateFilter === 'WEEK') {
          const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
          if (itemDate < sevenDaysAgo) return false;
        }
      }

      return true;
    }).sort((a, b) => {
      if (sortField === 'loss') {
        const lossA = a.financial_loss_numeric || 0;
        const lossB = b.financial_loss_numeric || 0;
        return sortAsc ? lossA - lossB : lossB - lossA;
      } else {
        const dateA = new Date(a.created_at || 0).getTime();
        const dateB = new Date(b.created_at || 0).getTime();
        return sortAsc ? dateA - dateB : dateB - dateA;
      }
    });
  }, [cases, searchTerm, selectedCategory, selectedStatus, selectedDateFilter, sortField, sortAsc]);

  const hasActiveFilters =
    searchTerm !== '' ||
    selectedCategory !== 'ALL' ||
    selectedStatus !== 'ALL' ||
    selectedDateFilter !== 'ALL';

  const resetFilters = () => {
    setSearchTerm('');
    setSelectedCategory('ALL');
    setSelectedStatus('ALL');
    setSelectedDateFilter('ALL');
  };

  const formatLoss = (amount: number | string | undefined) => {
    if (!amount) return 'N/A';
    const num = typeof amount === 'string' ? parseFloat(amount.replace(/[^\d.]/g, '')) : amount;
    if (isNaN(num) || num === 0) return 'N/A';
    return `₹${num.toLocaleString('en-IN')}`;
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-xs mt-6">
      {/* Module Header Bar */}
      <div className="p-5 lg:p-6 border-b border-slate-200">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-800 border border-blue-200 flex items-center justify-center font-bold">
              <FileCheck className="w-6 h-6 text-blue-700" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-lg font-bold text-slate-900 leading-tight">
                  Registered Cybercrime Reports
                </h2>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                  {filteredCases.length} Cases
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Official citizen fraud complaints recorded and transcribed via the voice intake pipeline
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-[11px] font-semibold uppercase px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
              Module 4
            </span>
          </div>
        </div>

        {/* Search & Filter Toolbar */}
        <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* 1. Search */}
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search Report ID, Citizen, Phone..."
              className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-300 bg-white text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-700 focus:ring-1 focus:ring-blue-700"
            />
          </div>

          {/* 2. Category Filter */}
          <div>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full py-2 px-3 text-xs rounded-lg border border-slate-300 bg-white text-slate-800 focus:outline-none focus:border-blue-700 focus:ring-1 focus:ring-blue-700"
            >
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          {/* 3. Call Status Filter */}
          <div>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="w-full py-2 px-3 text-xs rounded-lg border border-slate-300 bg-white text-slate-800 focus:outline-none focus:border-blue-700 focus:ring-1 focus:ring-blue-700"
            >
              {CALL_STATUSES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>

          {/* 4. Date Filter & Reset */}
          <div className="flex items-center space-x-2">
            <select
              value={selectedDateFilter}
              onChange={(e) => setSelectedDateFilter(e.target.value)}
              className="flex-1 py-2 px-3 text-xs rounded-lg border border-slate-300 bg-white text-slate-800 focus:outline-none focus:border-blue-700 focus:ring-1 focus:ring-blue-700"
            >
              <option value="ALL">All Dates</option>
              <option value="TODAY">Today's Incidents</option>
              <option value="WEEK">Last 7 Days</option>
            </select>

            {hasActiveFilters && (
              <button
                onClick={resetFilters}
                className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg border border-slate-200 transition-colors"
                title="Reset all filters"
              >
                <XCircle className="w-4 h-4 text-slate-500" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Reports Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 uppercase tracking-wider text-[11px]">
            <tr>
              <th className="py-3 px-4">Report ID</th>
              <th className="py-3 px-4">Citizen Name</th>
              <th className="py-3 px-4">Incident Category</th>
              <th
                className="py-3 px-4 cursor-pointer hover:text-slate-900"
                onClick={() => {
                  if (sortField === 'loss') setSortAsc(!sortAsc);
                  else {
                    setSortField('loss');
                    setSortAsc(false);
                  }
                }}
              >
                <div className="flex items-center space-x-1">
                  <span>Reported Loss</span>
                  <ArrowUpDown className="w-3 h-3" />
                </div>
              </th>
              <th
                className="py-3 px-4 cursor-pointer hover:text-slate-900"
                onClick={() => {
                  if (sortField === 'date') setSortAsc(!sortAsc);
                  else {
                    setSortField('date');
                    setSortAsc(false);
                  }
                }}
              >
                <div className="flex items-center space-x-1">
                  <span>Incident Date</span>
                  <ArrowUpDown className="w-3 h-3" />
                </div>
              </th>
              <th className="py-3 px-4">Call Status</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr>
                <td colSpan={7} className="py-12 text-center text-slate-500">
                  <div className="flex justify-center items-center space-x-2">
                    <span className="w-4 h-4 border-2 border-slate-600 border-t-transparent rounded-full animate-spin"></span>
                    <span>Retrieving official incident records...</span>
                  </div>
                </td>
              </tr>
            ) : filteredCases.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-12 text-center text-slate-500">
                  <FileText className="w-8 h-8 mx-auto text-slate-400 mb-2" />
                  <p className="font-semibold text-slate-700">No reports match the selected filters</p>
                  <p className="text-slate-400 text-[11px] mt-1">Try clearing your search query or reset filters.</p>
                </td>
              </tr>
            ) : (
              filteredCases.map((item) => {
                const reportIdentifier = item.report_id || item.id;
                return (
                  <tr
                    key={item.id}
                    className="hover:bg-slate-50/80 transition-colors cursor-pointer group"
                    onClick={() => onSelectCase(item.id)}
                  >
                    {/* Report ID */}
                    <td className="py-3.5 px-4 font-mono font-bold text-blue-900 group-hover:underline">
                      {reportIdentifier}
                    </td>

                    {/* Citizen Name & Phone */}
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-900">{item.name || 'Anonymous Citizen'}</div>
                      <div className="text-[11px] text-slate-500 font-mono">
                        {item.caller_phone || 'Masked / +91*****'}
                      </div>
                    </td>

                    {/* Category */}
                    <td className="py-3.5 px-4">
                      <CategoryBadge
                        category={item.scenario as FraudCategory}
                        label={item.scenario_label}
                        language={item.language}
                      />
                    </td>

                    {/* Financial Loss */}
                    <td className="py-3.5 px-4 font-semibold text-slate-900">
                      {formatLoss(item.financial_loss_numeric || item.financial_loss)}
                    </td>

                    {/* Incident Date */}
                    <td className="py-3.5 px-4 text-slate-600">
                      <div>{item.incident_date || 'Recent Date'}</div>
                      <div className="text-[11px] text-slate-400">{item.incident_time || ''}</div>
                    </td>

                    {/* Call Status Badge */}
                    <td className="py-3.5 px-4">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1.5"></span>
                        Completed
                      </span>
                    </td>

                    {/* Actions */}
                    <td
                      className="py-3.5 px-4 text-right space-x-1"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button
                        onClick={() => onSelectCase(item.id)}
                        className="inline-flex items-center space-x-1 px-2.5 py-1 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-md hover:bg-slate-100 hover:text-slate-900 transition-colors shadow-xs"
                        title="View Detailed Dossier"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Dossier</span>
                      </button>

                      {item.has_pdf && item.pdf_filename && (
                        <a
                          href={api.getDownloadUrl(item.pdf_filename)}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center space-x-1 px-2.5 py-1 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 transition-colors shadow-xs"
                          title="Download Official PDF"
                        >
                          <Download className="w-3.5 h-3.5" />
                          <span>PDF</span>
                        </a>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
