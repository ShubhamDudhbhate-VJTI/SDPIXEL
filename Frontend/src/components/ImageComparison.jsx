import { useState } from 'react';

const ImageComparison = ({ currentImage, referenceImage }) => {
  const [differenceScore] = useState(42.5);

  const getScoreColor = (score) => {
    if (score < 30) return 'text-emerald-600';
    if (score < 60) return 'text-orange-600';
    return 'text-red-600';
  };

  const getScoreMessage = (score) => {
    if (score < 30) return 'No major changes';
    if (score < 60) return 'Significant differences';
    return 'Major changes detected';
  };

  const getScoreBgColor = (score) => {
    if (score < 30) return 'bg-green-600';
    if (score < 60) return 'bg-orange-600';
    return 'bg-red-600';
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Current Scan */}
        <div className="card card-hover">
          <h4 className="text-sm font-semibold text-slate-700 mb-2">Current scan</h4>
          <div className="aspect-square bg-slate-100 rounded-xl overflow-hidden border border-slate-200/70">
            <img 
              src={currentImage} 
              alt="Current X-ray scan"
              className="w-full h-full object-cover"
            />
          </div>
        </div>

        {/* Reference Scan */}
        <div className="card card-hover">
          <h4 className="text-sm font-semibold text-slate-700 mb-2">Reference scan</h4>
          <div className="aspect-square bg-slate-100 rounded-xl overflow-hidden border border-slate-200/70">
            <img 
              src={referenceImage} 
              alt="Reference X-ray scan"
              className="w-full h-full object-cover"
            />
          </div>
        </div>

        {/* Difference Map */}
        <div className="card card-hover">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Difference</h4>
          <div className="aspect-square bg-slate-100 rounded-xl overflow-hidden relative border border-slate-200/70">
            <img 
              src={currentImage} 
              alt="Difference map"
              className="w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-red-500/25 rounded-xl" />
            <div className="absolute inset-0 bg-gradient-to-br from-transparent via-red-600/15 to-red-800/35 rounded-xl" />
          </div>
        </div>
      </div>

      {/* Difference Score */}
      <div className="card card-hover">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-lg font-semibold text-slate-900">Difference score</h4>
            <p className={`text-sm font-medium ${getScoreColor(differenceScore)}`}>
              {getScoreMessage(differenceScore)}
            </p>
          </div>
          <div className="text-right">
            <div className={`text-3xl font-bold ${getScoreColor(differenceScore)}`}>
              {differenceScore}%
            </div>
          </div>
        </div>
        
        {/* Progress Bar */}
        <div className="mt-4">
          <div className="w-full bg-slate-200/70 rounded-full h-3 overflow-hidden">
            <div 
              className={`h-full ${getScoreBgColor(differenceScore)} transition-all duration-1000`}
              style={{ width: `${differenceScore}%` }}
            />
          </div>
        </div>
        
        {/* Score Indicators */}
        <div className="mt-2 flex justify-between text-xs text-slate-500">
          <span>0% - Identical</span>
          <span>30% - Minor changes</span>
          <span>60% - Major changes</span>
          <span>100% - Completely different</span>
        </div>
      </div>
    </div>
  );
};

export default ImageComparison;
