import { PROHIBITED_TERMS_LOWER } from '../utils/constants';

const ManifestComparison = ({ manifestItems, detections }) => {
  const normalizeItem = (text) => text.trim().toLowerCase();
  
  const isProhibited = (label) => PROHIBITED_TERMS_LOWER.has(normalizeItem(label));

  const getComparisonData = () => {
    const declaredNorm = {};
    (manifestItems ?? []).forEach((item) => {
      const s = String(item).trim();
      if (s) {
        declaredNorm[normalizeItem(s)] = s;
      }
    });

    const detectedNorm = {};
    detections?.forEach(detection => {
      detectedNorm[normalizeItem(detection.label)] = detection.label;
    });

    const rows = [];

    // Process detected items
    Object.entries(detectedNorm).forEach(([norm, original]) => {
      if (isProhibited(original)) {
        rows.push({
          item: original,
          source: 'Detected',
          status: 'PROHIBITED',
        });
      } else if (declaredNorm[norm]) {
        rows.push({
          item: original,
          source: 'Detected',
          status: 'MATCH',
        });
      } else {
        rows.push({
          item: original,
          source: 'Detected',
          status: 'UNDECLARED',
        });
      }
    });

    // Process declared items that weren't detected
    Object.entries(declaredNorm).forEach(([norm, original]) => {
      if (!detectedNorm[norm]) {
        rows.push({
          item: original,
          source: 'Declared',
          status: 'NOT_FOUND',
        });
      }
    });

    return rows;
  };

  const getStatusClass = (status) => {
    switch (status) {
      case 'PROHIBITED':
        return "badge badge-solid bg-red-600";
      case 'UNDECLARED':
        return "badge badge-danger";
      case 'NOT_FOUND':
        return "badge badge-warning";
      case 'MATCH':
        return 'badge badge-success';
      default:
        return 'badge badge-slate';
    }
  };

  const getRowBackground = (status) => {
    switch (status) {
      case 'PROHIBITED':
      case 'UNDECLARED':
        return 'bg-red-50/50';
      case 'NOT_FOUND':
        return 'bg-orange-50/60';
      case 'MATCH':
        return 'bg-emerald-50/50';
      default:
        return '';
    }
  };

  const comparisonData = getComparisonData();
  const discrepancies = comparisonData.filter(row => 
    row.status === 'PROHIBITED' || row.status === 'UNDECLARED' || row.status === 'NOT_FOUND'
  ).length;

  if (!manifestItems?.length) {
    return null;
  }

  return (
    <div className="card card-hover">
      <div className="flex items-baseline justify-between gap-3 mb-4">
        <h3 className="section-title">Manifest vs detections</h3>
        <span className="section-subtitle">Discrepancy review</span>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-200">
              <th className="text-left py-3 px-4 font-semibold text-slate-900">Item</th>
              <th className="text-left py-3 px-4 font-semibold text-slate-900">Source</th>
              <th className="text-left py-3 px-4 font-semibold text-slate-900">Status</th>
            </tr>
          </thead>
          <tbody>
            {comparisonData.map((row, index) => (
              <tr 
                key={index}
                className={`border-b border-slate-100 ${getRowBackground(row.status)}`}
              >
                <td className="py-3 px-4">
                  <span className="font-medium text-slate-900">{row.item}</span>
                </td>
                <td className="py-3 px-4">
                  <span className="text-sm text-slate-600">{row.source}</span>
                </td>
                <td className="py-3 px-4">
                  <span className={getStatusClass(row.status)}>
                    {row.status.replace('_', ' ')}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {discrepancies > 0 && (
        <div className="mt-4 rounded-xl border border-red-200 bg-red-50/60 p-4">
          <div className="flex items-center gap-2">
            <span className="text-red-700 font-semibold">
              {discrepancies} discrepancies found
            </span>
            <span className="text-sm text-red-600">(Requires attention)</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default ManifestComparison;
