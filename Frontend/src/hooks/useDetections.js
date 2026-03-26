import { useState, useCallback } from 'react';
import { DUMMY_DETECTIONS, DUMMY_RISK } from '../utils/constants';
import { analyzeScan } from '../api/analyze';

export const useDetections = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [detections, setDetections] = useState(null);
  const [risk, setRisk] = useState(null);
  const [outputs, setOutputs] = useState(null);
  const [error, setError] = useState(null);

  /**
   * @param {{ file?: File, reference?: File, manifest?: File } | undefined} payload
   */
  const analyze = useCallback(async (payload) => {
    setIsLoading(true);
    setError(null);

    const file = payload?.file;

    try {
      if (!file) {
        setDetections(DUMMY_DETECTIONS);
        setRisk(DUMMY_RISK);
        setOutputs(null);
        return { detections: DUMMY_DETECTIONS, risk: DUMMY_RISK, outputs: null };
      }

      const data = await analyzeScan({
        file,
        reference: payload?.reference,
        manifest: payload?.manifest,
      });
      const nextDetections = data?.detections ?? [];
      const nextRisk = data?.risk ?? null;
      const nextOutputs = data?.outputs ?? null;

      setDetections(nextDetections);
      setRisk(nextRisk);
      setOutputs(nextOutputs);

      return { detections: nextDetections, risk: nextRisk, outputs: nextOutputs };
    } catch (err) {
      setDetections([]);
      setRisk(null);
      setOutputs(null);

      const message =
        err?.message
          ? `Analysis failed: ${err.message}`
          : 'Analysis failed — check that the backend server is running.';
      setError(message);
      return { detections: [], risk: null, outputs: null };
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
    clearResults,
  };
};
