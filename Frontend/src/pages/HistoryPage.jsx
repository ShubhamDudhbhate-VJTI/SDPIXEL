import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ClipboardCopy, Search, ChevronDown, Clock, CheckCircle2,
  XCircle, SkipForward, Loader2, ShieldCheck, AlertTriangle,
  Zap, Eye, FileText, Brain, Scan, BarChart3, Layers, Package
} from 'lucide-react';
import { getTransactionById, listRecentTransactions } from '../utils/transactions';
import { getApiBaseUrl } from '../api/analyze';

const MotionButton = motion.button;
const MotionDiv = motion.div;

/* ── Step metadata ────────────────────────────────────────────────────── */

const STEP_META = {
  manifest_extraction: {
    label: 'Manifest Extraction',
    icon: FileText,
    why: 'Extracts declared items from the commercial invoice PDF',
    color: 'text-blue-600',
  },
  vlm_extraction: {
    label: 'VLM Invoice Parser',
    icon: Brain,
    why: 'Extracts structured invoice data using Vision Language Model',
    color: 'text-violet-600',
  },
  yolov8_detection: {
    label: 'YOLO Detection',
    icon: Scan,
    why: 'Detects objects in the X-ray image using YOLO model',
    color: 'text-teal-600',
  },
  risk_scoring: {
    label: 'Legacy Risk Scoring',
    icon: ShieldCheck,
    why: 'Classifies detected objects as CLEAR / SUSPICIOUS / PROHIBITED',
    color: 'text-amber-600',
  },
  gradcam_generation: {
    label: 'Grad-CAM Heatmap',
    icon: Eye,
    why: 'Generates AI attention heatmap showing model focus areas',
    color: 'text-orange-600',
  },
  shap_explainer: {
    label: 'SHAP Explainer',
    icon: Zap,
    why: 'Explains which image regions influenced the detection decision',
    color: 'text-rose-600',
  },
  shap_service: {
    label: 'SHAP Service',
    icon: Zap,
    why: 'Explains which image regions influenced the detection decision',
    color: 'text-rose-600',
  },
  ssim_comparison: {
    label: 'SSIM Comparison',
    icon: Layers,
    why: 'Compares current scan against reference scan for anomalies',
    color: 'text-cyan-600',
  },
  zero_shot_inspection: {
    label: 'Zero-Shot Inspection',
    icon: Package,
    why: 'Checks if declared manifest items are visually present in the scan',
    color: 'text-indigo-600',
  },
  composite_risk_scoring: {
    label: 'Composite Risk Scoring',
    icon: BarChart3,
    why: 'Combines all signals into final RED / YELLOW / GREEN risk decision',
    color: 'text-red-600',
  },
  data_risk_analysis: {
    label: 'Data Risk Analysis',
    icon: BarChart3,
    why: 'Scores financial and regulatory risk from invoice data',
    color: 'text-pink-600',
  },
};

const getStepMeta = (service) => STEP_META[service] || {
  label: service.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
  icon: CheckCircle2,
  why: '',
  color: 'text-slate-600',
};

/* ── Status badge helper ──────────────────────────────────────────────── */

const StatusBadge = ({ status }) => {
  if (status === 'success') return (
    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 border border-emerald-200 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-emerald-700">
      <CheckCircle2 className="w-3 h-3" /> Success
    </span>
  );
  if (status === 'failed') return (
    <span className="inline-flex items-center gap-1 rounded-full bg-red-50 border border-red-200 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-red-700">
      <XCircle className="w-3 h-3" /> Failed
    </span>
  );
  if (status === 'skipped') return (
    <span className="inline-flex items-center gap-1 rounded-full bg-slate-50 border border-slate-200 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-slate-500">
      <SkipForward className="w-3 h-3" /> Skipped
    </span>
  );
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-slate-50 border border-slate-200 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-slate-500">
      {status}
    </span>
  );
};

/* ── Decision badge ───────────────────────────────────────────────────── */

