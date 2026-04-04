import { useMemo, useState } from 'react';
import { FileText, Loader2, Upload, X, Sparkles, ShieldCheck, AlertTriangle } from 'lucide-react';
import { extractManifestFromPdf } from '../api/manifest';

const Sidebar = ({
  manifestItems,
  onManifestItemsChange,
  onManifestFileChange,
  onVlmDataChange,
  referenceImages,
  onReferenceUpload,
  onRemoveReference,
}) => {
  const [manifestPdf, setManifestPdf] = useState(null);
  const [pdfStatus, setPdfStatus] = useState({ state: 'idle', message: '' });
  const [extractedItems, setExtractedItems] = useState([]);
  const [extractionMethod, setExtractionMethod] = useState(null);
  const [vlmResult, setVlmResult] = useState(null);
  const [riskAnalysis, setRiskAnalysis] = useState(null);

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
    setPdfStatus({ state: 'loading', message: 'Extracting items via AI — this may take a minute…' });

    try {
      const result = await extractManifestFromPdf(file);
      setExtractedItems(result.items);
      setExtractionMethod(result.extractionMethod);
      setVlmResult(result.vlmResult);
      setRiskAnalysis(result.riskAnalysis);
      onManifestItemsChange(result.items);
      onManifestFileChange(file);
      if (onVlmDataChange) {
        onVlmDataChange({
          vlmResult: result.vlmResult,
          riskAnalysis: result.riskAnalysis,
          extractionMethod: result.extractionMethod,
        });
      }
      setPdfStatus({
        state: 'ready',
        message: result.items.length
          ? `Extracted ${result.items.length} item(s) via ${result.extractionMethod === 'vlm' ? 'AI Vision Model' : 'text parser'}.`
          : 'No items found in PDF.',
      });
    } catch (err) {
      setExtractedItems([]);
      setExtractionMethod(null);
      setVlmResult(null);
      setRiskAnalysis(null);
      onManifestItemsChange([]);
      onManifestFileChange(null);
      if (onVlmDataChange) onVlmDataChange(null);
      setPdfStatus({
        state: 'error',
        message: err?.message ? String(err.message) : 'Manifest extract failed.',
      });
    }
  };

  const clearPdf = () => {
    setManifestPdf(null);
    setExtractedItems([]);
    setExtractionMethod(null);
    setVlmResult(null);
    setRiskAnalysis(null);
    setPdfStatus({ state: 'idle', message: '' });
    onManifestItemsChange([]);
    onManifestFileChange(null);
    if (onVlmDataChange) onVlmDataChange(null);
  };

  const extractedPreview = useMemo(() => extractedItems.slice(0, 12), [extractedItems]);

  // Build rich item details from VLM output when available
  const vlmItems = useMemo(() => {
    if (!vlmResult?.extracted_items) return null;
    return vlmResult.extracted_items.slice(0, 12).map((item, idx) => ({
      key: idx,
      name: item.item_name || `Item ${idx + 1}`,
      quantity: item.units ?? item.packages ?? null,
      hsCode: item.hs_code || null,
      value: item.total_value ?? null,
    }));
  }, [vlmResult]);

  // Risk level styling
  const riskLevel = riskAnalysis?.risk_level;
  const riskScore = riskAnalysis?.Data_Risk;
  const riskColor = riskLevel === 'HIGH'
    ? 'border-red-200 bg-red-50 text-red-800'
    : riskLevel === 'MEDIUM'
      ? 'border-amber-200 bg-amber-50 text-amber-800'
      : riskLevel === 'LOW'
        ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
        : 'border-slate-200 bg-slate-50 text-slate-700';
  const RiskIcon = riskLevel === 'HIGH' ? AlertTriangle : ShieldCheck;

  return (
    <aside className="w-full lg:w-[340px] shrink-0">
      <div className="space-y-6 lg:sticky lg:top-20 lg:max-h-[calc(100vh-5rem)] lg:overflow-y-auto lg:pr-1">
        <div className="card card-hover">
          <div className="flex items-baseline justify-between gap-3 mb-3">
            <h3 className="section-title">Cargo declaration</h3>
            <span className="section-subtitle">Manifest PDF</span>
          </div>

          <p className="text-xs text-slate-500 mb-4">
            Upload a manifest PDF. Items are extracted via AI vision model and used for inspection.
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
              <div className="text-xs text-slate-500">VLM extraction + risk analysis</div>
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
                <div className="text-xs text-slate-500 mt-1">Max 15MB · AI extracts items automatically</div>
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
                  <span className="inline-flex items-center gap-2 text-xs font-semibold text-teal-700">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    AI analyzing…
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

              {/* Extraction method badge */}
              {extractionMethod && pdfStatus.state === 'ready' && (
                <div className="mt-3 flex items-center gap-2">
                  <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide ${
                    extractionMethod === 'vlm'
                      ? 'border border-violet-200 bg-violet-50 text-violet-700'
                      : 'border border-slate-200 bg-slate-50 text-slate-600'
                  }`}>
                    {extractionMethod === 'vlm' && <Sparkles className="w-3 h-3" />}
                    {extractionMethod === 'vlm' ? 'AI Vision Model' : 'Text Parser'}
                  </span>
                </div>
              )}

              {/* Risk analysis summary */}
              {riskAnalysis && pdfStatus.state === 'ready' && (
                <div className={`mt-3 flex items-center gap-2 rounded-lg border px-3 py-2 ${riskColor}`}>
                  <RiskIcon className="w-4 h-4 shrink-0" />
                  <div className="min-w-0">
                    <span className="text-xs font-bold">{riskLevel} RISK</span>
                    {riskScore != null && (
                      <span className="ml-2 text-xs font-medium opacity-80">
                        Score: {riskScore.toFixed(4)}
                      </span>
                    )}
                  </div>
                </div>
              )}

              <div className="mt-4">
                <div className="text-xs font-semibold text-slate-700 mb-2">
                  Extracted items ({extractedCount})
                </div>

                <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3">
                  {vlmItems && vlmItems.length > 0 ? (
                    /* Rich VLM items with details */
                    <div className="space-y-2">
                      {vlmItems.map((item) => (
                        <div
                          key={item.key}
                          className="flex items-center justify-between gap-2 rounded-lg border border-slate-100 bg-white/80 px-2.5 py-1.5"
                        >
                          <span className="text-xs font-medium text-slate-900 truncate min-w-0">
                            {item.name}
                          </span>
                          <div className="flex items-center gap-1.5 shrink-0">
                            {item.quantity != null && (
                              <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-600">
                                ×{item.quantity}
                              </span>
                            )}
                            {item.hsCode && (
                              <span className="rounded bg-teal-50 px-1.5 py-0.5 text-[10px] font-semibold text-teal-700">
                                HS:{item.hsCode}
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                      {vlmResult?.extracted_items?.length > 12 && (
                        <div className="text-[10px] text-slate-500 text-center pt-1">
                          +{vlmResult.extracted_items.length - 12} more items
                        </div>
                      )}
                    </div>
                  ) : extractedCount ? (
                    /* Simple item badges (pdfplumber fallback) */
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
