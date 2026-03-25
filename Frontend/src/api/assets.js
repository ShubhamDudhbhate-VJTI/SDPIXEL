import { getApiBaseUrl } from './analyze';

function isLikelyUrl(value) {
  return /^https?:\/\//i.test(value) || /^data:/i.test(value) || /^blob:/i.test(value);
}

/**
 * Convert backend "file outputs" into a browser-loadable URL.
 *
 * Supported inputs:
 * - Full URL: "https://.../img.png" (returned as-is)
 * - Data URL: "data:image/png;base64,..." (returned as-is)
 * - File path/name: "outputs/out1.png" -> "{base}/api/files?path=outputs%2Fout1.png"
 */
export function resolveAssetUrl(value) {
  if (!value || typeof value !== 'string') return null;
  if (isLikelyUrl(value)) return value;

  const base = getApiBaseUrl();
  const clean = value.replace(/^\.?\//, '');
  const q = encodeURIComponent(clean);
  return `${base}/api/files?path=${q}`;
}

export function resolveAssetList(values) {
  if (!Array.isArray(values)) return [];
  return values.map(resolveAssetUrl).filter(Boolean);
}

