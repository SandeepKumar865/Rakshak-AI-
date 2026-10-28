import React from 'react';
import { CaseStatus } from '../types';

interface StatusBadgeProps {
  status: CaseStatus | string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const norm = (status || 'New').toLowerCase();

  let styles = 'bg-slate-100 text-slate-700 border-slate-200';
  let dot = 'bg-slate-400';

  if (norm.includes('new')) {
    styles = 'bg-blue-50 text-blue-700 border-blue-200';
    dot = 'bg-blue-500';
  } else if (norm.includes('review')) {
    styles = 'bg-amber-50 text-amber-700 border-amber-200';
    dot = 'bg-amber-500';
  } else if (norm.includes('investigat')) {
    styles = 'bg-indigo-50 text-indigo-700 border-indigo-200';
    dot = 'bg-indigo-500';
  } else if (norm.includes('resolved') || norm.includes('completed')) {
    styles = 'bg-emerald-50 text-emerald-700 border-emerald-200';
    dot = 'bg-emerald-500';
  } else if (norm.includes('closed')) {
    styles = 'bg-slate-100 text-slate-600 border-slate-200';
    dot = 'bg-slate-400';
  }

  const padding = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium rounded-full border ${padding} ${styles}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      <span>{status || 'New'}</span>
    </span>
  );
};