const DecisionBadge = ({ decision }) => {
  const style = decision === 'RED'
    ? 'bg-red-600 text-white shadow-red-600/30'
    : decision === 'YELLOW'
      ? 'bg-amber-500 text-white shadow-amber-500/30'
      : decision === 'GREEN'
        ? 'bg-emerald-600 text-white shadow-emerald-600/30'
        : 'bg-slate-400 text-white';
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-xl px-4 py-2 text-sm font-extrabold uppercase tracking-wider shadow-lg ${style}`}>
      {decision === 'RED' ? <AlertTriangle className="w-4 h-4" /> : <ShieldCheck className="w-4 h-4" />}
      {decision}
    </span>
  );
};

/* ── Risk bar ─────────────────────────────────────────────────────────── */

const RiskBar = ({ label, value, max = 1 }) => {
  const pct = value != null ? Math.min(Math.round((value / max) * 100), 100) : null;
  const barColor = pct == null ? 'bg-slate-200'
    : pct >= 70 ? 'bg-red-500'
    : pct >= 40 ? 'bg-amber-500'
    : 'bg-emerald-500';
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-semibold text-slate-600">{label}</span>
        <span className="text-xs font-bold text-slate-900">
          {pct != null ? `${pct}%` : 'Pending'}
        </span>
      </div>
      <div className="h-2.5 rounded-full bg-slate-100 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${barColor}`}
          style={{ width: `${pct ?? 0}%` }}
        />
      </div>
    </div>
  );
};

/* ── Data renderer (summary of input/output objects) ──────────────────── */

const DataSummary = ({ data, title }) => {
  if (!data || typeof data !== 'object') return null;
  const entries = Object.entries(data);
  if (entries.length === 0) return null;
  return (
    <div className="mt-2">
      <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400 mb-1">{title}</p>
      <div className="rounded-lg bg-slate-50/80 border border-slate-100 px-3 py-2 space-y-1">
        {entries.slice(0, 12).map(([k, v]) => (
          <div key={k} className="flex items-start gap-2 text-xs">
            <span className="font-semibold text-slate-500 shrink-0 min-w-[100px]">{k}:</span>
            <span className="text-slate-800 break-all">
              {Array.isArray(v) ? v.join(', ') || '—' : v == null ? '—' : String(v)}
            </span>
          </div>
        ))}
        {entries.length > 12 && (
          <p className="text-[10px] text-slate-400">+{entries.length - 12} more fields</p>
        )}
      </div>
    </div>
  );
};

/* ── Expandable Step Card ─────────────────────────────────────────────── */

