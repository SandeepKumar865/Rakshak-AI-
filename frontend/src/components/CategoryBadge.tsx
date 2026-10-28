import React from 'react';
import { CreditCard, ShoppingBag, Briefcase, Banknote, Shield } from 'lucide-react';

interface CategoryBadgeProps {
  category: string;
  label?: string;
  labelHi?: string;
  language?: string;
}

export const CategoryBadge: React.FC<CategoryBadgeProps> = ({
  category,
  label,
  labelHi,
  language,
}) => {
  const norm = (category || '').toUpperCase();

  let Icon = Shield;
  let bg = 'bg-slate-100 text-slate-700 border-slate-200';

  if (norm.includes('OTP') || norm.includes('BANK')) {
    Icon = CreditCard;
    bg = 'bg-blue-50 text-blue-700 border-blue-200';
  } else if (norm.includes('OLX') || norm.includes('QR')) {
    Icon = ShoppingBag;
    bg = 'bg-emerald-50 text-emerald-700 border-emerald-200';
  } else if (norm.includes('JOB') || norm.includes('TELEGRAM')) {
    Icon = Briefcase;
    bg = 'bg-amber-50 text-amber-700 border-amber-200';
  } else if (norm.includes('LOAN') || norm.includes('EXTORTION')) {
    Icon = Banknote;
    bg = 'bg-rose-50 text-rose-700 border-rose-200';
  }

  const displayLabel = label || category.replace(/_/g, ' ');

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 text-xs font-medium rounded-md border ${bg}`}
      title={labelHi ? `${displayLabel} (${labelHi})` : displayLabel}
    >
      <Icon className="w-3.5 h-3.5 shrink-0 opacity-75" />
      <span className="truncate max-w-[190px]">{displayLabel}</span>
    </span>
  );
};
