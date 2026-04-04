/**
 * ScoreRiskBadge — displays the composite RED/YELLOW/GREEN risk decision
 * produced by the Stage 6-8 pipeline.
 *
 * Rendered *below* the existing CLEAR/SUSPICIOUS/PROHIBITED badge inside
 * RiskBadge.jsx.  Never replaces it.
 *
 * Props
 * ─────
 *   decision       "RED" | "YELLOW" | "GREEN"
 *   final_risk     float 0–1
 *   visual_risk    float 0–1
 *   data_risk      float 0–1 | null   (null until LLM extractor is wired)
 *   risk_breakdown {
 *     suspicious_score, uncertain_ratio, ssim_risk, shap_intensity_score,
 *     value_anomaly, hs_code_risk, country_risk
 *   }
 */

// ── Score bar ────────────────────────────────────────────────────────────────

function ScoreBar({ label, value, barColor, pending = false, pendingLabel = 'Pending' }) {
  if (pending || value === null || value === undefined) {
    return (
      <div className="space-y-1">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-500">{label}</span>
          <span className="text-slate-400 italic">{pendingLabel}</span>
        </div>
        <div className="h-1.5 w-full rounded-full bg-slate-100" />
      </div>
    );
  }

  const pct = Math.round(Math.min(Math.max(value, 0), 1) * 100);

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-600">{label}</span>
        <span className="font-mono font-semibold text-slate-700">{pct}%</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-slate-100">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

// ── Decision theming ─────────────────────────────────────────────────────────

const DECISION_THEME = {
  RED: {
    badge:    'bg-red-600 text-white',
    dot:      'bg-red-300',
    border:   'border-red-200',
    barColor: 'bg-red-500',
    label:    'HIGH RISK',
  },
  YELLOW: {
    badge:    'bg-amber-400 text-amber-900',
    dot:      'bg-amber-600',
    border:   'border-amber-200',
    barColor: 'bg-amber-400',
    label:    'MEDIUM RISK',
  },
  GREEN: {
    badge:    'bg-emerald-500 text-white',
    dot:      'bg-emerald-200',
    border:   'border-emerald-200',
    barColor: 'bg-emerald-500',
    label:    'LOW RISK',
  },
};

const FALLBACK_THEME = {
  badge:    'bg-slate-400 text-white',
  dot:      'bg-slate-300',
  border:   'border-slate-200',
  barColor: 'bg-slate-400',
  label:    'UNKNOWN',
};

// ── Main component ───────────────────────────────────────────────────────────

export default function ScoreRiskBadge({
  decision,
  final_risk,
  visual_risk,
  data_risk,
  risk_breakdown,
}) {
  const theme = DECISION_THEME[decision] ?? FALLBACK_THEME;
  const finalPct = typeof final_risk === 'number'
    ? Math.round(Math.min(Math.max(final_risk, 0), 1) * 100)
    : null;

  const bd = risk_breakdown ?? {};

  return (
    <div className={`rounded-2xl border ${theme.border} bg-white shadow-sm overflow-hidden`}>

      {/* ── Header: decision chip + final score ────────────────────── */}
      <div className="flex items-center justify-between gap-4 px-6 py-5">
        <div className="space-y-1">
          <div className="text-xs font-semibold uppercase tracking-widest text-slate-500">
            Composite risk score
          </div>
          <div className="flex items-center gap-2.5">
            <span
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1 text-sm font-bold tracking-wide ${theme.badge}`}
            >
              <span className={`h-2 w-2 rounded-full ${theme.dot}`} />
              {decision ?? '—'}
            </span>
            <span className="text-xs text-slate-500">{theme.label}</span>
          </div>
        </div>

        <div className="text-right">
          <div className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-0.5">
            Final risk
          </div>
          <div className="text-3xl font-bold tabular-nums text-slate-900">
            {finalPct !== null ? `${finalPct}%` : '—'}
          </div>
        </div>
      </div>

      {/* ── Risk components (visual + data) ────────────────────────── */}
      <div className="border-t border-slate-100 px-6 py-4 space-y-3">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
          Risk components
        </div>

        <ScoreBar
          label="Visual Risk"
          value={visual_risk}
          barColor="bg-cyan-500"
        />

        <ScoreBar
          label="Data Risk"
          value={data_risk}
          barColor="bg-indigo-500"
          pending={data_risk === null}
          pendingLabel="Pending — awaiting invoice"
        />
      </div>

      {/* ── Breakdown sub-scores ────────────────────────────────────── */}
      <div className="border-t border-slate-100 px-6 py-4 space-y-3">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
          Breakdown
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">

          {/* Visual risk inputs */}
          <ScoreBar
            label="Suspicious score"
            value={bd.suspicious_score}
            barColor="bg-red-400"
          />
          <ScoreBar
            label="Uncertain ratio"
            value={bd.uncertain_ratio}
            barColor="bg-amber-400"
          />
          <ScoreBar
            label="SSIM risk"
            value={bd.ssim_risk}
            barColor="bg-blue-400"
          />
          <ScoreBar
            label="SHAP intensity"
            value={bd.shap_intensity_score}
            barColor="bg-purple-400"
            pending={bd.shap_intensity_score === null}
            pendingLabel="Pending"
          />

          {/* Data risk inputs — pending until invoice extraction lands */}
          <ScoreBar
            label="Value anomaly"
            value={bd.value_anomaly}
            barColor="bg-indigo-400"
            pending={bd.value_anomaly === null}
            pendingLabel="Pending — awaiting invoice"
          />
          <ScoreBar
            label="HS code risk"
            value={bd.hs_code_risk}
            barColor="bg-violet-400"
            pending={bd.hs_code_risk === null}
            pendingLabel="Pending — awaiting invoice"
          />
          <ScoreBar
            label="Country risk"
            value={bd.country_risk}
            barColor="bg-rose-400"
            pending={bd.country_risk === null}
            pendingLabel="Pending — awaiting invoice"
          />

        </div>
      </div>

    </div>
  );
}
