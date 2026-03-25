import { MODEL_METRICS } from '../utils/constants';

const MetricsPanel = () => {
  return (
    <div className="card card-hover">
      <div className="flex items-baseline justify-between gap-3 mb-4">
        <h3 className="section-title">Model performance</h3>
        <span className="section-subtitle">Reference metrics</span>
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        {Object.entries(MODEL_METRICS).map(([metric, value]) => (
          <div key={metric} className="flex items-center justify-between gap-4">
            <span className="text-sm font-medium text-slate-600">{metric}</span>
            <span className="text-sm font-semibold text-slate-900 tabular-nums">
              {value}
            </span>
          </div>
        ))}
      </div>
      
      <div className="mt-4 pt-4 border-t border-slate-200">
        <p className="text-xs text-slate-500">
          Performance metrics computed on held-out test set not seen during training.
        </p>
      </div>
    </div>
  );
};

export default MetricsPanel;
