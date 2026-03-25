import { useEffect, useMemo, useState } from 'react';
import { FileText, Loader2, Upload, X } from 'lucide-react';
import { extractManifestItemsFromPdf } from '../utils/pdfManifest';

const Sidebar = ({ 
  declaredItems, 
  onDeclarationChange, 
  referenceImages, 
  onReferenceUpload,
  onRemoveReference 
}) => {
  const [rawDeclarationText, setRawDeclarationText] = useState(declaredItems.join('\n'));
  const [manifestPdf, setManifestPdf] = useState(null);
  const [pdfStatus, setPdfStatus] = useState({ state: 'idle', message: '' });
  const [extractedItems, setExtractedItems] = useState([]);

  useEffect(() => {
    setRawDeclarationText(declaredItems.join('\n'));
  }, [declaredItems]);

  const declaredCount = declaredItems.length;
  const extractedCount = extractedItems.length;

  const handleTextChange = (e) => {
    const text = e.target.value;
    setRawDeclarationText(text);
    const items = text
      .split('\n')
      .map(line => line.trim())
      .filter(line => line.length > 0);
    onDeclarationChange(text, items);
  };

  const applyExtractedToDeclaration = () => {
    const nextText = extractedItems.join('\n');
    const nextItems = extractedItems;
    onDeclarationChange(nextText, nextItems);
  };

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
      const { items } = await extractManifestItemsFromPdf(file);
      setExtractedItems(items);
      setPdfStatus({
        state: 'ready',
        message: items.length ? `Extracted ${items.length} item(s).` : 'No items found in PDF text.',
      });
    } catch (err) {
      setExtractedItems([]);
      setPdfStatus({
        state: 'error',
        message: err?.message ? `Failed to read PDF: ${err.message}` : 'Failed to read PDF.',
      });
    }
  };

  const clearPdf = () => {
    setManifestPdf(null);
    setExtractedItems([]);
    setPdfStatus({ state: 'idle', message: '' });
  };

  const extractedPreview = useMemo(() => extractedItems.slice(0, 12), [extractedItems]);

  return (
    <aside className="w-full lg:w-[340px] shrink-0">
      <div className="space-y-6 lg:sticky lg:top-20 lg:max-h-[calc(100vh-5rem)] lg:overflow-y-auto lg:pr-1">
      {/* Cargo Declaration */}
      <div className="card card-hover">
        <div className="flex items-baseline justify-between gap-3 mb-3">
          <h3 className="section-title">Cargo declaration</h3>
          <span className="section-subtitle">Manifest</span>
        </div>
        
        {/* Tag Pills */}
        {declaredItems.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {declaredItems.map((item, index) => (
              <span 
                key={index}
                className="badge badge-slate"
              >
                {item}
              </span>
            ))}
          </div>
        )}
        
        <textarea
          value={rawDeclarationText}
          onChange={handleTextChange}
          placeholder="e.g.&#10;Textiles&#10;Laptop batteries&#10;Kitchen tools"
          className="w-full h-32 p-3 text-sm border border-slate-200 rounded-xl resize-none bg-white/80 focus:outline-none focus-visible:ring-4 focus-visible:ring-blue-200"
        />
        
        <p className="text-xs text-slate-500 mt-2">
          Enter one item per line for manifest comparison
        </p>

        {/* PDF Upload + Extraction */}
        <div className="mt-5 pt-5 border-t border-slate-200/70">
          <div className="flex items-center justify-between gap-3 mb-2">
            <div>
              <div className="text-sm font-semibold text-slate-900">Upload manifest PDF</div>
              <div className="text-xs text-slate-500">
                Extract objects/items and fill the declaration box.
              </div>
            </div>
            {(manifestPdf || extractedItems.length > 0) && (
              <button type="button" className="btn-secondary px-3 py-2" onClick={clearPdf}>
                <X className="w-4 h-4" />
                <span className="hidden sm:inline">Clear</span>
              </button>
            )}
          </div>

          {!manifestPdf ? (
            <div className="border border-dashed border-slate-300/80 rounded-xl p-4 text-center hover:border-blue-300 hover:bg-blue-50/20 transition-colors">
              <label className="cursor-pointer block">
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={handlePdfUpload}
                  className="hidden"
                />
                <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-2xl bg-blue-600/10 border border-blue-200/50">
                  <FileText className="w-5 h-5 text-blue-700" />
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
                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className="text-xs font-semibold text-slate-700">
                    Extracted items ({extractedCount})
                  </div>
                  <button
                    type="button"
                    className="btn-primary px-3 py-2 text-sm"
                    onClick={applyExtractedToDeclaration}
                    disabled={!extractedCount}
                    title={!extractedCount ? 'Upload a PDF with detectable item text' : 'Fill the declaration box'}
                  >
                    Use extracted
                  </button>
                </div>

                <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3">
                  {extractedCount ? (
                    <div className="flex flex-wrap gap-2">
                      {extractedPreview.map((item) => (
                        <span key={item} className="badge badge-slate">
                          {item}
                        </span>
                      ))}
                      {extractedCount > extractedPreview.length && (
                        <span className="badge badge-slate">
                          +{extractedCount - extractedPreview.length} more
                        </span>
                      )}
                    </div>
                  ) : (
                    <div className="text-xs text-slate-500">
                      Extracted items will appear here after upload.
                    </div>
                  )}
                </div>

                <div className="mt-2 text-xs text-slate-500">
                  Current declared items: {declaredCount}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Reference Scan */}
      <div className="card card-hover">
        <div className="flex items-baseline justify-between gap-3 mb-3">
          <h3 className="section-title">Reference scan</h3>
          <span className="section-subtitle">Optional</span>
        </div>
        
        {!referenceImages?.length ? (
          <div className="border border-dashed border-slate-300/80 rounded-xl p-6 text-center hover:border-blue-300 hover:bg-blue-50/30 transition-colors">
            <Upload className="w-8 h-8 mx-auto mb-2 text-slate-400" />
            <label className="cursor-pointer">
              <span className="text-sm text-slate-700 font-medium">Upload previous clean scan</span>
              <input
                type="file"
                accept="image/*"
                multiple
                onChange={onReferenceUpload}
                className="hidden"
              />
            </label>
            <p className="mt-2 text-xs text-slate-500">
              Compare against a known-good scan to spot changes.
            </p>
          </div>
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
              <div className="text-xs text-slate-500">
                Using first image for comparison
              </div>
            </div>
          </div>
        )}
      </div>
      </div>
    </aside>
  );
};

export default Sidebar;
