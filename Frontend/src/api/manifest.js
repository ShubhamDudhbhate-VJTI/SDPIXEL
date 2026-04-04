import { getApiBaseUrl } from './analyze';

/**
 * POST /api/manifest/extract — multipart field `file` (PDF).
 *
 * Response (enriched):
 *   { items: string[], extraction_method: "vlm"|"pdfplumber",
 *     vlm_result: object|null, risk_analysis: object|null }
 */
export async function extractManifestFromPdf(file) {
  const base = getApiBaseUrl();
  const url = `${base}/api/manifest/extract`;

  const form = new FormData();
  form.append('file', file);

  const res = await fetch(url, {
    method: 'POST',
    body: form,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || `Manifest extract failed (${res.status})`);
  }

  const data = await res.json();

  // Extract items — handle both old ({items}) and new enriched responses
  const raw = data?.items ?? data?.manifest_items ?? [];
  const items = Array.isArray(raw)
    ? raw.map((x) => String(x).trim()).filter(Boolean)
    : [];

  return {
    items,
    extractionMethod: data?.extraction_method ?? 'pdfplumber',
    vlmResult: data?.vlm_result ?? null,
    riskAnalysis: data?.risk_analysis ?? null,
  };
}
