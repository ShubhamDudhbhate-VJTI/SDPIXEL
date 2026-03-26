import { useMemo, useState } from 'react';
import { Image as ImageIcon, FileText } from 'lucide-react';
import { resolveAssetList, resolveAssetUrl } from '../api/assets';

function getZeroShotImageValues(outputs) {
  const single =
    outputs?.zeroShotOutputImage ??
    outputs?.zero_shot_output_image ??
    outputs?.zeroShotOutput ??
    outputs?.zero_shot_output ??
    null;

  const list =
    outputs?.zeroShotOutputImages ??
    outputs?.zero_shot_output_images ??
    null;

  if (Array.isArray(list) && list.length > 0) return list;
  if (typeof single === 'string' && single.trim().length > 0) return [single];
  return [];
}

function getZeroShotText(outputs) {
  return (
    outputs?.zeroShotOutputText ??
    outputs?.zero_shot_output_text ??
    outputs?.zeroShotText ??
    outputs?.zero_shot_text ??
    null
  );
}

export default function ZeroShotOutput({ outputs }) {
  const gallery = useMemo(() => {
    const values = getZeroShotImageValues(outputs);
    return resolveAssetList(values);
  }, [outputs]);

  const zeroShotText = useMemo(() => getZeroShotText(outputs), [outputs]);

  const [selectedIndex, setSelectedIndex] = useState(0);
  const selected = gallery[selectedIndex] ?? gallery[0] ?? null;

  const hasImage = gallery.length > 0;
  const hasText = typeof zeroShotText === 'string' && zeroShotText.trim().length > 0;

  return (
    <div className="card card-hover">
      <div className="flex items-baseline justify-between gap-3 mb-4">
        <h3 className="section-title">Zero shot Output</h3>
        <span className="section-subtitle">From backend `outputs`</span>
      </div>

      {hasImage ? (
        <>
          <div className="overflow-hidden rounded-xl bg-slate-100 border border-slate-200/70">
            <img src={selected} alt="Zero-shot output" className="w-full h-auto" />
          </div>

          {gallery.length > 1 && (
            <div className="mt-4 flex gap-2 overflow-x-auto pb-1">
              {gallery.map((src, idx) => (
                <button
                  key={`${src}-${idx}`}
                  type="button"
                  onClick={() => setSelectedIndex(idx)}
                  className={`shrink-0 overflow-hidden rounded-xl border transition ${
                    idx === selectedIndex
                      ? 'border-blue-300 ring-4 ring-blue-100'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                  title={`Zero-shot output ${idx + 1}`}
                >
                  <img src={src} alt={`Zero-shot output ${idx + 1}`} className="h-16 w-24 object-cover bg-slate-100" />
                </button>
              ))}
            </div>
          )}
        </>
      ) : hasText ? (
        <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-4">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="w-5 h-5 text-slate-700" />
            <span className="text-sm font-semibold text-slate-900">Zero-shot result</span>
          </div>
          <pre className="whitespace-pre-wrap text-sm text-slate-800 font-mono">
            {zeroShotText}
          </pre>
        </div>
      ) : (
        <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-6 text-center">
          <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-900/5 border border-slate-200">
            <ImageIcon className="w-5 h-5 text-slate-600" />
          </div>
          <div className="text-sm font-semibold text-slate-900">No zero-shot output yet</div>
          <div className="text-xs text-slate-500 mt-1">
            Backend should return `outputs.zeroShotOutputImage(s)` or `outputs.zeroShotOutputText`.
          </div>
        </div>
      )}
    </div>
  );
}

