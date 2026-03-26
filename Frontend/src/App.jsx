import { useState } from 'react';
import { motion } from 'framer-motion';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import ImageUploader from './components/ImageUploader';
import AnnotatedImage from './components/AnnotatedImage';
import RiskBadge from './components/RiskBadge';
import DetectionList from './components/DetectionList';
import ManifestComparison from './components/ManifestComparison';
import MetricsPanel from './components/MetricsPanel';
import GradCamHeatmap from './components/GradCamHeatmap';
import ScanHeatmapComparison from './components/ScanHeatmapComparison';
import DownloadReport from './components/DownloadReport';
import ResultsOutputs from './components/ResultsOutputs';
import ZeroShotOutput from './components/ZeroShotOutput';
import { useDetections } from './hooks/useDetections';
import { Loader2 } from 'lucide-react';
import heroImage from './assets/hero.png';

function App() {
  const MotionDiv = motion.div;

  const [uploadedImages, setUploadedImages] = useState([]);
  const [referenceImages, setReferenceImages] = useState([]);
  const [manifestItems, setManifestItems] = useState([]);
  const [manifestPdfFile, setManifestPdfFile] = useState(null);
  const [selectedDetectionId, setSelectedDetectionId] = useState(null);

  const { analyze, isLoading, detections, risk, outputs, error, clearResults } = useDetections();

  const handleImagesSelect = (images) => {
    setUploadedImages(images);
    clearResults();
    setSelectedDetectionId(null);
  };

  const handleClearImage = () => {
    setUploadedImages([]);
    setSelectedDetectionId(null);
    clearResults();
  };

  const handleReferenceUpload = (e) => {
    const files = Array.from(e.target.files ?? []);
    if (!files.length) return;

    files.forEach((file) => {
      const reader = new FileReader();
      reader.onload = (event) => {
        setReferenceImages((prev) => [
          ...prev,
          { file, url: event.target.result, name: file.name },
        ]);
      };
      reader.readAsDataURL(file);
    });
  };

  const handleRemoveReference = (indexToRemove) => {
    setReferenceImages((prev) => prev.filter((_, idx) => idx !== indexToRemove));
  };

  const handleAnalyze = async () => {
    try {
      await analyze({
        file: uploadedImages?.[0]?.file,
        reference: referenceImages?.[0]?.file,
        manifest: manifestPdfFile ?? undefined,
      });
    } catch (err) {
      console.error('Analysis failed:', err);
    }
  };

  const primaryUploaded = uploadedImages?.[0] ?? null;
  const primaryReference = referenceImages?.[0]?.url ?? null;

  const gradcamUrl =
    outputs?.gradcam ?? outputs?.gradCamImage ?? outputs?.grad_cam ?? null;
  const highlightHeatmapPath =
    outputs?.highlightHeatmap ?? outputs?.highlight_heatmap ?? null;
  const outputHeatmapPath =
    outputs?.outputHeatmap ?? outputs?.output_heatmap ?? null;

  const handleDetectionSelect = (detectionId) => {
    setSelectedDetectionId(detectionId === selectedDetectionId ? null : detectionId);
  };

  return (
    <div className="app-shell">
      <Header />

      <div className="container-page">
        <div className="flex flex-col gap-6 py-6 lg:flex-row">
          <Sidebar
            manifestItems={manifestItems}
            onManifestItemsChange={setManifestItems}
            onManifestFileChange={setManifestPdfFile}
            referenceImages={referenceImages.map((r) => r.url)}
            onReferenceUpload={handleReferenceUpload}
            onRemoveReference={handleRemoveReference}
          />

          <main className="min-w-0 flex-1 space-y-6">
            <ImageUploader
              selectedImages={uploadedImages}
              onImagesSelect={handleImagesSelect}
              onClearImage={handleClearImage}
            />

            {!detections && (
              <MotionDiv
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center"
              >
                <button
                  onClick={handleAnalyze}
                  disabled={isLoading}
                  className="btn-primary w-full max-w-sm"
                >
                  {isLoading ? (
                    <span className="inline-flex items-center justify-center gap-2">
                      <Loader2 className="w-5 h-5 animate-spin" />
                      AI analyzing…
                    </span>
                  ) : primaryUploaded ? (
                    'Analyze with AI'
                  ) : (
                    'Run demo analysis'
                  )}
                </button>
                {!primaryUploaded && (
                  <p className="mt-2 text-xs text-slate-500">
                    Upload a scan to analyze real input. Demo runs with placeholder outputs.
                  </p>
                )}
              </MotionDiv>
            )}

            {isLoading && (
              <MotionDiv
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-center py-12"
              >
                <Loader2 className="w-12 h-12 animate-spin mx-auto mb-4 text-blue-600" />
                <p className="text-lg font-medium text-gray-700">
                  Analyzing X-ray scan with AI...
                </p>
                <p className="text-sm text-gray-500 mt-2">
                  This may take a few seconds
                </p>
              </MotionDiv>
            )}

            {detections && (
              <MotionDiv
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="space-y-6"
              >
                <div className="space-y-6">
                  <div>
                    <h2 className="text-xl font-semibold tracking-tight text-slate-900">
                      Final output
                    </h2>
                    <p className="section-subtitle">Manifest-derived cargo list.</p>
                  </div>

                  <ResultsOutputs outputs={outputs} manifestItems={manifestItems} />
                </div>

                <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                  <div className="card card-hover">
                    <div className="flex items-baseline justify-between gap-3 mb-4">
                      <h3 className="section-title">Original scan</h3>
                      <span className="section-subtitle">Uploaded image</span>
                    </div>
                    <div className="overflow-hidden rounded-xl bg-slate-100 border border-slate-200/70">
                      <img
                        src={primaryUploaded?.url ?? heroImage}
                        alt="Original X-ray scan"
                        className="w-full h-auto"
                      />
                    </div>
                  </div>

                  <div className="card card-hover">
                    <div className="flex items-baseline justify-between gap-3 mb-4">
                      <h3 className="section-title">Detections</h3>
                      <span className="section-subtitle">Annotated overlay</span>
                    </div>
                    <AnnotatedImage
                      imageUrl={primaryUploaded?.url ?? heroImage}
                      detections={detections}
                      selectedDetectionId={selectedDetectionId}
                    />
                  </div>
                </div>

                <GradCamHeatmap
                  imageUrl={primaryUploaded?.url ?? heroImage}
                  gradcamUrl={gradcamUrl}
                />

                <ScanHeatmapComparison
                  referenceImageUrl={primaryReference}
                  uploadImageUrl={primaryUploaded?.url ?? heroImage}
                  highlightHeatmapPath={highlightHeatmapPath}
                  outputHeatmapPath={outputHeatmapPath}
                />

                <RiskBadge level={risk?.level} score={risk?.score} reason={risk?.reason} />

                <ZeroShotOutput outputs={outputs} />

                <DetectionList
                  detections={detections}
                  onDetectionSelect={handleDetectionSelect}
                  selectedDetectionId={selectedDetectionId}
                />

                <ManifestComparison manifestItems={manifestItems} detections={detections} />

                <MetricsPanel />

                <div className="text-center">
                  <DownloadReport
                    detections={detections}
                    risk={risk}
                    manifestItems={manifestItems}
                  />
                </div>
              </MotionDiv>
            )}

            {error && (
              <div className="card border-red-200 bg-red-50/60">
                <h3 className="section-title text-red-900 mb-2">Analysis failed</h3>
                <p className="text-red-700">{error}</p>
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}

export default App;
