import { useMemo, useState } from 'react';
import { Download, Loader2 } from 'lucide-react';

const DownloadReport = ({ detections, risk, manifestItems, outputs }) => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [humanVerdict, setHumanVerdict] = useState(null); // 'PASS' | 'FAIL'
  const [officerNotes, setOfficerNotes] = useState('');

  const reportContext = useMemo(() => {
    const declared = Array.isArray(manifestItems) ? manifestItems : [];
    const zs = outputs?.zeroShot ?? null;

    // The backend zero-shot reconciler returns a missing-item list when manifest is supplied.
    const labelsUsed =
      Array.isArray(zs?.labelsUsed) && zs.labelsUsed.length ? zs.labelsUsed : declared;
    const missingItems = Array.isArray(zs?.missingItems) ? zs.missingItems : [];

    const detectedLabelsNorm = new Set(
      (Array.isArray(detections) ? detections : [])
        .map((d) => String(d?.label ?? '').trim().toLowerCase())
        .filter(Boolean)
    );

    // Fallback: compute "not found" directly from detections vs manifest labels.
    const manifestNotFoundFallback = declared.filter((item) => {
      const norm = String(item ?? '').trim().toLowerCase();
      return norm && !detectedLabelsNorm.has(norm);
    });

    const requiresHumanInterventionFromZeroShot =
      Array.isArray(zs?.missingItems) &&
      labelsUsed.length > 0 &&
      missingItems.length === labelsUsed.length;

    const requiresHumanInterventionFromFallback =
      declared.length > 0 && manifestNotFoundFallback.length === declared.length;

    const requiresHumanIntervention =
      requiresHumanInterventionFromZeroShot || requiresHumanInterventionFromFallback;

    const missingForDisplay = requiresHumanInterventionFromZeroShot
      ? missingItems
      : manifestNotFoundFallback;

    return {
      declared,
      zeroShot: zs,
      labelsUsed,
      missingItems,
      missingForDisplay,
      requiresHumanIntervention,
    };
  }, [detections, manifestItems, outputs]);

  const canDownload = useMemo(() => {
    if (!reportContext.requiresHumanIntervention) return true;
    return humanVerdict === 'PASS' || humanVerdict === 'FAIL';
  }, [humanVerdict, reportContext.requiresHumanIntervention]);

  const handleDownload = async () => {
    if (!canDownload) return;
    setIsGenerating(true);

    // Simulate report generation delay
    await new Promise((resolve) => setTimeout(resolve, 2000));

    const reportContent = generateReportContent();
    const blob = new Blob([reportContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `customs_report_${new Date().toISOString().slice(0, 10)}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    setIsGenerating(false);
    setIsReady(true);

    // Reset ready state after 3 seconds
    setTimeout(() => setIsReady(false), 3000);
  };

  const generateReportContent = () => {
    const timestamp = new Date().toLocaleString();
    const zs = reportContext.zeroShot;
    const officerOutcome =
      reportContext.requiresHumanIntervention && humanVerdict
        ? humanVerdict === 'PASS'
          ? 'PASS (released for transport)'
          : 'FAIL (held for inspection)'
        : reportContext.requiresHumanIntervention
          ? 'PENDING (human decision required)'
          : 'Not required (auto assessment)';

    const officerNotesBlock = officerNotes?.trim() ? officerNotes.trim() : 'None provided.';

    let content = `CUSTOMS INSPECTION REPORT\n`;
    content += `=========================\n\n`;
    content += `Generated: ${timestamp}\n\n`;
    content += `System: Customs X-ray Intelligence Platform\n`;
    content += `Version: v1.0 (frontend)\n\n`;
    content += `Scan & Decision Basis\n`;
    content += `----------------------\n`;
    content += `- YOLOv8 detections for object labeling\n`;
    content += `- Zero-shot manifest reconciliation (OWL-ViT v2 + SAM 2)\n\n`;

    content += `RISK ASSESSMENT\n`;
    content += `----------------\n`;
    content += `Risk Level: ${risk?.level || 'UNKNOWN'}\n`;
    content += `Risk Score: ${risk?.score ?? 0}\n`;
    content += `Reason: ${risk?.reason || 'No reason provided'}\n\n`;

    content += `MANIFEST RECONCILIATION (ZERO-SHOT)\n`;
    content += `------------------------------------\n`;
    content += `Zero-shot verdict: ${zs?.verdict || 'N/A'}\n`;
    content += `Labels evaluated: ${Array.isArray(reportContext.labelsUsed) ? reportContext.labelsUsed.length : 0}\n`;
    content += `Missing declared items: ${Array.isArray(zs?.missingItems) ? zs.missingItems.length : 0}\n\n`;

    content += `HUMAN OFFICER REVIEW\n`;
    content += `--------------------\n`;
    content += `Outcome: ${officerOutcome}\n`;
    content += `Officer notes: ${officerNotesBlock}\n\n`;

    if (reportContext.requiresHumanIntervention && Array.isArray(reportContext.missingForDisplay)) {
      content += `CAUSE FOR HUMAN INTERVENTION\n`;
      content += `-------------------------------\n`;
      content += `The system could not visually detect any declared manifest items.\n`;
      content += `Missing items (${reportContext.missingForDisplay.length}):\n`;
      reportContext.missingForDisplay.forEach((item) => {
        content += `- ${item}\n`;
      });
      content += `\n`;
    }

    if (detections && detections.length > 0) {
      content += `DETECTED ITEMS\n`;
      content += `-------------\n`;
      detections.forEach((detection, index) => {
        content += `${index + 1}. ${detection.label} - ${Math.round(detection.confidence * 100)}% (${detection.category})\n`;
      });
      content += `\n`;
    }

    if (manifestItems && manifestItems.length > 0) {
      content += `MANIFEST ITEMS\n`;
      content += `---------------\n`;
      manifestItems.forEach((item, index) => {
        content += `${index + 1}. ${item}\n`;
      });
      content += `\n`;
    }

    content += `DISCLAIMER\n`;
    content += `----------\n`;
    content += `This report was generated by an AI-assisted system. Final inspection decisions must be made by a certified customs officer.\n`;

    return content;
  };

  return (
    <div className="w-full max-w-md mx-auto space-y-3">
      {reportContext.requiresHumanIntervention && (
        <div className="card border-red-200 bg-red-50/60 p-4">
          <div className="font-semibold text-red-900">
            Suspicious cargo — human intervention required
          </div>
          <div className="text-xs text-red-700 mt-1">
            None of the declared manifest items were detected in the scan.
          </div>

          {Array.isArray(reportContext.missingForDisplay) && reportContext.missingForDisplay.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {reportContext.missingForDisplay.slice(0, 12).map((item, idx) => (
                <span
                  key={`${item}-${idx}`}
                  className="inline-flex items-center px-2 py-1 rounded-lg text-xs font-semibold bg-red-100 text-red-900 border border-red-200"
                >
                  {item}
                </span>
              ))}
              {reportContext.missingForDisplay.length > 12 && (
                <span className="text-xs text-red-700 font-semibold mt-1">
                  +{reportContext.missingForDisplay.length - 12} more
                </span>
              )}
            </div>
          )}

          {!humanVerdict && (
            <div className="mt-3 text-xs text-red-800 font-semibold">
              Select PASS or FAIL to enable report download.
            </div>
          )}

          <div className="mt-3">
            <div className="text-xs font-semibold text-slate-800 mb-2">Officer outcome</div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setHumanVerdict('PASS')}
                className={`btn-secondary flex-1 ${
                  humanVerdict === 'PASS'
                    ? 'border-emerald-500 bg-emerald-100 text-emerald-900'
                    : ''
                }`}
              >
                PASS
              </button>
              <button
                type="button"
                onClick={() => setHumanVerdict('FAIL')}
                className={`btn-secondary flex-1 ${
                  humanVerdict === 'FAIL'
                    ? 'border-red-500 bg-red-100 text-red-900'
                    : ''
                }`}
              >
                FAIL
              </button>
            </div>
          </div>

          <div className="mt-3">
            <label className="block text-xs font-semibold text-slate-800 mb-1">
              Officer notes (optional)
            </label>
            <textarea
              value={officerNotes}
              onChange={(e) => setOfficerNotes(e.target.value)}
              rows={3}
              className="focus-brand w-full rounded-xl border border-slate-200 bg-white/70 px-3 py-2 text-sm text-slate-900"
              placeholder="e.g., Verified documentation / items found / reason for release or hold…"
            />
          </div>
        </div>
      )}

      <button
        onClick={handleDownload}
        disabled={isGenerating || (reportContext.requiresHumanIntervention && !canDownload)}
        className={`btn-primary w-full max-w-md mx-auto ${
          isGenerating || (reportContext.requiresHumanIntervention && !canDownload)
            ? 'opacity-75 cursor-not-allowed'
            : ''
        } ${isReady ? 'bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800' : ''}`}
      >
        {isGenerating ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>Generating report…</span>
          </>
        ) : isReady ? (
          <>
            <Download className="w-5 h-5" />
            <span>Report ready</span>
          </>
        ) : (
          <>
            <Download className="w-5 h-5" />
            <span>Download report</span>
          </>
        )}
      </button>
    </div>
  );
};

export default DownloadReport;
