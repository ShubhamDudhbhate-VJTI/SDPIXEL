import { useMemo } from 'react';
import { Package } from 'lucide-react';

function normalizeManifestItemsFromOutputs(outputs) {
  const raw = outputs?.manifestItems ?? outputs?.manifest_items;
  if (!Array.isArray(raw) || raw.length === 0) return null;
  return raw.map((x) => String(x).trim()).filter(Boolean);
}

export default function ResultsOutputs({ outputs, manifestItems }) {
  const items = useMemo(() => {
    const fromOutputs = normalizeManifestItemsFromOutputs(outputs);
    if (fromOutputs?.length) return fromOutputs;
    return Array.isArray(manifestItems) ? manifestItems : [];
  }, [outputs, manifestItems]);

  return (
    <div className="card card-hover">
      <div className="flex items-baseline justify-between gap-3 mb-4">
        <h3 className="section-title">Objects in cargo</h3>
        <span className="section-subtitle">From manifest PDF</span>
      </div>

      {items.length > 0 ? (
        <ul className="max-h-64 overflow-y-auto rounded-xl border border-slate-200 bg-slate-50/60 divide-y divide-slate-100">
          {items.map((item, idx) => (
            <li
              key={`${item}-${idx}`}
              className="px-4 py-2.5 text-sm text-slate-800"
            >
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-6 text-center">
          <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-900/5 border border-slate-200">
            <Package className="w-5 h-5 text-slate-600" />
          </div>
          <div className="text-sm font-semibold text-slate-900">No manifest items yet</div>
          <div className="text-xs text-slate-500 mt-1">
            Upload a manifest PDF in the sidebar (POST /api/manifest/extract).
          </div>
        </div>
      )}
    </div>
  );
}