const StepCard = ({ step, index }) => {
  const [open, setOpen] = useState(false);
  const meta = getStepMeta(step.service);
  const Icon = meta.icon;

  return (
    <MotionDiv
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04 }}
      className="rounded-xl border border-slate-200/80 bg-white/90 shadow-sm overflow-hidden"
    >
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-slate-50/80 transition-colors"
      >
        <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white border border-slate-200 ${meta.color}`}>
          <Icon className="w-4 h-4" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-slate-900">{meta.label}</span>
            <StatusBadge status={step.status} />
          </div>
          {meta.why && (
            <p className="text-[11px] text-slate-500 mt-0.5 leading-snug">{meta.why}</p>
          )}
        </div>
        <div className="flex items-center gap-3 shrink-0">
          {step.latency != null && (
            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-400">
              <Clock className="w-3 h-3" />
              {step.latency.toFixed(2)}s
            </span>
          )}
          <motion.span
            animate={{ rotate: open ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <ChevronDown className="w-4 h-4 text-slate-400" />
          </motion.span>
        </div>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <MotionDiv
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
            className="border-t border-slate-100"
          >
            <div className="px-4 py-3 space-y-2">
              {step.error && (
                <div className="rounded-lg bg-red-50 border border-red-100 px-3 py-2 text-xs text-red-700">
                  <span className="font-bold">Error: </span>{step.error}
                </div>
              )}
              <DataSummary data={step.input} title="Input" />
              <DataSummary data={step.output} title="Output" />
              {step.model_version && (
                <p className="text-[11px] text-slate-400">
                  <span className="font-semibold">Model:</span> {step.model_version}
                </p>
              )}
            </div>
          </MotionDiv>
        )}
      </AnimatePresence>
    </MotionDiv>
  );
};

/* ═══════════════════════════════════════════════════════════════════════ */
/*  Main Page                                                            */
/* ═══════════════════════════════════════════════════════════════════════ */

const HistoryPage = () => {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [auditData, setAuditData] = useState(null);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditError, setAuditError] = useState(null);

  const recent = listRecentTransactions(8);

  /* Fetch full audit trail from backend */
  const fetchAudit = async (requestId) => {
    if (!requestId) return;
    setAuditLoading(true);
    setAuditError(null);
    setAuditData(null);
    try {
      const base = getApiBaseUrl();
      const res = await fetch(`${base}/api/audit/detail/${encodeURIComponent(requestId)}`);
      if (!res.ok) {
        if (res.status === 404) {
          setAuditError('No audit trail found for this request ID on the server.');
        } else {
          setAuditError(`Server error (${res.status})`);
        }
        return;
      }
      const data = await res.json();
      setAuditData(data?.audit ?? null);
    } catch (err) {
      setAuditError(err?.message || 'Failed to fetch audit trail');
    } finally {
      setAuditLoading(false);
    }
  };

  /* Simple UUID-ish check (8-4-4-4-12 hex) */
  const isUUID = (s) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(s);

  const lookup = (id) => {
    const trimmed = String(id ?? query).trim();
    if (!trimmed) {
      setResult(null);
      setNotFound(false);
      setAuditData(null);
      setAuditError(null);
      return;
    }
    const row = getTransactionById(trimmed);
    setResult(row);
    setNotFound(!row);
    setAuditData(null);
    setAuditError(null);

    // Determine the request UUID to fetch audit with
    if (row?.requestId) {
      fetchAudit(row.requestId);
    } else if (isUUID(trimmed)) {
      fetchAudit(trimmed);
    }
    // If it's a TXN ID without requestId, we can't fetch the audit trail
    // (old transactions created before requestId was saved)
  };

  /* Also allow looking up by raw request_id (UUID) directly */
  const lookupDirect = () => {
    const trimmed = query.trim();
    if (!trimmed) return;

    // Try localStorage first
    const row = getTransactionById(trimmed);
    setResult(row);
    setNotFound(!row && !isUUID(trimmed));
    setAuditData(null);
    setAuditError(null);

    // Determine the request UUID to fetch
    if (row?.requestId) {
      fetchAudit(row.requestId);
    } else if (isUUID(trimmed)) {
      // User entered a UUID directly — fetch audit trail
      fetchAudit(trimmed);
    }
    // TXN IDs without stored requestId: no audit to fetch
  };

  const copyId = async (id) => {
    try {
      await navigator.clipboard.writeText(id);
    } catch {
      /* ignore */
    }
  };

  /* Extract key data from audit */
  const compositeStep = auditData?.steps?.find((s) => s.service === 'composite_risk_scoring');
  const legacyRiskStep = auditData?.steps?.find((s) => s.service === 'risk_scoring');
  const compositeOutput = compositeStep?.output;
  const compositeInput = compositeStep?.input;

  return (
    <div className="mx-auto max-w-3xl space-y-8 pt-2">
      {/* ── Page header ─────────────────────────────────────────────── */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">Transaction history</h2>
        <p className="mt-1 text-sm text-slate-600">
          Enter a transaction ID or request UUID to view the full audit trail.
        </p>
      </div>

      {/* ── Lookup card ─────────────────────────────────────────────── */}
      <div className="card card-hover">
        <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500">
          Transaction / Request ID
        </label>
        <div className="mt-2 flex flex-col gap-3 sm:flex-row sm:items-stretch">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && lookupDirect()}
            placeholder="TXN-XXXXX-ABC or UUID"
            className="focus-brand min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-mono text-slate-900"
          />
          <MotionButton
            type="button"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={lookupDirect}
            className="btn-primary shrink-0 px-6"
          >
            <Search className="h-4 w-4" />
            Lookup
          </MotionButton>
        </div>

        {recent.length > 0 && (
          <div className="mt-4 border-t border-slate-100 pt-4">
            <p className="text-xs font-semibold text-slate-500">Recent IDs (this browser)</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {recent.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => {
                    setQuery(t.id);
                    lookup(t.id);
                  }}
                  className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 font-mono text-[11px] font-medium text-slate-800 transition-colors duration-200 hover:border-teal-200 hover:bg-teal-50/70"
                >
                  {t.id}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Not found ───────────────────────────────────────────────── */}
      <AnimatePresence mode="wait">
        {notFound && !auditData && !auditLoading ? (
          <MotionDiv
            key="nf"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="rounded-2xl border border-amber-200 bg-amber-50/80 px-4 py-3 text-sm text-amber-900"
          >
            No transaction found for that ID. Run an analysis first — the ID appears in a banner on the
            analysis page.
          </MotionDiv>
        ) : null}

        {/* ── Loading audit ──────────────────────────────────────────── */}
        {auditLoading ? (
          <MotionDiv
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex items-center justify-center gap-3 py-8"
          >
            <Loader2 className="w-6 h-6 animate-spin text-teal-600" />
            <span className="text-sm font-medium text-slate-600">Loading audit trail…</span>
          </MotionDiv>
        ) : null}

        {/* ── Transaction summary (localStorage) ─────────────────────── */}
        {result ? (
          <MotionDiv
            key={result.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.35 }}
            className="card border-teal-100/80 bg-gradient-to-b from-white to-teal-50/25"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Transaction</p>
                <p className="mt-1 font-mono text-lg font-bold text-slate-900">{result.id}</p>
              </div>
              <button
                type="button"
                onClick={() => copyId(result.id)}
                className="btn-secondary px-3 py-2 text-xs"
              >
                <ClipboardCopy className="h-4 w-4" />
                Copy ID
              </button>
            </div>

            <dl className="mt-6 grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl border border-slate-100 bg-white/80 p-4">
                <dt className="text-xs font-semibold text-slate-500">Saved at</dt>
                <dd className="mt-1 text-sm font-medium text-slate-900">{result.savedAt}</dd>
              </div>
              <div className="rounded-xl border border-slate-100 bg-white/80 p-4">
                <dt className="text-xs font-semibold text-slate-500">Mode</dt>
                <dd className="mt-1 text-sm font-medium text-slate-900">
                  {result.demo ? 'Demo / placeholder run' : 'Live scan'}
                </dd>
              </div>
              {result.fileName ? (
                <div className="rounded-xl border border-slate-100 bg-white/80 p-4 sm:col-span-2">
                  <dt className="text-xs font-semibold text-slate-500">Primary file</dt>
                  <dd className="mt-1 text-sm font-medium text-slate-900 break-all">{result.fileName}</dd>
                </div>
              ) : null}
              <div className="rounded-xl border border-slate-100 bg-white/80 p-4">
                <dt className="text-xs font-semibold text-slate-500">Detections</dt>
                <dd className="mt-1 text-sm font-medium text-slate-900">{result.detectionCount}</dd>
              </div>
              <div className="rounded-xl border border-slate-100 bg-white/80 p-4">
                <dt className="text-xs font-semibold text-slate-500">Manifest items</dt>
                <dd className="mt-1 text-sm font-medium text-slate-900">{result.manifestItemCount ?? 0}</dd>
              </div>
              {result.risk ? (
                <div className="rounded-xl border border-slate-100 bg-white/80 p-4 sm:col-span-2">
                  <dt className="text-xs font-semibold text-slate-500">Risk</dt>
                  <dd className="mt-1 text-sm font-medium text-slate-900">
                    <span className="mr-2 inline-flex rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs">
                      {result.risk.level ?? '—'}
                    </span>
                    {result.risk.score != null ? `Score ${result.risk.score}` : null}
                  </dd>
                  {result.risk.reason ? (
                    <p className="mt-2 text-xs leading-relaxed text-slate-600">{result.risk.reason}</p>
                  ) : null}
                </div>
              ) : null}
            </dl>

            {Array.isArray(result.labels) && result.labels.length > 0 ? (
              <div className="mt-4">
                <p className="text-xs font-semibold text-slate-500">Top labels</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {result.labels.map((lab, i) => (
                    <span key={`${lab}-${i}`} className="badge badge-slate">
                      {lab}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}
          </MotionDiv>
        ) : null}

        {/* ── Audit error ────────────────────────────────────────────── */}
        {auditError && !auditLoading ? (
          <MotionDiv
            key="audit-err"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="rounded-2xl border border-slate-200 bg-slate-50/80 px-4 py-3 text-sm text-slate-600"
          >
            {auditError}
          </MotionDiv>
        ) : null}

        {/* ════════════════════════════════════════════════════════════ */}
        {/*  AUDIT TRAIL (from server)                                  */}
        {/* ════════════════════════════════════════════════════════════ */}
        {auditData ? (
          <MotionDiv
            key="audit"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="space-y-6"
          >
            {/* ── Audit header ──────────────────────────────────────── */}
            <div className="card border-violet-100/80 bg-gradient-to-b from-white to-violet-50/20">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-wide text-violet-500">Server Audit Trail</p>
                  <p className="mt-1 font-mono text-sm font-bold text-slate-900">{auditData.request_id}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {auditData.timestamp ? new Date(auditData.timestamp).toLocaleString() : '—'}
                  </p>
                </div>
                <StatusBadge status={auditData.final_status} />
              </div>
            </div>

            {/* ── Risk Summary ──────────────────────────────────────── */}
            {(compositeOutput || legacyRiskStep) && (
              <div className="card border-slate-200/80">
                <h3 className="text-sm font-bold text-slate-900 mb-4">Risk Summary</h3>

                {compositeOutput && (
                  <div className="space-y-5">
                    {/* Decision + final risk */}
                    <div className="flex flex-wrap items-center gap-4">
                      <DecisionBadge decision={compositeOutput.decision} />
                      <div className="text-center">
                        <p className="text-3xl font-extrabold text-slate-900">
                          {Math.round(compositeOutput.final_risk * 100)}%
                        </p>
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Final Risk</p>
                      </div>
                    </div>

                    {/* Risk bars */}
                    <div className="grid gap-4 sm:grid-cols-2">
                      <RiskBar label="Visual Risk" value={compositeOutput.visual_risk} />
                      <RiskBar label="Data Risk" value={compositeInput?.data_risk} />
                    </div>

                    {/* Input signals */}
                    {compositeInput && (
                      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                        {[
                          { label: 'Suspicious', value: compositeInput.suspicious_score },
                          { label: 'Uncertainty', value: compositeInput.uncertain_ratio },
                          { label: 'SSIM Risk', value: compositeInput.ssim_risk },
                          { label: 'SHAP', value: compositeInput.shap_intensity_score },
                        ].map((s) => (
                          <div key={s.label} className="rounded-lg border border-slate-100 bg-white/80 p-2.5 text-center">
                            <p className="text-[10px] font-semibold text-slate-400 uppercase">{s.label}</p>
                            <p className="text-sm font-bold text-slate-900 mt-0.5">
                              {s.value != null ? (typeof s.value === 'number' ? s.value.toFixed(2) : s.value) : '—'}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Legacy risk */}
                {legacyRiskStep?.output && (
                  <div className={`${compositeOutput ? 'mt-5 pt-4 border-t border-slate-100' : ''}`}>
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-semibold text-slate-500">Legacy classification:</span>
                      <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-bold ${
                        legacyRiskStep.output.level === 'PROHIBITED' ? 'bg-red-100 text-red-800 border border-red-200'
                        : legacyRiskStep.output.level === 'SUSPICIOUS' ? 'bg-amber-100 text-amber-800 border border-amber-200'
                        : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                      }`}>
                        {legacyRiskStep.output.level}
                      </span>
                      {legacyRiskStep.output.score != null && (
                        <span className="text-xs text-slate-500">Score: {legacyRiskStep.output.score}</span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ── Pipeline Steps ────────────────────────────────────── */}
            {auditData.steps?.length > 0 && (
              <div>
                <h3 className="text-sm font-bold text-slate-900 mb-3">
                  Pipeline Steps
                  <span className="ml-2 text-xs font-medium text-slate-400">
                    ({auditData.steps.length} stages)
                  </span>
                </h3>
                <div className="space-y-2">
                  {auditData.steps.map((step, idx) => (
                    <StepCard key={`${step.service}-${idx}`} step={step} index={idx} />
                  ))}
                </div>
              </div>
            )}
          </MotionDiv>
        ) : null}
      </AnimatePresence>
    </div>
  );
};

export default HistoryPage;
