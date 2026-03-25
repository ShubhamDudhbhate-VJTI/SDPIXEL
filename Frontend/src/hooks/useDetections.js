import { useState, useCallback } from 'react';
import { DUMMY_DETECTIONS, DUMMY_RISK } from '../utils/constants';
import { analyzeScan } from '../api/analyze';

export const useDetections = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [detections, setDetections] = useState(null);
  const [risk, setRisk] = useState(null);
  const [outputs, setOutputs] = useState(null);
  const [error, setError] = useState(null);

  const analyze = useCallback(async (imageFile) => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Demo mode: allow running UI without a file selected yet.
      if (!imageFile) {
        setDetections(DUMMY_DETECTIONS);
        setRisk(DUMMY_RISK);
        setOutputs(null);
        return { detections: DUMMY_DETECTIONS, risk: DUMMY_RISK, outputs: null };
      }

      const data = await analyzeScan({ file: imageFile });
      const nextDetections = data?.detections ?? [];
      const nextRisk = data?.risk ?? null;
      const nextOutputs = data?.outputs ?? null;

      setDetections(nextDetections);
      setRisk(nextRisk);
      setOutputs(nextOutputs);

      return { detections: nextDetections, risk: nextRisk, outputs: nextOutputs };
    } catch (err) {
      // Fallback to dummy data so UI remains demo-able without backend.
      setDetections(DUMMY_DETECTIONS);
      setRisk(DUMMY_RISK);
      setOutputs(null);

      const message =
        err?.message
          ? `API error (showing demo data): ${err.message}`
          : 'API error (showing demo data).';
      setError(message);
      return { detections: DUMMY_DETECTIONS, risk: DUMMY_RISK, outputs: null };
    } finally {
      setIsLoading(false);
    }
  }, []);

  const clearResults = useCallback(() => {
    setDetections(null);
    setRisk(null);
    setOutputs(null);
    setError(null);
  }, []);

  return { 
    analyze, 
    isLoading, 
    detections, 
    risk, 
    outputs,
    error, 
    clearResults 
  };
};
