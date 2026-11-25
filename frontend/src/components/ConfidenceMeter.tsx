import React from 'react';

interface Props {
  confidence: number; // 0.0 to 1.0
  showLabel?: boolean;
}

export default function ConfidenceMeter({ confidence, showLabel = true }: Props) {
  const pct = Math.min(100, Math.max(0, Math.round(confidence * 100)));

  let barColor = 'bg-slate-500';
  let textColor = 'text-slate-700';

  if (pct >= 80) {
    barColor = 'bg-emerald-500';
    textColor = 'text-emerald-700';
  } else if (pct >= 60) {
    barColor = 'bg-amber-500';
    textColor = 'text-amber-700';
  } else {
    barColor = 'bg-rose-500';
    textColor = 'text-rose-700';
  }

  return (
    <div className="w-full">
      {showLabel && (
        <div className="flex justify-between items-center text-xs font-semibold mb-1">
          <span className="text-gray-600">Verification Confidence</span>
          <span className={textColor}>{pct}%</span>
        </div>
      )}
      <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
        <div
          className={`h-2.5 rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
