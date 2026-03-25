import { useMemo, useState } from 'react';
import { Image as ImageIcon } from 'lucide-react';
import { resolveAssetList, resolveAssetUrl } from '../api/assets';

function normalizeOutputs(outputs) {
  const modelOutputs = outputs?.modelOutputImages ?? outputs?.model_outputs ?? outputs?.outputs ?? [];
  const objectsImage = outputs?.objectsImage ?? outputs?.objects_image ?? outputs?.objects ?? null;

  const list = Array.isArray(modelOutputs) ? modelOutputs.filter(Boolean) : [];
  return { modelOutputImages: list, objectsImage };
}

export default function ResultsOutputs({ outputs, fallbackGallery, fallbackObjects }) {
  const normalized = useMemo(() => normalizeOutputs(outputs), [outputs]);
  const gallery = useMemo(() => {
    const raw = normalized.modelOutputImages.length
      ? normalized.modelOutputImages
      : (fallbackGallery ?? []);
    return resolveAssetList(raw);
  }, [normalized.modelOutputImages, fallbackGallery]);
  const objectsImage = useMemo(
    () => resolveAssetUrl(normalized.objectsImage || fallbackObjects || null),
    [normalized.objectsImage, fallbackObjects],
  );

  const [selectedIndex, setSelectedIndex] = useState(0);
  const selected = gallery[selectedIndex] || gallery[0] || null;

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <div className="card card-hover">
        <div className="flex items-baseline justify-between gap-3 mb-4">
          <h3 className="section-title">Model output</h3>
          <span className="section-subtitle">
            {gallery.length ? `${gallery.length} image(s)` : 'No images'}
          </span>
        </div>

        {selected ? (
          <>
            <div className="overflow-hidden rounded-xl bg-slate-100 border border-slate-200/70">
              <img
                src={selected}
                alt="Model output"
                className="w-full h-auto"
              />
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
                    title={`Output ${idx + 1}`}
                  >
                    <img
                      src={src}
                      alt={`Output ${idx + 1}`}
                      className="h-16 w-24 object-cover bg-slate-100"
                    />
                  </button>
                ))}
              </div>
            )}
          </>
        ) : (
          <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-6 text-center">
            <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-900/5 border border-slate-200">
              <ImageIcon className="w-5 h-5 text-slate-600" />
            </div>
            <div className="text-sm font-semibold text-slate-900">No model output images yet</div>
            <div className="text-xs text-slate-500 mt-1">
              Backend should return URLs in <code className="font-mono">outputs.modelOutputImages</code>.
            </div>
          </div>
        )}
      </div>

      <div className="card card-hover">
        <div className="flex items-baseline justify-between gap-3 mb-4">
          <h3 className="section-title">Objects in cargo</h3>
          <span className="section-subtitle">Secondary model</span>
        </div>

        {objectsImage ? (
          <div className="overflow-hidden rounded-xl bg-slate-100 border border-slate-200/70">
            <img
              src={objectsImage}
              alt="Objects in cargo"
              className="w-full h-auto"
            />
          </div>
        ) : (
          <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-6 text-center">
            <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-900/5 border border-slate-200">
              <ImageIcon className="w-5 h-5 text-slate-600" />
            </div>
            <div className="text-sm font-semibold text-slate-900">No objects image yet</div>
            <div className="text-xs text-slate-500 mt-1">
              Backend should return a URL in <code className="font-mono">outputs.objectsImage</code>.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

