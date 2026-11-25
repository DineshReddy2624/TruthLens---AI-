import React from 'react';
import { VerdictLabelType } from '../types';
import { CheckCircle2, XCircle, AlertTriangle, HelpCircle, AlertOctagon } from 'lucide-react';

interface Props {
  label: VerdictLabelType | string;
  size?: 'sm' | 'md' | 'lg';
}

export default function VerdictBadge({ label, size = 'md' }: Props) {
  const norm = label.toLowerCase();

  let colorClasses = 'bg-slate-100 text-slate-800 border-slate-300';
  let Icon = HelpCircle;

  if (norm.includes('supported') && !norm.includes('partially')) {
    colorClasses = 'bg-emerald-100 text-emerald-800 border-emerald-300';
    Icon = CheckCircle2;
  } else if (norm.includes('contradicted')) {
    colorClasses = 'bg-rose-100 text-rose-800 border-rose-300';
    Icon = XCircle;
  } else if (norm.includes('partially')) {
    colorClasses = 'bg-amber-100 text-amber-800 border-amber-300';
    Icon = AlertTriangle;
  } else if (norm.includes('conflicting')) {
    colorClasses = 'bg-purple-100 text-purple-800 border-purple-300';
    Icon = AlertOctagon;
  } else {
    colorClasses = 'bg-slate-100 text-slate-700 border-slate-300';
    Icon = HelpCircle;
  }

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs font-medium space-x-1',
    md: 'px-3 py-1 text-sm font-semibold space-x-1.5',
    lg: 'px-4 py-2 text-base font-bold space-x-2',
  }[size];

  const iconSizes = {
    sm: 12,
    md: 16,
    lg: 20,
  }[size];

  return (
    <span
      className={`inline-flex items-center rounded-full border ${colorClasses} ${sizeClasses}`}
    >
      <Icon size={iconSizes} className="shrink-0" />
      <span>{label}</span>
    </span>
  );
}
