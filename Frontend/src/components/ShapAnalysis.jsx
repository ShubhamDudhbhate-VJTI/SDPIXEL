/**
 * ShapAnalysis — displays the structured output from the external SHAP
 * explainability service (outputs.shap).
 *
 * Props
 * ─────
 *   shap  {
 *     label:       string   — top detected class name
 *     confidence:  number   — detection confidence [0, 1]
 *     strength:    string   — "High" | "Medium" | "Low"
 *     reliability: string   — human-readable reliability descriptor
 *     coverage:    number   — high-attribution pixel coverage [0, 100]
 *     verdict:     string   — human-readable SHAP verdict
 *   }
 *
 * Styled to match the existing card-based dashboard UI.
 */

import { Activity } from 'lucide-react';

// ── Strength theming ─────────────────────────────────────────────────────────

const STRENGTH_THEME = {
  High:   { chip: 'bg-red-100 text-red-800 border border-red-200',    dot: 'bg-red-500' },
  Medium: { chip: 'bg-amber-100 text-amber-800 border border-amber-200', dot: 'bg-amber-500' },
  Low:    { chip: 'bg-emerald-100 text-emerald-800 border border-emerald-200', dot: 'bg-emerald-500' },
};

function strengthTheme(strength) {
  return STRENGTH_THEME[strength] ?? {
    chip: 'bg-slate-100 text-slate-700 border border-slate-200',
    dot:  'bg-slate-400',
  };
}

// ── Coverage bar ─────────────────────────────────────────────────────────────

function CoverageBar({ coverage }) {
  const pct = Math.round(Math.min(Math.max(coverage ?? 0, 0), 100));
  // colour the bar based on coverage intensity
  const barColor = pct >= 30 ? 'bg-red-500' : pct >= 10 ? 'bg-amber-400' : 'bg-emerald-400';

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium text-slate-600">Attribution coverage</span>
        <span className="font-mono font-semibold text-slate-800">{pct}%</span>
      </div>
      <div className="h-2 w-full rounded-full bg-slate-100">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-xs text-slate-500">
        Percentage of image pixels with significant SHAP attribution weight
      </p>
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

export default function ShapAnalysis({ shap }) {
  if (!shap) return null;

  const {
    label,
    confidence,
    strength,
    reliability,
    coverage,
    verdict,
  } = shap;

  const confPct = typeof confidence === 'number'
    ? Math.round(confidence * 100)
    : null;

  const st = strengthTheme(strength);

  return (
    <div className="card card-hover space-y-5">

      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="section-title">SHAP Explainability</h3>
        <span className="section-subtitle">External attribution service</span>
      </div>

      {/* ── Detection row ───────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Label chip */}
        <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
          <Activity className="h-4 w-4 shrink-0 text-slate-500" />
          <span className="text-sm font-semibold text-slate-800">
            {label ?? '—'}
          </span>
        </div>

        {/* Confidence */}
        {confPct !== null && (
          <div className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-center">
            <div className="text-xs font-semibold uppercase tracking-widest text-slate-400">
              Confidence
            </div>
            <div className="text-xl font-bold tabular-nums text-slate-900">
              {confPct}%
            </div>
          </div>
        )}

        {/* Strength badge */}
        {strength && (
          <span className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold ${st.chip}`}>
            <span className={`h-2 w-2 rounded-full ${st.dot}`} />
            {strength} strength
          </span>
        )}

        {/* Reliability */}
        {reliability && (
          <span className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600">
            Reliability: <span className="font-semibold text-slate-800">{reliability}</span>
          </span>
        )}
      </div>

      {/* ── Coverage bar ────────────────────────────────────────────── */}
      <div className="rounded-xl border border-slate-200 bg-slate-50/70 px-4 py-4">
        <CoverageBar coverage={coverage} />
      </div>

      {/* ── Verdict ─────────────────────────────────────────────────── */}
      {verdict && (
        <div className="rounded-xl border border-slate-200 bg-white px-4 py-4">
          <div className="mb-1.5 text-xs font-semibold uppercase tracking-widest text-slate-400">
            Verdict
          </div>
          <p className="text-sm leading-relaxed text-slate-700">{verdict}</p>
        </div>
      )}

    </div>
  );
}
