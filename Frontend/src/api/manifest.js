import { getApiBaseUrl } from './analyze';

/**
 * POST /api/manifest/extract — multipart field `file` (PDF).
 * Response: { items: string[] }
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
  const raw = data?.items ?? data?.manifest_items ?? [];
  const items = Array.isArray(raw)
    ? raw.map((x) => String(x).trim()).filter(Boolean)
    : [];

  return { items };
}
