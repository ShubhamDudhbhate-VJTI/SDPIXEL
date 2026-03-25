import { resolveAssetUrl } from '../api/assets';

const GradCamHeatmap = ({ imageUrl, gradcamUrl }) => {
  const resolvedGradcam = gradcamUrl ? resolveAssetUrl(gradcamUrl) : null;

  return (
    <div className="card card-hover">
      <div className="flex items-baseline justify-between gap-3 mb-4">
        <h3 className="section-title">AI attention heatmap</h3>
        <span className="section-subtitle">
          {resolvedGradcam ? 'From API' : 'Model focus regions (preview)'}
        </span>
      </div>

      {resolvedGradcam ? (
        <div className="overflow-hidden rounded-xl bg-slate-100 border border-slate-200/70">
          <img
            src={resolvedGradcam}
            alt="Grad-CAM heatmap"
            className="w-full h-auto"
          />
        </div>
      ) : (
        <div className="relative">
          <div className="relative">
            <img
              src={imageUrl}
              alt="X-ray scan"
              className="w-full h-auto opacity-50 rounded-xl border border-slate-200/70"
            />

            <div className="absolute inset-0 bg-gradient-to-br from-transparent via-red-500/25 to-red-700/55 rounded-xl" />

            <div className="absolute top-4 right-4 bg-white/90 backdrop-blur-sm rounded-xl p-3 shadow-lg border border-slate-200/70">
              <div className="text-xs font-semibold text-slate-700 mb-2">Intensity</div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-red-700 rounded" />
                  <span className="text-xs text-slate-600">High</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-red-500 rounded" />
                  <span className="text-xs text-slate-600">Medium</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-red-300 rounded" />
                  <span className="text-xs text-slate-600">Low</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50/70 p-4">
        <p className="text-sm text-slate-700">
          <span className="font-semibold text-slate-900">Interpretation:</span>{' '}
          {resolvedGradcam
            ? 'Heatmap image returned as outputs.gradcam (or grad_cam / gradCamImage).'
            : 'Brighter red areas indicate regions that most influenced the model’s decision (placeholder overlay until the API returns a heatmap).'}
        </p>
      </div>
    </div>
  );
};

export default GradCamHeatmap;
