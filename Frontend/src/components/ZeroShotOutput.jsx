import { useMemo, useState } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Eye,
} from 'lucide-react';
import { resolveAssetUrl } from '../api/assets';

// ── Verdict theming ─────────────────────────────────────────────────────
const VERDICT_THEME = {
  CLEAR: {
    bg: 'bg-emerald-50 border-emerald-200',
    text: 'text-emerald-800',
    icon: ShieldCheck,
    label: '✅ CLEAR',
  },
  'UNDECLARED ITEMS DETECTED': {
    bg: 'bg-amber-50 border-amber-200',
    text: 'text-amber-800',
    icon: ShieldAlert,
    label: '🚨 UNDECLARED ITEMS DETECTED',
  },
  'SUSPICIOUS: MISSING DECLARED GOODS — REQUIRES HUMAN INSPECTION': {
    bg: 'bg-red-50 border-red-200',
    text: 'text-red-800',
    icon: ShieldX,
    label: '🔴 SUSPICIOUS: MISSING DECLARED GOODS',
  },
  'CRITICAL: UNDECLARED ITEMS + MISSING DECLARED GOODS': {
    bg: 'bg-red-50 border-red-300',
    text: 'text-red-900',
    icon: ShieldX,
    label: '🔴 CRITICAL: UNDECLARED + MISSING',
  },
};

function getTheme(verdict) {
  return (
    VERDICT_THEME[verdict] ?? {
      bg: 'bg-slate-50 border-slate-200',
      text: 'text-slate-800',
      icon: Eye,
      label: verdict ?? 'Unknown',
    }
  );
}

