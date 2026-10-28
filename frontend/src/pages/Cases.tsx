import React, { useState, useMemo } from 'react';
import {
  Search,
  ArrowUpDown,
  Download,
  Eye,
  FileSpreadsheet,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  SlidersHorizontal,
  X,
  FileDown,
} from 'lucide-react';
import { StatusBadge } from '../components/StatusBadge';
import { PriorityBadge } from '../components/PriorityBadge';
import { CategoryBadge } from '../components/CategoryBadge';
import { CaseSummary } from '../types';

interface CasesProps {
  cases: CaseSummary[];
  loading: boolean;
  onSelectCase: (caseId: string) => void;
  onRefresh: () => void;
  initialSearch?: string;
}

export const Cases: React.FC<CasesProps> = ({
  cases,
  loading,
  onSelectCase,
  onRefresh,
  initialSearch = '',
}) => {
  const [searchTerm, setSearchTerm] = useState(initialSearch);
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [selectedPriority, setSelectedPriority] = useState<string>('ALL');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [selectedLanguage, setSelectedLanguage] = useState<string>('ALL');
  const [sortField, setSortField] = useState<'created_at' | 'loss' | 'name' | 'priority'>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  const categories = useMemo(() => {
    const set = new Set<string>();
    cases.forEach((c) => {
      if (c.scenario) set.add(c.scenario);
    });
    return Array.from(set);
  }, [cases]);

  const priorityWeights: Record<string, number> = {
    Critical: 4,
    High: 3,
    Medium: 2,
    Low: 1,
  };

  const filteredCases = useMemo(() => {
    return cases
      .filter((c) => {
        if (searchTerm.trim()) {
          const q = searchTerm.toLowerCase();
          const matchId = (c.report_id || c.id || '').toLowerCase().includes(q);
          const matchName = (c.name || '').toLowerCase().includes(q);
          const matchPhone = (c.caller_phone || '').toLowerCase().includes(q);
          const matchLoss = (c.financial_loss || '').toLowerCase().includes(q);
          const matchSnippet = (c.story_snippet || '').toLowerCase().includes(q);
          if (!matchId && !matchName && !matchPhone && !matchLoss && !matchSnippet) {
            return false;
          }
        }

        if (selectedCategory !== 'ALL' && c.scenario !== selectedCategory) {
          return false;
        }

        if (selectedPriority !== 'ALL' && c.priority !== selectedPriority) {
          return false;
        }

        if (selectedStatus !== 'ALL' && c.status !== selectedStatus) {
          return false;
        }

        if (selectedLanguage !== 'ALL' && c.language !== selectedLanguage) {
          return false;
        }

        return true;
      })
      .sort((a, b) => {
        let diff = 0;
        if (sortField === 'created_at') {
          diff = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        } else if (sortField === 'loss') {
          diff = (a.financial_loss_numeric || 0) - (b.financial_loss_numeric || 0);
        } else if (sortField === 'name') {
          diff = (a.name || '').localeCompare(b.name || '');
        } else if (sortField === 'priority') {
          diff = (priorityWeights[a.priority] || 0) - (priorityWeights[b.priority] || 0);
        }
        return sortOrder === 'desc' ? -diff : diff;
      });
  }, [
    cases,
    searchTerm,
    selectedCategory,
    selectedPriority,
    selectedStatus,
    selectedLanguage,
    sortField,
    sortOrder,
  ]);

  const totalPages = Math.ceil(filteredCases.length / pageSize) || 1;
  const paginatedCases = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredCases.slice(start, start + pageSize);
  }, [filteredCases, currentPage, pageSize]);

  const toggleSort = (field: typeof sortField) => {
    if (sortField === field) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const resetFilters = () => {
    setSearchTerm('');
    setSelectedCategory('ALL');
    setSelectedPriority('ALL');
    setSelectedStatus('ALL');
    setSelectedLanguage('ALL');
    setCurrentPage(1);
  };

  const exportCSV = () => {
    const headers = ['Case ID', 'Citizen Name', 'Category', 'Loss', 'Priority', 'Status', 'Language', 'Created At'];
    const rows = filteredCases.map((c) => [
      c.report_id || c.id,
      `"${c.name}"`,
      `"${c.scenario_label || c.scenario}"`,
      `"${c.financial_loss || ''}"`,
      c.priority,
      c.status,
      c.language,
      c.created_at,
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `Rakshak_Complaints_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const hasActiveFilters =
    searchTerm !== '' ||
    selectedCategory !== 'ALL' ||
    selectedPriority !== 'ALL' ||
    selectedStatus !== 'ALL' ||
    selectedLanguage !== 'ALL';

  return (
    <div className="space-y-5">
      {/* ── Page Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2.5">
            <FileSpreadsheet className="w-6 h-6 text-blue-600" />
            <span>Cybercrime Complaints Repository</span>
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Official citizen intake records registered through the automated first-responder voice system.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={exportCSV}
            className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 flex items-center gap-2 shadow-sm transition-colors"
            title="Export filtered records as CSV"
          >
            <FileDown className="w-3.5 h-3.5 text-slate-500" />
            <span>Export CSV</span>
          </button>

          <button
            onClick={onRefresh}
            disabled={loading}
            className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 flex items-center gap-2 shadow-sm transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-blue-600 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* ── Filters & Search Controls Card ── */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-card space-y-3">
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center gap-3">
          {/* Search Input */}
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setCurrentPage(1);
              }}
              placeholder="Search by Case ID, Citizen Name, Phone, or keyword..."
              className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-10 pr-4 py-2 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Filter Dropdowns */}
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={selectedCategory}
              onChange={(e) => {
                setSelectedCategory(e.target.value);
                setCurrentPage(1);
              }}
              className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:border-blue-500 focus:bg-white"
            >
              <option value="ALL">All Categories</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat.replace(/_/g, ' ')}
                </option>
              ))}
            </select>

            <select
              value={selectedPriority}
              onChange={(e) => {
                setSelectedPriority(e.target.value);
                setCurrentPage(1);
              }}
              className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:border-blue-500 focus:bg-white"
            >
              <option value="ALL">All Priorities</option>
              <option value="Critical">Critical</option>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
            </select>

            <select
              value={selectedStatus}
              onChange={(e) => {
                setSelectedStatus(e.target.value);
                setCurrentPage(1);
              }}
              className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:border-blue-500 focus:bg-white"
            >
              <option value="ALL">All Statuses</option>
              <option value="New">New</option>
              <option value="Under Review">Under Review</option>
              <option value="Investigating">Investigating</option>
              <option value="Resolved">Resolved</option>
              <option value="Closed">Closed</option>
            </select>

            <select
              value={selectedLanguage}
              onChange={(e) => {
                setSelectedLanguage(e.target.value);
                setCurrentPage(1);
              }}
              className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:border-blue-500 focus:bg-white"
            >
              <option value="ALL">All Languages</option>
              <option value="hi">Hindi (हिन्दी)</option>
              <option value="en">English</option>
            </select>

            {hasActiveFilters && (
              <button
                onClick={resetFilters}
                className="flex items-center gap-1 px-3 py-2 rounded-xl text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100 transition-colors"
                title="Clear all filters"
              >
                <X className="w-3.5 h-3.5" />
                <span>Reset</span>
              </button>
            )}
          </div>
        </div>

        {/* Counter and Sorting Row */}
        <div className="flex items-center justify-between text-xs text-slate-500 pt-2 border-t border-slate-100">
          <div>
            Showing <strong className="text-slate-900 font-mono">{filteredCases.length}</strong> of{' '}
            <strong className="text-slate-700 font-mono">{cases.length}</strong> complaints
          </div>
          <div className="flex items-center gap-2">
            <span>Sort by:</span>
            <button
              onClick={() => toggleSort('created_at')}
              className={`font-medium ${sortField === 'created_at' ? 'text-blue-600 underline' : 'text-slate-600'}`}
            >
              Date {sortField === 'created_at' && (sortOrder === 'desc' ? '↓' : '↑')}
            </button>
            <span>•</span>
            <button
              onClick={() => toggleSort('loss')}
              className={`font-medium ${sortField === 'loss' ? 'text-blue-600 underline' : 'text-slate-600'}`}
            >
              Loss {sortField === 'loss' && (sortOrder === 'desc' ? '↓' : '↑')}
            </button>
            <span>•</span>
            <button
              onClick={() => toggleSort('priority')}
              className={`font-medium ${sortField === 'priority' ? 'text-blue-600 underline' : 'text-slate-600'}`}
            >
              Priority {sortField === 'priority' && (sortOrder === 'desc' ? '↓' : '↑')}
            </button>
          </div>
        </div>
      </div>

      {/* ── Table Card ── */}
      <div className="bg-white border border-slate-200/90 rounded-2xl shadow-card overflow-hidden">
        {loading ? (
          <div className="p-12 text-center">
            <div className="inline-block w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mb-3"></div>
            <p className="text-sm text-slate-500">Querying complaints repository...</p>
          </div>
        ) : filteredCases.length === 0 ? (
          <div className="p-12 text-center">
            <SlidersHorizontal className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-slate-800">No Matching Complaints</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              No complaint records matched your search query or filter selection.
            </p>
            {hasActiveFilters && (
              <button
                onClick={resetFilters}
                className="mt-3 px-4 py-1.5 rounded-xl text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition-colors"
              >
                Clear Filters
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="overflow-x-auto hidden md:block">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 text-xs uppercase font-semibold">
                  <tr>
                    <th className="py-3.5 px-4 cursor-pointer" onClick={() => toggleSort('created_at')}>
                      <div className="flex items-center gap-1.5">
                        <span>Case ID</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                    <th className="py-3.5 px-4 cursor-pointer" onClick={() => toggleSort('name')}>
                      <div className="flex items-center gap-1.5">
                        <span>Citizen Name</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                    <th className="py-3.5 px-4">Category</th>
                    <th className="py-3.5 px-4">Incident Date</th>
                    <th className="py-3.5 px-4 cursor-pointer" onClick={() => toggleSort('loss')}>
                      <div className="flex items-center gap-1.5">
                        <span>Reported Loss</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                    <th className="py-3.5 px-4">Language</th>
                    <th className="py-3.5 px-4 cursor-pointer" onClick={() => toggleSort('priority')}>
                      <div className="flex items-center gap-1.5">
                        <span>Priority</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                    <th className="py-3.5 px-4">Status</th>
                    <th className="py-3.5 px-4 cursor-pointer" onClick={() => toggleSort('created_at')}>
                      <div className="flex items-center gap-1.5">
                        <span>Logged At</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                    <th className="py-3.5 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {paginatedCases.map((c) => (
                    <tr
                      key={c.id}
                      onClick={() => onSelectCase(c.id)}
                      className="hover:bg-slate-50/80 transition-colors cursor-pointer group"
                    >
                      <td className="py-3.5 px-4 font-mono text-xs font-bold text-blue-600 group-hover:underline">
                        {c.report_id || c.id}
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-slate-900">{c.name}</div>
                        <div className="text-[11px] text-slate-500 font-mono">
                          {c.caller_phone || 'Twilio Voice'}
                        </div>
                      </td>
                      <td className="py-3.5 px-4">
                        <CategoryBadge
                          category={c.scenario}
                          label={c.scenario_label}
                          labelHi={c.scenario_label_hi}
                        />
                      </td>
                      <td className="py-3.5 px-4 text-xs text-slate-600">
                        {c.incident_date || 'Recent date'}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-xs font-semibold text-slate-900">
                        {c.financial_loss || 'Not specified'}
                      </td>
                      <td className="py-3.5 px-4 text-xs">
                        <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-mono text-[11px]">
                          {c.language === 'hi' ? 'HI (हिन्दी)' : 'EN'}
                        </span>
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
                            title="Open Investigation Dossier"
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
                              title="Download Official Bilingual PDF"
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

            {/* Mobile Cards */}
            <div className="divide-y divide-slate-100 md:hidden">
              {paginatedCases.map((c) => (
                <div
                  key={c.id}
                  onClick={() => onSelectCase(c.id)}
                  className="p-4 space-y-2.5 hover:bg-slate-50 transition-colors cursor-pointer"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className="font-mono text-xs font-bold text-blue-600">
                        {c.report_id || c.id}
                      </span>
                      <h4 className="text-base font-semibold text-slate-900 mt-0.5">
                        {c.name}
                      </h4>
                    </div>
                    <PriorityBadge priority={c.priority} size="sm" />
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <CategoryBadge
                      category={c.scenario}
                      label={c.scenario_label}
                      labelHi={c.scenario_label_hi}
                    />
                    <StatusBadge status={c.status} size="sm" />
                  </div>

                  <div className="flex items-center justify-between text-xs text-slate-600 pt-1">
                    <div>
                      <span>Loss: </span>
                      <span className="font-mono font-bold text-slate-900">
                        {c.financial_loss || 'Not specified'}
                      </span>
                    </div>
                    <span className="text-slate-400 font-mono">{c.created_at}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination Controls */}
            <div className="p-4 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
              <div>
                Page <strong className="text-slate-900">{currentPage}</strong> of{' '}
                <strong className="text-slate-900">{totalPages}</strong>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="p-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 disabled:opacity-40 transition-colors shadow-sm"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="p-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 disabled:opacity-40 transition-colors shadow-sm"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
