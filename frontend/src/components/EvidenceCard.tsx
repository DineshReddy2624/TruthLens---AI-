import React, { useState } from 'react';
import { EvidenceRecord, RetrievedSource } from '../types';
import { ExternalLink, Award, ChevronDown, ChevronUp } from 'lucide-react';

interface Props {
  evidence: EvidenceRecord;
  source?: RetrievedSource;
  highlighted?: boolean;
}

export default function EvidenceCard({ evidence, source, highlighted = false }: Props) {
  const [showEvaluation, setShowEvaluation] = useState(false);

  const nliLabel = (evidence.nli_label || '').toLowerCase();
  let badgeColor = 'bg-slate-100 text-slate-700 border-slate-300';
  if (nliLabel === 'entailment') {
    badgeColor = 'bg-emerald-50 text-emerald-700 border-emerald-300';
  } else if (nliLabel === 'contradiction') {
    badgeColor = 'bg-rose-50 text-rose-700 border-rose-300';
  } else if (nliLabel === 'neutral') {
    badgeColor = 'bg-slate-50 text-slate-600 border-slate-200';
  }

  const evaluation = source?.evaluation;

  return (
    <div
      className={`rounded-xl border p-4 transition-all duration-300 ${
        highlighted
          ? 'ring-2 ring-blue-500 bg-blue-50/40 border-blue-300 shadow-md'
          : 'bg-white border-slate-200 hover:border-slate-300 shadow-sm'
      }`}
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div>
          <span className="text-xs font-bold text-slate-900 block line-clamp-1">
            {source?.title || source?.domain || 'Retrieved Web Passage'}
          </span>
          {source?.url && (
            <a
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[11px] text-blue-600 hover:underline inline-flex items-center gap-1 mt-0.5"
            >
              <span>{source.domain || source.url}</span>
              <ExternalLink size={10} />
            </a>
          )}
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          {evidence.nli_label && (
            <span className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full border ${badgeColor}`}>
              {evidence.nli_label}
            </span>
          )}
          {evidence.rank_score !== undefined && (
            <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
              Rank: {(evidence.rank_score * 100).toFixed(0)}%
            </span>
          )}
        </div>
      </div>

      <p className="text-xs text-slate-700 leading-relaxed italic bg-slate-50/70 p-3 rounded-lg border border-slate-100">
        "{evidence.passage}"
      </p>

      {/* Credibility Evaluation Drawer */}
      {evaluation && (
        <div className="mt-3 pt-2 border-t border-slate-100">
          <button
            onClick={() => setShowEvaluation(!showEvaluation)}
            className="flex items-center justify-between w-full text-[11px] font-medium text-slate-600 hover:text-blue-600 transition-colors"
          >
            <div className="flex items-center gap-1">
              <Award size={12} className="text-blue-500" />
              <span>Source Credibility: <b>{evaluation.total_score.toFixed(1)} / 8.0</b></span>
            </div>
            {showEvaluation ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>

          {showEvaluation && (
            <div className="mt-2 text-[11px] bg-slate-50 p-2.5 rounded-lg border border-slate-200 space-y-1.5">
              <div className="grid grid-cols-2 gap-2 text-slate-600">
                <div>Publisher Identity: <b className="text-slate-800">{evaluation.publisher_score.toFixed(1)}/2.0</b></div>
                <div>Date vs Timeliness: <b className="text-slate-800">{evaluation.date_score.toFixed(1)}/2.0</b></div>
                <div>Evidence Quality: <b className="text-slate-800">{evaluation.quality_score.toFixed(1)}/2.0</b></div>
                <div>Corroboration: <b className="text-slate-800">{evaluation.corroboration_score.toFixed(1)}/2.0</b></div>
              </div>
              {evaluation.reason && (
                <p className="text-slate-600 pt-1 border-t border-slate-200">
                  <span className="font-semibold text-slate-700">Reason:</span> {evaluation.reason}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