// ── Component ───────────────────────────────────────────────────────────
export default function ZeroShotOutput({ outputs, originalImageUrl }) {
  const zs = outputs?.zeroShot ?? null;
  const [showTimings, setShowTimings] = useState(false);

  const overlayUrl = useMemo(
    () => resolveAssetUrl(zs?.overlayImage),
    [zs?.overlayImage],
  );

  // No zero-shot data at all
  if (!zs) {
    return (
      <div className="card card-hover">
        <div className="flex items-baseline justify-between gap-3 mb-4">
          <h3 className="section-title">Zero-Shot Inspection</h3>
          <span className="section-subtitle">OWL-ViT v2 + SAM 2</span>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-6 text-center">
          <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-900/5 border border-slate-200">
            <Eye className="w-5 h-5 text-slate-600" />
          </div>
          <div className="text-sm font-semibold text-slate-900">
            Waiting for analysis
          </div>
          <div className="text-xs text-slate-500 mt-1">
            Zero-shot inspection will run automatically after YOLO detection.
          </div>
        </div>
      </div>
    );
  }

  const theme = getTheme(zs.verdict);
  const VerdictIcon = theme.icon;
  const items = zs.items ?? [];
  const requiresHumanIntervention =
    Array.isArray(zs.labelsUsed) &&
    zs.labelsUsed.length > 0 &&
    Array.isArray(zs.missingItems) &&
    zs.missingItems.length === zs.labelsUsed.length;

  return (
    <div className="card card-hover space-y-5">
      {/* Header */}
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="section-title">Zero-Shot Inspection</h3>
        <span className="section-subtitle">OWL-ViT v2 + SAM 2</span>
      </div>

      {/* ── Verdict Banner ──────────────────────────────────────────── */}
      <div className={`rounded-xl border p-4 ${theme.bg}`}>
        <div className="flex items-center gap-3">
          <VerdictIcon className={`w-6 h-6 shrink-0 ${theme.text}`} />
          <div>
            <div className={`text-sm font-bold ${theme.text}`}>
              {theme.label}
            </div>
            {zs.labelsUsed && (
              <div className="text-xs text-slate-500 mt-0.5">
                Scanned against {zs.labelsUsed.length} label(s)
              </div>
            )}
          </div>
        </div>
      </div>

      {requiresHumanIntervention && (
        <div className="rounded-xl border border-amber-200 bg-amber-50/80 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
            <div>
              <div className="text-sm font-bold text-amber-900">
                Suspicious cargo — human intervention required
              </div>
              <p className="text-xs text-amber-800 mt-1">
                None of the declared manifest items were visually detected in the scan.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ── Missing Items Callout ───────────────────────────────────── */}
      {zs.missingItems?.length > 0 && (
        <div className="rounded-xl border border-red-200 bg-red-50/80 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
            <div>
              <div className="text-sm font-bold text-red-800">
                Missing Declared Items
              </div>
              <p className="text-xs text-red-700 mt-1">
                The following items are listed in the manifest but were{' '}
                <strong>NOT visually detected</strong> in the scan:
              </p>
              <div className="flex flex-wrap gap-1.5 mt-2">
                {zs.missingItems.map((item, idx) => (
                  <span
                    key={`${item}-${idx}`}
                    className="inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-semibold bg-red-100 text-red-800 border border-red-200"
                  >
                    {item}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Metrics Row ─────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Total Objects', value: zs.totalObjects, color: 'text-slate-900' },
          { label: 'Declared ✓', value: zs.declaredCount, color: 'text-emerald-700' },
          { label: 'Undeclared ⚠', value: zs.undeclaredCount, color: 'text-amber-700' },
          { label: 'Missing 🚫', value: zs.missingCount, color: 'text-red-700' },
        ].map((m) => (
          <div
            key={m.label}
            className="rounded-xl border border-slate-200 bg-white/80 p-3 text-center"
          >
            <div className={`text-2xl font-bold ${m.color}`}>
              {m.value ?? 0}
            </div>
            <div className="text-xs text-slate-500 mt-0.5">{m.label}</div>
          </div>
        ))}
      </div>

      {/* ── Side-by-side: Original vs Overlay ───────────────────────── */}
      {overlayUrl && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {originalImageUrl && (
            <div>
              <div className="text-xs font-semibold text-slate-700 mb-2">
                Original Scan
              </div>
              <div className="overflow-hidden rounded-xl bg-slate-100 border border-slate-200/70">
                <img
                  src={originalImageUrl}
                  alt="Original scan"
                  className="w-full h-auto"
                />
              </div>
            </div>
          )}
          <div>
            <div className="text-xs font-semibold text-slate-700 mb-2">
              Inspection Overlay
            </div>
            <div className="overflow-hidden rounded-xl bg-slate-100 border border-slate-200/70">
              <img
                src={overlayUrl}
                alt="Zero-shot inspection overlay"
                className="w-full h-auto"
              />
            </div>
          </div>
        </div>
      )}

      {/* ── Detailed Items Table ─────────────────────────────────────── */}
      {items.length > 0 && (
        <div>
          <div className="text-xs font-semibold text-slate-700 mb-2">
            Detected Items ({items.length})
          </div>
          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">
                  <th className="px-4 py-2.5">#</th>
                  <th className="px-4 py-2.5">Status</th>
                  <th className="px-4 py-2.5">Label</th>
                  <th className="px-4 py-2.5 text-right">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((item, idx) => {
                  const isDeclared = item.status === 'declared';
                  const rowBg = isDeclared
                    ? 'bg-emerald-50/40'
                    : 'bg-red-50/40';

                  return (
                    <tr key={`${item.label}-${idx}`} className={rowBg}>
                      <td className="px-4 py-2 text-slate-500 font-mono text-xs">
                        {item.index}
                      </td>
                      <td className="px-4 py-2">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold ${
                            isDeclared
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {isDeclared ? '✓ declared' : '⚠ undeclared'}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-slate-800 font-medium">
                        {item.label}
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-slate-700">
                        {((item.confidence ?? 0) * 100).toFixed(1)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Timing Breakdown (collapsible) ───────────────────────────── */}
      {zs.timings && Object.keys(zs.timings).length > 0 && (
        <div className="rounded-xl border border-slate-200 overflow-hidden">
          <button
            type="button"
            onClick={() => setShowTimings((v) => !v)}
            className="w-full flex items-center justify-between px-4 py-2.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
          >
            <span>⏱ Pipeline Timing Breakdown</span>
            {showTimings ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
          {showTimings && (
            <div className="border-t border-slate-100">
              <table className="w-full text-sm">
                <tbody className="divide-y divide-slate-50">
                  {Object.entries(zs.timings).map(([stage, secs]) => (
                    <tr key={stage}>
                      <td className="px-4 py-2 text-slate-600 capitalize">
                        {stage.replace(/_/g, ' ')}
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-slate-700">
                        {secs}s
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
