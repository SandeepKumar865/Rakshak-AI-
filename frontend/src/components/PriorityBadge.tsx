import React from 'react';
import { CasePriority } from '../types';
import { AlertCircle, AlertTriangle, Info, CheckCircle2 } from 'lucide-react';

interface PriorityBadgeProps {
  priority: CasePriority | string;
  showIcon?: boolean;
  size?: 'sm' | 'md';
}

export const PriorityBadge: React.FC<PriorityBadgeProps> = ({
  priority,
  showIcon = true,
  size = 'md',
}) => {
  const norm = (priority || 'Low').toLowerCase();

  let styles = 'bg-slate-100 text-slate-700 border-slate-200';
  let Icon = Info;

  if (norm.includes('critical')) {
    styles = 'bg-rose-50 text-rose-700 border-rose-200';
    Icon = AlertCircle;
  } else if (norm.includes('high')) {
    styles = 'bg-orange-50 text-orange-700 border-orange-200';
    Icon = AlertTriangle;
  } else if (norm.includes('medium')) {
    styles = 'bg-amber-50 text-amber-700 border-amber-200';
    Icon = AlertTriangle;
  } else {
    styles = 'bg-slate-100 text-slate-600 border-slate-200';
    Icon = CheckCircle2;
  }

  const padding = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-semibold rounded-md border ${padding} ${styles} uppercase tracking-wider text-[11px]`}
      title="Priority level based on financial loss & threat indicators"
    >
      {showIcon && <Icon className="w-3 h-3" />}
      <span>{priority || 'Low'}</span>
    </span>
  );
};
