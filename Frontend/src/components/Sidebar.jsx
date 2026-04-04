import { useMemo, useState } from 'react';
import { FileText, Loader2, Upload, X } from 'lucide-react';
import { extractManifestFromPdf } from '../api/manifest';

const Sidebar = ({
  manifestItems,
  onManifestItemsChange,
  onManifestFileChange,
  referenceImages,
  onReferenceUpload,
  onRemoveReference,
}) => {
  const [manifestPdf, setManifestPdf] = useState(null);
  const [pdfStatus, setPdfStatus] = useState({ state: 'idle', message: '' });
  const [extractedItems, setExtractedItems] = useState([]);

  const extractedCount = extractedItems.length;

  const handlePdfUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.type !== 'application/pdf') {
      setPdfStatus({ state: 'error', message: 'Please upload a PDF file.' });
      return;
    }
    if (file.size > 15 * 1024 * 1024) {
      setPdfStatus({ state: 'error', message: 'PDF must be under 15MB.' });
      return;
    }

    setManifestPdf(file);
    setPdfStatus({ state: 'loading', message: 'Extracting items from PDF…' });

    try {
      const { items } = await extractManifestFromPdf(file);
      setExtractedItems(items);
      onManifestItemsChange(items);
      onManifestFileChange(file);
      setPdfStatus({
        state: 'ready',
        message: items.length ? `Extracted ${items.length} item(s).` : 'No items found in PDF.',
      });
    } catch (err) {
      setExtractedItems([]);
      onManifestItemsChange([]);
      onManifestFileChange(null);
      setPdfStatus({
        state: 'error',
        message: err?.message ? String(err.message) : 'Manifest extract failed.',
      });
    }
  };

  const clearPdf = () => {
    setManifestPdf(null);
    setExtractedItems([]);
    setPdfStatus({ state: 'idle', message: '' });
    onManifestItemsChange([]);
    onManifestFileChange(null);
  };

  const extractedPreview = useMemo(() => extractedItems.slice(0, 12), [extractedItems]);

  return (
    <aside className="w-full lg:w-[340px] shrink-0">
      <div className="space-y-6 lg:sticky lg:top-20 lg:max-h-[calc(100vh-5rem)] lg:overflow-y-auto lg:pr-1">
        <div className="card card-hover">
          <div className="flex items-baseline justify-between gap-3 mb-3">
            <h3 className="section-title">Cargo declaration</h3>
            <span className="section-subtitle">Manifest PDF</span>
          </div>

          <p className="text-xs text-slate-500 mb-4">
            Upload a manifest PDF. Items are extracted from this PDF and used for comparison.
          </p>

          {manifestItems.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-4">
              {manifestItems.slice(0, 16).map((item, index) => (
                <span key={`${item}-${index}`} className="badge badge-slate">
                  {item}
                </span>
              ))}
              {manifestItems.length > 16 && (
                <span className="badge badge-slate">+{manifestItems.length - 16} more</span>
              )}
            </div>
          )}

          <div className="flex items-center justify-between gap-3 mb-2">
            <div>
              <div className="text-sm font-semibold text-slate-900">Upload manifest PDF</div>
              <div className="text-xs text-slate-500">POST /api/manifest/extract</div>
            </div>
            {(manifestPdf || extractedItems.length > 0) && (
              <button type="button" className="btn-secondary px-3 py-2" onClick={clearPdf}>
                <X className="w-4 h-4" />
                <span className="hidden sm:inline">Clear</span>
              </button>
            )}
          </div>

          {!manifestPdf ? (
            <div className="border border-dashed border-slate-300/80 rounded-xl p-4 text-center transition-all duration-300 hover:border-teal-300 hover:bg-teal-50/25">
              <label className="cursor-pointer block">
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={handlePdfUpload}
                  className="hidden"
                />
                <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-2xl border border-teal-200/60 bg-teal-600/10">
                  <FileText className="w-5 h-5 text-teal-700" />
                </div>
                <div className="text-sm font-semibold text-slate-900">Click to upload PDF</div>
                <div className="text-xs text-slate-500 mt-1">Max 15MB</div>
              </label>
            </div>
          ) : (
            <div className="rounded-xl border border-slate-200 bg-white/70 p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-sm font-semibold text-slate-900 truncate">{manifestPdf.name}</div>
                  <div className="text-xs text-slate-500">
                    {(manifestPdf.size / 1024 / 1024).toFixed(2)} MB
                  </div>
                </div>
                {pdfStatus.state === 'loading' && (
                  <span className="inline-flex items-center gap-2 text-xs font-semibold text-slate-600">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Working…
                  </span>
                )}
              </div>

              {pdfStatus.message && (
                <div
                  className={`mt-3 text-xs ${
                    pdfStatus.state === 'error'
                      ? 'text-red-700'
                      : pdfStatus.state === 'ready'
                        ? 'text-emerald-700'
                        : 'text-slate-600'
                  }`}
                >
                  {pdfStatus.message}
                </div>
              )}

              <div className="mt-4">
                <div className="text-xs font-semibold text-slate-700 mb-2">
                  Extracted items ({extractedCount})
                </div>

                <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3">
                  {extractedCount ? (
                    <div className="flex flex-wrap gap-2">
                      {extractedPreview.map((item, idx) => (
                        <span key={`${item}-${idx}`} className="badge badge-slate">
                          {item}
                        </span>
                      ))}
                      {extractedCount > extractedPreview.length && (
                        <span className="badge badge-slate">
                          +{extractedCount - extractedPreview.length} more
                        </span>
                      )}
                    </div>
                  ) : pdfStatus.state !== 'loading' && pdfStatus.state !== 'error' ? (
                    <div className="text-xs text-slate-500">No items returned.</div>
                  ) : null}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="card card-hover">
          <div className="flex items-baseline justify-between gap-3 mb-3">
            <h3 className="section-title">Reference scan</h3>
            <span className="section-subtitle">Optional</span>
          </div>

          {!referenceImages?.length ? (
            <label
              htmlFor="reference-upload"
              className="block cursor-pointer rounded-xl border border-dashed border-slate-300/80 p-6 text-center transition-all duration-300 hover:border-teal-300 hover:bg-teal-50/30"
            >
              <Upload className="w-8 h-8 mx-auto mb-2 text-slate-400" />
              <span className="text-sm text-slate-700 font-medium block">Upload previous clean scan</span>
              <input
                id="reference-upload"
                type="file"
                accept="image/*"
                multiple
                onChange={onReferenceUpload}
                className="hidden"
              />
              <p className="mt-2 text-xs text-slate-500">
                Compare against a known-good scan to spot changes.
              </p>
            </label>
          ) : (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                {referenceImages.slice(0, 4).map((url, idx) => (
                  <div key={`${url}-${idx}`} className="relative">
                    <img
                      src={url}
                      alt={`Reference scan ${idx + 1}`}
                      className="w-full h-24 object-cover rounded-xl border border-slate-200 bg-slate-100"
                    />
                    <button
                      onClick={() => onRemoveReference(idx)}
                      className="absolute top-2 right-2 inline-flex items-center justify-center h-8 w-8 rounded-full bg-white/90 border border-slate-200 shadow-sm hover:bg-white"
                      type="button"
                      aria-label="Remove reference"
                    >
                      <X className="w-4 h-4 text-slate-700" />
                    </button>
                  </div>
                ))}
              </div>

              {referenceImages.length > 4 && (
                <div className="text-xs text-slate-500">
                  +{referenceImages.length - 4} more reference image(s)
                </div>
              )}

              <div className="flex items-center justify-between gap-3">
                <label className="btn-secondary cursor-pointer px-3 py-2">
                  <Upload className="w-4 h-4" />
                  <span>Add more</span>
                  <input
                    type="file"
                    accept="image/*"
                    multiple
                    onChange={onReferenceUpload}
                    className="hidden"
                  />
                </label>
                <div className="text-xs text-slate-500">Using first image for comparison</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
