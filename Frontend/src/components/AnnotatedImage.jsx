import { useState, useRef, useCallback } from 'react';
import { AlertTriangle, ShieldAlert, CheckCircle } from 'lucide-react';

const AnnotatedImage = ({ imageUrl, detections, onDetectionHover, selectedDetectionId }) => {
  const [hoveredBox, setHoveredBox] = useState(null);
  const [imgSize, setImgSize] = useState({ w: 1000, h: 800 });
  const imgRef = useRef(null);

  const handleImageLoad = useCallback(() => {
    const img = imgRef.current;
    if (img) {
      setImgSize({ w: img.naturalWidth, h: img.naturalHeight });
    }
  }, []);

  const getBoxColor = (category) => {
    switch (category) {
      case 'prohibited':
        return '#c62828';
      case 'suspicious':
        return '#ef6c00';
      case 'clear':
        return '#2e7d32';
      default:
        return '#666666';
    }
  };

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

  const handleBoxHover = (detection, isHovering) => {
    setHoveredBox(isHovering ? detection.id : null);
    if (onDetectionHover) {
      onDetectionHover(isHovering ? detection : null);
    }
  };

  return (
    <div className="relative bg-slate-100 rounded-xl overflow-hidden border border-slate-200/70">
      {/* Base Image */}
      <img 
        ref={imgRef}
        src={imageUrl} 
        alt="X-ray scan with detections"
        className="w-full h-auto"
        onLoad={handleImageLoad}
      />
      
      {/* SVG Overlay for Bounding Boxes — viewBox matches actual image pixels */}
      <svg 
        className="absolute inset-0 w-full h-full pointer-events-none"
        viewBox={`0 0 ${imgSize.w} ${imgSize.h}`}
        preserveAspectRatio="xMidYMid meet"
      >
        {detections?.map((detection) => {
          const color = getBoxColor(detection.category);
          const isHovered = hoveredBox === detection.id || selectedDetectionId === detection.id;
          const Icon = getIcon(detection.category);
          
          return (
            <g key={detection.id}>
              {/* Bounding Box */}
              <rect
                x={detection.bbox.x}
                y={detection.bbox.y}
                width={detection.bbox.width}
                height={detection.bbox.height}
                fill={color}
                fillOpacity="0.2"
                stroke={color}
                strokeWidth="3"
                rx="4"
                className="pointer-events-auto cursor-pointer transition-all duration-200"
                style={{
                  filter: isHovered ? 'drop-shadow(0 0 8px rgba(0,0,0,0.3))' : 'none',
                  strokeDasharray: isHovered ? 'none' : '0',
                }}
                onMouseEnter={() => handleBoxHover(detection, true)}
                onMouseLeave={() => handleBoxHover(detection, false)}
              />
              
              {/* Label Background */}
              <rect
                x={detection.bbox.x}
                y={detection.bbox.y - 24}
                width={detection.bbox.width}
                height="24"
                fill={color}
                rx="4"
                className="pointer-events-none"
              />
              
              {/* Label Text */}
              <text
                x={detection.bbox.x + 8}
                y={detection.bbox.y - 8}
                fill="white"
                fontSize="14"
                fontWeight="bold"
                className="pointer-events-none"
              >
                {detection.label} {Math.round(detection.confidence * 100)}%
              </text>
              
              {/* Icon */}
              <foreignObject
                x={detection.bbox.x + detection.bbox.width - 20}
                y={detection.bbox.y - 20}
                width="16"
                height="16"
                className="pointer-events-none"
              >
                <Icon className="w-4 h-4 text-white" />
              </foreignObject>
            </g>
          );
        })}
      </svg>
      
      {/* Tooltip */}
      {hoveredBox && (
        <div className="absolute bg-slate-900 text-white px-3 py-2 rounded-xl text-sm pointer-events-none z-10 shadow-lg"
             style={{
               left: `${(detections.find(d => d.id === hoveredBox)?.bbox.x || 0) + 10}px`,
               top: `${(detections.find(d => d.id === hoveredBox)?.bbox.y || 0) - 40}px`
             }}>
          <div className="font-semibold">
            {detections.find(d => d.id === hoveredBox)?.label}
          </div>
          <div className="text-xs opacity-90">
            Confidence: {Math.round((detections.find(d => d.id === hoveredBox)?.confidence || 0) * 100)}%
          </div>
          <div className="absolute w-2 h-2 bg-slate-900 transform rotate-45 -bottom-1 left-4"></div>
        </div>
      )}
    </div>
  );
};

export default AnnotatedImage;
