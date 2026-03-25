import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ShieldAlert, AlertTriangle, CheckCircle } from 'lucide-react';

const DetectionList = ({ detections, onDetectionSelect, selectedDetectionId }) => {
  const MotionDiv = motion.div;
  const [animatedValues, setAnimatedValues] = useState({});

  useEffect(() => {
    // Animate progress bars on mount
    const timer = setTimeout(() => {
      const values = {};
      detections?.forEach(detection => {
        values[detection.id] = detection.confidence * 100;
      });
      setAnimatedValues(values);
    }, 100);
    
    return () => clearTimeout(timer);
  }, [detections]);

  const getIcon = (category) => {
    switch (category) {
      case 'prohibited':
        return ShieldAlert;
      case 'suspicious':
        return AlertTriangle;
      case 'clear':
        return CheckCircle;
      default:
        return CheckCircle;
    }
  };

  const getStatusColor = (category) => {
    switch (category) {
      case 'prohibited':
        return 'bg-red-600 text-white';
      case 'suspicious':
        return 'bg-orange-600 text-white';
      case 'clear':
        return 'bg-emerald-600 text-white';
      default:
        return 'bg-gray-500 text-white';
    }
  };

  const getProgressColor = (category) => {
    switch (category) {
      case 'prohibited':
        return 'bg-red-600';
      case 'suspicious':
        return 'bg-orange-600';
      case 'clear':
        return 'bg-emerald-600';
      default:
        return 'bg-gray-500';
    }
  };

  if (!detections || detections.length === 0) {
    return (
      <div className="card">
        <div className="flex items-baseline justify-between gap-3 mb-4">
          <h3 className="section-title">Detected objects</h3>
          <span className="section-subtitle">No issues found</span>
        </div>
        <div className="text-center py-8">
          <CheckCircle className="w-12 h-12 mx-auto mb-3 text-emerald-600" />
          <p className="text-slate-500">No prohibited or suspicious items detected</p>
        </div>
      </div>
    );
  }

  // Sort by confidence (highest first)
  const sortedDetections = [...detections].sort((a, b) => b.confidence - a.confidence);

  return (
    <div className="card card-hover">
      <div className="flex items-baseline justify-between gap-3 mb-4">
        <h3 className="section-title">Detected objects</h3>
        <span className="section-subtitle">Sorted by confidence</span>
      </div>
      
      <div className="space-y-3">
        {sortedDetections.map((detection, index) => {
          const Icon = getIcon(detection.category);
          const confidence = detection.confidence * 100;
          const isSelected = selectedDetectionId === detection.id;
          
          return (
            <MotionDiv
              key={detection.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className={`flex items-center gap-4 p-4 rounded-lg border-2 cursor-pointer transition-all ${
                isSelected 
                  ? 'border-blue-300 bg-blue-50/40' 
                  : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
              }`}
              onClick={() => onDetectionSelect?.(detection.id)}
            >
              {/* Icon */}
              <div className={`p-2 rounded-full ${getStatusColor(detection.category)}`}>
                <Icon className="w-5 h-5" />
              </div>
              
              {/* Item Details */}
              <div className="flex-1">
                <div className="font-semibold text-slate-900">{detection.label}</div>
                
                {/* Progress Bar */}
                <div className="mt-2">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-slate-200/70 rounded-full h-2 overflow-hidden">
                      <MotionDiv
                        className={`h-full ${getProgressColor(detection.category)}`}
                        initial={{ width: 0 }}
                        animate={{ width: `${animatedValues[detection.id] || 0}%` }}
                        transition={{ duration: 1, ease: "easeOut" }}
                      />
                    </div>
                    <span className="text-sm font-medium text-slate-700 min-w-[50px]">
                      {Math.round(confidence)}%
                    </span>
                  </div>
                </div>
              </div>
              
              {/* Status Badge */}
              <span
                className={`badge badge-solid ${getStatusColor(detection.category)}`}
              >
                {detection.category.toUpperCase()}
              </span>
            </MotionDiv>
          );
        })}
      </div>
    </div>
  );
};

export default DetectionList;
