export function getApiBaseUrl() {
  const base = import.meta.env.VITE_API_BASE_URL;
  if (!base) return '';
  return base.replace(/\/+$/, '');
}

export async function analyzeScan({ file }) {
  const base = getApiBaseUrl();
  const url = `${base}/api/analyze`;

  const form = new FormData();
  form.append('file', file);

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

