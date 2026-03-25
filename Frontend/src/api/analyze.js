export function getApiBaseUrl() {
  const base = import.meta.env.VITE_API_BASE_URL;
  if (!base) return '';
  return base.replace(/\/+$/, '');
}

/**
 * POST /api/analyze
 * Form fields: file (required image), optional reference (image), optional manifest (PDF).
 */
export async function analyzeScan({ file, reference, manifest }) {
  const base = getApiBaseUrl();
  const url = `${base}/api/analyze`;

  const form = new FormData();
  if (file) {
    form.append('file', file);
  }
  if (reference) {
    form.append('reference', reference);
  }
  if (manifest) {
    form.append('manifest', manifest);
  }

  const res = await fetch(url, {
    method: 'POST',
    body: form,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || `Analyze request failed (${res.status})`);
  }

  return await res.json();
}
