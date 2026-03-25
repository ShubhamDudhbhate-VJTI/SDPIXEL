import { resolveAssetUrl } from '../api/assets';

function HeatmapCell({ title, subtitle, url, emptyLabel }) {
  const src = url ? resolveAssetUrl(url) : null;

  return (
    <div className="card card-hover">
      <div className="flex items-baseline justify-between gap-3 mb-3">
        <h4 className="text-sm font-semibold text-slate-800">{title}</h4>
        {subtitle ? <span className="text-xs text-slate-500">{subtitle}</span> : null}
      </div>
      {src ? (
        <div className="overflow-hidden rounded-xl bg-slate-100 border border-slate-200/70">
          <img src={src} alt={title} className="w-full h-auto" />
        </div>
      ) : (
        <div className="flex min-h-[140px] items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50/80 px-4 text-center text-xs text-slate-500">
          {emptyLabel}
        </div>
      )}
    </div>
  );
}

export default function ScanHeatmapComparison({
  referenceImageUrl,
  uploadImageUrl,
  highlightHeatmapPath,
  outputHeatmapPath,
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="section-title">Scan and heatmap comparison</h3>
        <span className="section-subtitle">Reference vs upload · heatmaps from analyze</span>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <HeatmapCell
          title="Reference scan"
          subtitle="First reference image"
          url={referenceImageUrl}
          emptyLabel="No reference scan uploaded. Add one in the sidebar."
        />
        <HeatmapCell
          title="Upload scan"
          subtitle="Current analysis image"
          url={uploadImageUrl}
          emptyLabel="No upload image."
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <HeatmapCell
          title="Highlighted heatmap"
          subtitle="outputs.highlightHeatmap"
          url={highlightHeatmapPath}
          emptyLabel="Backend can return outputs.highlightHeatmap (path or URL)."
        />
        <HeatmapCell
          title="Output heatmap"
          subtitle="outputs.outputHeatmap"
          url={outputHeatmapPath}
          emptyLabel="Backend can return outputs.outputHeatmap (path or URL)."
        />
      </div>
    </div>
  );
}
