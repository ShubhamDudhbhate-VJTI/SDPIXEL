import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ClipboardCopy, Search } from 'lucide-react';
import { getTransactionById, listRecentTransactions } from '../utils/transactions';

const MotionButton = motion.button;
const MotionDiv = motion.div;

const HistoryPage = () => {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);
  const [notFound, setNotFound] = useState(false);

  const recent = listRecentTransactions(8);

  const lookup = (id) => {
    const trimmed = String(id ?? query).trim();
    if (!trimmed) {
      setResult(null);
      setNotFound(false);
      return;
    }
    const row = getTransactionById(trimmed);
    setResult(row);
    setNotFound(!row);
  };

  const copyId = async (id) => {
    try {
      await navigator.clipboard.writeText(id);
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-8 pt-2">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">Transaction history</h2>
        <p className="mt-1 text-sm text-slate-600">
          Enter the transaction ID shown after an analysis completes to view stored summary details.
        </p>
      </div>

      <div className="card card-hover">
        <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500">
          Transaction ID
        </label>
        <div className="mt-2 flex flex-col gap-3 sm:flex-row sm:items-stretch">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && lookup()}
            placeholder="e.g. TXN-MXXXXX-ABC123"
            className="focus-brand min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-mono text-slate-900"
          />
          <MotionButton
            type="button"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => lookup()}
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

      <AnimatePresence mode="wait">
        {notFound ? (
          <MotionDiv
            key="nf"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="rounded-2xl border border-amber-200 bg-amber-50/80 px-4 py-3 text-sm text-amber-900"
          >
            No transaction found for that ID. Run an analysis first—the ID appears in a banner on the
            analysis page.
          </MotionDiv>
        ) : null}

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
      </AnimatePresence>
    </div>
  );
};

export default HistoryPage;
