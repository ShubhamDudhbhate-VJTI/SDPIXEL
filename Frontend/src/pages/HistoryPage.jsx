import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ClipboardCopy, Search, ChevronDown, Clock, CheckCircle2,
  XCircle, SkipForward, Loader2, ShieldCheck, AlertTriangle,
  Zap, Eye, FileText, Brain, Scan, BarChart3, Layers, Package,
  Calendar, RefreshCw, Hash,
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

/* ── Pipeline ordering — always show all 10 stages ───────────────────── */

const PIPELINE_ORDER = [
  'manifest_extraction',
  'vlm_extraction',
  'yolov8_detection',
  'risk_scoring',
  'gradcam_generation',
  'ssim_comparison',
  'shap_explainer',
  'zero_shot_inspection',
  'data_risk_analysis',
  'composite_risk_scoring',
];

const buildFullPipeline = (actualSteps = []) => {
  const stepMap = {};
  actualSteps.forEach((s) => { stepMap[s.service] = s; });
  if (stepMap['shap_service'] && !stepMap['shap_explainer']) {
    stepMap['shap_explainer'] = { ...stepMap['shap_service'], service: 'shap_explainer' };
  }
  return PIPELINE_ORDER.map((service) => {
    if (stepMap[service]) return stepMap[service];
    return { service, status: 'skipped', _placeholder: true };
  });
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

/* ── Data renderer ────────────────────────────────────────────────────── */

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
            {(step.service === 'shap_explainer' || step.service === 'shap_service') && step.status === 'success' && step.output?.strength && (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 border border-amber-200 px-2 py-0.5 text-[10px] font-bold text-amber-700">
                <AlertTriangle className="w-3 h-3" /> {step.output.strength} · {step.output.reliability || 'N/A'}
              </span>
            )}
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
  const [dateFilter, setDateFilter] = useState('');

  // localStorage transaction lookup
  const [txnResult, setTxnResult] = useState(null);
  const [notFound, setNotFound] = useState(false);

  // Recent audits from API
  const [recentAudits, setRecentAudits] = useState([]);
  const [recentLoading, setRecentLoading] = useState(false);
  const [recentError, setRecentError] = useState(null);

  // Selected audit detail from server
  const [auditData, setAuditData] = useState(null);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditError, setAuditError] = useState(null);
  const [selectedRequestId, setSelectedRequestId] = useState(null);

  const base = getApiBaseUrl();

  // Recent transactions from localStorage (always available)
  const recentTxns = listRecentTransactions(8);

  /* Simple UUID check */
  const isUUID = (s) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(s);

  /* ── Fetch recent audits list from API ──────────────────────── */
  const fetchRecentAudits = useCallback(async (dateStr) => {
    setRecentLoading(true);
    setRecentError(null);
    try {
      let url = `${base}/api/audit/logs?limit=10`;
      if (dateStr) url += `&date_filter=${encodeURIComponent(dateStr)}`;

      let res = await fetch(url);
      if (!res.ok) {
        res = await fetch(`${base}/api/audit/local?limit=10`);
      }
      if (!res.ok) throw new Error(`Server error (${res.status})`);

      const data = await res.json();
      setRecentAudits(data?.logs ?? []);
    } catch (err) {
      setRecentError(err?.message || 'Failed to load audit list');
      setRecentAudits([]);
    } finally {
      setRecentLoading(false);
    }
  }, [base]);

  /* ── Fetch full audit detail by request_id ──────────────────── */
  const fetchAuditDetail = useCallback(async (requestId) => {
    if (!requestId) return;
    setAuditLoading(true);
    setAuditError(null);
    setAuditData(null);
    setSelectedRequestId(requestId);
    try {
      const res = await fetch(`${base}/api/audit/detail/${encodeURIComponent(requestId)}`);
      if (!res.ok) {
        setAuditError(res.status === 404
          ? 'No audit trail found for this request ID.'
          : `Server error (${res.status})`);
        return;
      }
      const data = await res.json();
      setAuditData(data?.audit ?? null);
    } catch (err) {
      setAuditError(err?.message || 'Failed to fetch audit trail');
    } finally {
      setAuditLoading(false);
    }
  }, [base]);

  /* ── Load recent audits on mount ────────────────────────────── */
  useEffect(() => { fetchRecentAudits(); }, [fetchRecentAudits]);

  /* ── Unified lookup: TXN-ID or UUID ────────────────────────── */
  const handleSearch = (id) => {
    const trimmed = String(id ?? query).trim();
    if (!trimmed) {
      setTxnResult(null);
      setNotFound(false);
      setAuditData(null);
      setAuditError(null);
      return;
    }

    // 1. Try localStorage transaction lookup
    const row = getTransactionById(trimmed);
    setTxnResult(row);
    setNotFound(!row && !isUUID(trimmed));
    setAuditData(null);
    setAuditError(null);

    // 2. Fetch audit trail from server
    if (row?.requestId) {
      fetchAuditDetail(row.requestId);
    } else if (isUUID(trimmed)) {
      fetchAuditDetail(trimmed);
    }
  };

  /* ── Date filter handler ─────────────────────────────────────── */
  const handleDateFilter = () => {
    if (!dateFilter) { fetchRecentAudits(); return; }
    const parts = dateFilter.split('-');
    if (parts.length === 3) {
      fetchRecentAudits(`${parts[2]}-${parts[1]}-${parts[0]}`);
    }
  };

  const copyId = async (id) => {
    try { await navigator.clipboard.writeText(id); } catch { /* */ }
  };

  const formatDate = (ts) => {
    if (!ts) return '—';
    try { return new Date(ts).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }); }
    catch { return ts; }
  };

  /* Extract risk data from audit detail */
  const compositeStep = auditData?.steps?.find((s) => s.service === 'composite_risk_scoring');
  const legacyRiskStep = auditData?.steps?.find((s) => s.service === 'risk_scoring');
  const ssimStep = auditData?.steps?.find((s) => s.service === 'ssim_comparison');
  const shapStep = auditData?.steps?.find((s) => s.service === 'shap_explainer' || s.service === 'shap_service');
  const dataRiskStep = auditData?.steps?.find((s) => s.service === 'data_risk_analysis');
  const compositeOutput = compositeStep?.output;
  const compositeInput = compositeStep?.input;

  /* Derive composite-like display data when composite_risk_scoring is missing */
  const displayRisk = compositeOutput || (() => {
    if (!legacyRiskStep?.output) return null;
    const lro = legacyRiskStep.output;
    const score = lro.score ?? 0;
    return {
      decision: lro.level === 'PROHIBITED' ? 'RED' : lro.level === 'SUSPICIOUS' ? 'YELLOW' : 'GREEN',
      final_risk: score / 100,
      visual_risk: score / 100,
    };
  })();

  const displayRiskInput = compositeInput || (() => {
    if (!legacyRiskStep?.output) return null;
    const lro = legacyRiskStep.output;
    return {
      suspicious_score: (lro.level === 'PROHIBITED' || lro.level === 'SUSPICIOUS') ? 1.0 : 0.0,
      uncertain_ratio: null,
      ssim_risk: ssimStep?.output?.ssim_score != null ? Math.round((1 - ssimStep.output.ssim_score) * 100) / 100 : null,
      shap_intensity_score: shapStep?.output?.shap_intensity_score ?? (shapStep?.output?.coverage != null ? shapStep.output.coverage / 100 : null),
      data_risk: dataRiskStep?.output?.data_risk ?? null,
    };
  })();

  /* ── Build a unified "display" object for the Transaction card ──
       If localStorage has a txnResult, use it. Otherwise, derive
       the same fields from the audit JSON steps so the card always
       shows the same format regardless of how the audit was opened. */
  const derivedSummary = (() => {
    if (txnResult) return txnResult; // localStorage data takes priority
    if (!auditData) return null;

    const yoloStep = auditData.steps?.find((s) => s.service === 'yolov8_detection');
    const manifestStep = auditData.steps?.find((s) => s.service === 'manifest_extraction');
    const riskStep = legacyRiskStep;
    const compStep = compositeStep;

    const riskObj = {};
    if (riskStep?.output) {
      riskObj.level = riskStep.output.level;
      riskObj.score = riskStep.output.score;
    }
    if (compStep?.output) {
      riskObj.decision = compStep.output.decision;
      riskObj.final_risk = compStep.output.final_risk;
    }
    if (riskStep?.output?.reason) {
      riskObj.reason = riskStep.output.reason;
    }

    return {
      id: auditData.request_id,
      requestId: auditData.request_id,
      savedAt: auditData.timestamp,
      demo: false,
      fileName: yoloStep?.input?.filename ?? null,
      detectionCount: yoloStep?.output?.detection_count ?? null,
      manifestItemCount: manifestStep?.output?.item_count ?? null,
      risk: Object.keys(riskObj).length > 0 ? riskObj : null,
      labels: yoloStep?.output?.labels ?? [],
      _fromAudit: true, // flag so we know this is derived
    };
  })();

  return (
    <div className="mx-auto max-w-3xl space-y-8 pt-2">
      {/* ── Page header ─────────────────────────────────────────────── */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">Transaction History</h2>
        <p className="mt-1 text-sm text-slate-600">
          Enter a transaction ID or request UUID to view full details and audit trail.
        </p>
      </div>

      {/* ── Search Card ──────────────────────────────────────────────── */}
      <div className="card card-hover">
        <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500">
          Transaction / Request ID
        </label>
        <div className="mt-2 flex flex-col gap-3 sm:flex-row sm:items-stretch">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="TXN-XXXXX-ABC or UUID"
            className="focus-brand min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-mono text-slate-900"
          />
          <MotionButton
            type="button"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => handleSearch()}
            className="btn-primary shrink-0 px-6"
          >
            <Search className="h-4 w-4" />
            Lookup
          </MotionButton>
        </div>

        {/* Recent TXN-IDs from localStorage */}
        {recentTxns.length > 0 && (
          <div className="mt-4 border-t border-slate-100 pt-4">
            <p className="text-xs font-semibold text-slate-500">Recent IDs (this browser)</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {recentTxns.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => { setQuery(t.id); handleSearch(t.id); }}
                  className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 font-mono text-[11px] font-medium text-slate-800 transition-colors duration-200 hover:border-teal-200 hover:bg-teal-50/70"
                >
                  {t.id}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Date filter */}
        <div className="mt-4 border-t border-slate-100 pt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label className="block text-xs font-semibold text-slate-500 mb-1">
              <Calendar className="w-3 h-3 inline mr-1" />
              Filter audits by date
            </label>
            <input
              type="date"
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900"
            />
          </div>
          <MotionButton
            type="button"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleDateFilter}
            className="btn-secondary px-4 py-2 shrink-0"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            {dateFilter ? 'Apply Filter' : 'Show All'}
          </MotionButton>
        </div>
      </div>

      {/* ── Recent Audits from API ────────────────────────────────────── */}
      <div className="card card-hover">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Hash className="w-4 h-4 text-slate-400" />
            Recent Audits
            {recentAudits.length > 0 && (
              <span className="text-xs font-medium text-slate-400">({recentAudits.length})</span>
            )}
          </h3>
          <button type="button" onClick={() => fetchRecentAudits()}
            className="text-xs text-slate-400 hover:text-slate-600 transition-colors flex items-center gap-1">
            <RefreshCw className="w-3 h-3" /> Refresh
          </button>
        </div>

        {recentLoading ? (
          <div className="flex items-center justify-center gap-3 py-6">
            <Loader2 className="w-5 h-5 animate-spin text-teal-600" />
            <span className="text-sm text-slate-500">Loading audits…</span>
          </div>
        ) : recentError ? (
          <div className="rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-700">
            {recentError}
          </div>
        ) : recentAudits.length === 0 ? (
          <div className="text-center py-6 text-sm text-slate-400">
            No audit records found. Run an analysis first.
          </div>
        ) : (
          <div className="space-y-2">
            {recentAudits.map((audit, idx) => {
              const reqId = audit.request_id || audit.id || '—';
              const isSelected = selectedRequestId === reqId;
              const ts = audit.created_at || audit.timestamp;
              const status = audit.status || audit.final_status || '—';
              const stepCount = audit.step_count;
              const desc = audit.description;

              return (
                <MotionDiv key={reqId + '-' + idx}
                  initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.04 }}>
                  <div role="button" tabIndex={0}
                    onClick={() => { setQuery(reqId); handleSearch(reqId); }}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { setQuery(reqId); handleSearch(reqId); } }}
                    className={`w-full text-left rounded-xl border px-4 py-3 transition-all duration-200 cursor-pointer ${
                      isSelected
                        ? 'border-teal-300 bg-teal-50/60 shadow-sm'
                        : 'border-slate-200/80 bg-white hover:border-teal-200 hover:bg-teal-50/30'
                    }`}>
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <p className="font-mono text-xs font-bold text-slate-900 truncate">{reqId}</p>
                        <div className="flex items-center gap-3 mt-1 flex-wrap">
                          <span className="text-[11px] text-slate-400 flex items-center gap-1">
                            <Clock className="w-3 h-3" />{formatDate(ts)}
                          </span>
                          {stepCount != null && (
                            <span className="text-[11px] text-slate-400">{stepCount} steps</span>
                          )}
                        </div>
                        {desc && <p className="text-[11px] text-slate-500 mt-0.5 truncate max-w-md">{desc}</p>}
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <StatusBadge status={status} />
                        <button type="button" onClick={(e) => { e.stopPropagation(); copyId(reqId); }}
                          className="text-slate-300 hover:text-slate-500 transition-colors" title="Copy">
                          <ClipboardCopy className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>
                </MotionDiv>
              );
            })}
          </div>
        )}
      </div>

      {/* ═══════════════════════════════════════════════════════════════ */}
      {/*  RESULTS SECTION                                              */}
      {/* ═══════════════════════════════════════════════════════════════ */}
      <AnimatePresence mode="wait">
        {/* Not found message */}
        {notFound && !auditData && !auditLoading ? (
          <MotionDiv key="nf" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="rounded-2xl border border-amber-200 bg-amber-50/80 px-4 py-3 text-sm text-amber-900">
            No transaction found for that ID. Run an analysis first — the ID appears in a banner on the analysis page.
          </MotionDiv>
        ) : null}

        {/* Loading */}
        {auditLoading ? (
          <MotionDiv key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="flex items-center justify-center gap-3 py-8">
            <Loader2 className="w-6 h-6 animate-spin text-teal-600" />
            <span className="text-sm font-medium text-slate-600">Loading audit trail…</span>
          </MotionDiv>
        ) : null}

        {/* ── Transaction summary (localStorage OR derived from audit) ── */}
        {derivedSummary ? (
          <MotionDiv key={derivedSummary.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }} transition={{ duration: 0.35 }}
            className="card border-teal-100/80 bg-gradient-to-b from-white to-teal-50/25">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Transaction</p>
                <p className="mt-1 font-mono text-lg font-bold text-slate-900">{derivedSummary.id}</p>
                {derivedSummary.requestId && derivedSummary.requestId !== derivedSummary.id && (
                  <div className="mt-1.5 flex items-center gap-2">
                    <span className="text-[10px] font-semibold uppercase tracking-wide text-violet-500">Audit Request ID</span>
                    <code className="rounded-md bg-violet-50 border border-violet-100 px-2 py-0.5 font-mono text-[11px] text-violet-700">{derivedSummary.requestId}</code>
                    <button type="button" onClick={() => copyId(derivedSummary.requestId)}
                      className="text-violet-400 hover:text-violet-600 transition-colors" title="Copy request ID">
                      <ClipboardCopy className="h-3 w-3" />
                    </button>
                  </div>
                )}
              </div>
              <button type="button" onClick={() => copyId(derivedSummary.id)}
                className="btn-secondary px-3 py-2 text-xs">
                <ClipboardCopy className="h-4 w-4" /> Copy ID
              </button>
            </div>

            <dl className="mt-6 grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl border border-slate-100 bg-white/80 p-4">
                <dt className="text-xs font-semibold text-slate-500">Saved at</dt>
                <dd className="mt-1 text-sm font-medium text-slate-900">{derivedSummary.savedAt ? formatDate(derivedSummary.savedAt) : '—'}</dd>
              </div>
              <div className="rounded-xl border border-slate-100 bg-white/80 p-4">
                <dt className="text-xs font-semibold text-slate-500">Mode</dt>
                <dd className="mt-1 text-sm font-medium text-slate-900">
                  {derivedSummary.demo ? 'Demo / placeholder run' : 'Live scan'}
                </dd>
              </div>
              {derivedSummary.fileName ? (
                <div className="rounded-xl border border-slate-100 bg-white/80 p-4 sm:col-span-2">
                  <dt className="text-xs font-semibold text-slate-500">Primary file</dt>
                  <dd className="mt-1 text-sm font-medium text-slate-900 break-all">{derivedSummary.fileName}</dd>
                </div>
              ) : null}
              <div className="rounded-xl border border-slate-100 bg-white/80 p-4">
                <dt className="text-xs font-semibold text-slate-500">Detections</dt>
                <dd className="mt-1 text-sm font-medium text-slate-900">{derivedSummary.detectionCount ?? '—'}</dd>
              </div>
              <div className="rounded-xl border border-slate-100 bg-white/80 p-4">
                <dt className="text-xs font-semibold text-slate-500">Manifest items</dt>
                <dd className="mt-1 text-sm font-medium text-slate-900">{derivedSummary.manifestItemCount ?? 0}</dd>
              </div>
              {derivedSummary.risk ? (
                <div className="rounded-xl border border-slate-100 bg-white/80 p-4 sm:col-span-2">
                  <dt className="text-xs font-semibold text-slate-500">Risk</dt>
                  <dd className="mt-1 text-sm font-medium text-slate-900">
                    <span className="mr-2 inline-flex rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs">
                      {derivedSummary.risk.level ?? derivedSummary.risk.decision ?? '—'}
                    </span>
                    {derivedSummary.risk.score != null ? `Score ${derivedSummary.risk.score}` : null}
                    {derivedSummary.risk.final_risk != null ? ` · Final ${Math.round(derivedSummary.risk.final_risk * 100)}%` : null}
                    {derivedSummary.risk.decision ? ` · ${derivedSummary.risk.decision}` : null}
                  </dd>
                  {derivedSummary.risk.reason ? (
                    <p className="mt-2 text-xs leading-relaxed text-slate-600">{derivedSummary.risk.reason}</p>
                  ) : null}
                </div>
              ) : null}
            </dl>

            {Array.isArray(derivedSummary.labels) && derivedSummary.labels.length > 0 ? (
              <div className="mt-4">
                <p className="text-xs font-semibold text-slate-500">Top labels</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {derivedSummary.labels.map((lab, i) => (
                    <span key={`${lab}-${i}`} className="badge badge-slate">{lab}</span>
                  ))}
                </div>
              </div>
            ) : null}
          </MotionDiv>
        ) : null}

        {/* ── Audit error ────────────────────────────────────────────── */}
        {auditError && !auditLoading ? (
          <MotionDiv key="audit-err" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="rounded-2xl border border-slate-200 bg-slate-50/80 px-4 py-3 text-sm text-slate-600">
            {auditError}
          </MotionDiv>
        ) : null}

        {/* ════════════════════════════════════════════════════════════ */}
        {/*  FULL AUDIT TRAIL (from server)                             */}
        {/* ════════════════════════════════════════════════════════════ */}
        {auditData ? (
          <MotionDiv key="audit" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }} className="space-y-6">

            {/* ── Audit header ──────────────────────────────────────── */}
            <div className="card border-violet-100/80 bg-gradient-to-b from-white to-violet-50/20">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-wide text-violet-500">Server Audit Trail</p>
                  <div className="mt-1 flex items-center gap-2">
                    <p className="font-mono text-sm font-bold text-slate-900">{auditData.request_id}</p>
                    <button type="button" onClick={() => copyId(auditData.request_id)}
                      className="text-violet-400 hover:text-violet-600 transition-colors" title="Copy">
                      <ClipboardCopy className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    {auditData.timestamp ? formatDate(auditData.timestamp) : '—'}
                  </p>
                </div>
                <StatusBadge status={auditData.final_status} />
              </div>
            </div>

            {/* ── Risk Summary ──────────────────────────────────────── */}
            {(displayRisk || legacyRiskStep) && (
              <div className="card border-slate-200/80">
                <h3 className="text-sm font-bold text-slate-900 mb-4">Risk Summary</h3>

                {displayRisk && (
                  <div className="space-y-5">
                    <div className="flex flex-wrap items-center gap-4">
                      <DecisionBadge decision={displayRisk.decision} />
                      <div className="text-center">
                        <p className="text-3xl font-extrabold text-slate-900">
                          {displayRisk.final_risk != null ? `${Math.round(displayRisk.final_risk * 100)}%` : '—'}
                        </p>
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Final Risk</p>
                      </div>
                    </div>

                    <div className="grid gap-4 sm:grid-cols-2">
                      <RiskBar label="Visual Risk" value={displayRisk.visual_risk} />
                      <RiskBar label="Data Risk" value={displayRiskInput?.data_risk} />
                    </div>

                    {displayRiskInput && (
                      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                        {[
                          { label: 'Suspicious', value: displayRiskInput.suspicious_score },
                          { label: 'Uncertainty', value: displayRiskInput.uncertain_ratio },
                          { label: 'SSIM Risk', value: displayRiskInput.ssim_risk },
                          { label: 'SHAP', value: displayRiskInput.shap_intensity_score },
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

                {legacyRiskStep?.output && (
                  <div className={`${displayRisk ? 'mt-5 pt-4 border-t border-slate-100' : ''}`}>
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
            {(() => {
              const fullPipeline = buildFullPipeline(auditData.steps);
              return fullPipeline.length > 0 ? (
                <div>
                  <h3 className="text-sm font-bold text-slate-900 mb-3">
                    Pipeline Steps
                    <span className="ml-2 text-xs font-medium text-slate-400">
                      ({fullPipeline.length} stages)
                    </span>
                  </h3>
                  <div className="space-y-2">
                    {fullPipeline.map((step, idx) => (
                      <StepCard key={`${step.service}-${idx}`} step={step} index={idx} />
                    ))}
                  </div>
                </div>
              ) : null;
            })()}
          </MotionDiv>
        ) : null}
      </AnimatePresence>
    </div>
  );
};

export default HistoryPage;
