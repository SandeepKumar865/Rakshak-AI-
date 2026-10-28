import React from 'react';
import { LucideIcon } from 'lucide-react';

interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: string;
  trendType?: 'positive' | 'negative' | 'neutral' | 'alert';
  colorTheme?: 'cyan' | 'blue' | 'rose' | 'amber' | 'emerald' | 'purple';
  loading?: boolean;
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  trendType = 'neutral',
  colorTheme = 'blue',
  loading = false,
}) => {
  const themeColors = {
    cyan: {
      iconBg: 'bg-sky-50 text-sky-600 border border-sky-100',
    },
    blue: {
      iconBg: 'bg-blue-50 text-blue-600 border border-blue-100',
    },
    rose: {
      iconBg: 'bg-rose-50 text-rose-600 border border-rose-100',
    },
    amber: {
      iconBg: 'bg-amber-50 text-amber-600 border border-amber-100',
    },
    emerald: {
      iconBg: 'bg-emerald-50 text-emerald-600 border border-emerald-100',
    },
    purple: {
      iconBg: 'bg-purple-50 text-purple-600 border border-purple-100',
    },
  };

  const selectedTheme = themeColors[colorTheme] || themeColors.blue;

  if (loading) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-card animate-pulse">
        <div className="flex items-center justify-between mb-3">
          <div className="h-3.5 bg-slate-200 rounded w-24"></div>
          <div className="h-9 w-9 bg-slate-100 rounded-lg"></div>
        </div>
        <div className="h-7 bg-slate-200 rounded w-20 mb-2"></div>
        <div className="h-3 bg-slate-100 rounded w-32"></div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-slate-200/90 rounded-xl p-5 shadow-card hover:shadow-card-hover transition-all duration-150">
      <div className="flex items-center justify-between mb-2.5">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          {title}
        </span>
        <div className={`p-2 rounded-lg ${selectedTheme.iconBg}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>

      <div className="flex items-baseline gap-2 mb-1">
        <span className="text-2xl lg:text-3xl font-bold text-slate-900 tracking-tight font-mono">
          {value !== undefined && value !== null && value !== '' ? value : 'N/A'}
        </span>
        {trend && (
          <span
            className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
              trendType === 'alert'
                ? 'bg-rose-50 text-rose-700 border border-rose-200'
                : trendType === 'positive'
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                : 'bg-slate-100 text-slate-600 border border-slate-200'
            }`}
          >
            {trend}
          </span>
        )}
      </div>

      {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
    </div>
  );
};
