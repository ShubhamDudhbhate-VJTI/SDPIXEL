import * as pdfjs from 'pdfjs-dist/build/pdf';

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

async function fileToArrayBuffer(file) {
  return await file.arrayBuffer();
}

export async function extractPdfText(file) {
  const data = await fileToArrayBuffer(file);
  const doc = await pdfjs.getDocument({ data }).promise;

  const pages = [];
  for (let pageNum = 1; pageNum <= doc.numPages; pageNum += 1) {
    const page = await doc.getPage(pageNum);
    const content = await page.getTextContent();
    const text = content.items
      .map((item) => ('str' in item ? item.str : ''))
      .join(' ')
      .replace(/\s+/g, ' ')
      .trim();
    pages.push(text);
  }
  return pages.join('\n');
}

export function parseItemsFromText(text) {
  const rawLines = text
    .split(/\r?\n|•|\u2022/g)
    .map((l) => l.trim())
    .filter(Boolean);

  const candidates = rawLines
    .flatMap((line) => line.split(/[,;|]/g).map((p) => p.trim()))
    .map((line) => line.replace(/^\d+[).\-\s]+/, '').trim())
    .filter((line) => line.length >= 3 && line.length <= 60)
    .filter((line) => !/^(page|date|time|invoice|manifest|shipper|consignee)\b/i.test(line));

  const dedup = new Map();
  for (const item of candidates) {
    const key = item.toLowerCase();
    if (!dedup.has(key)) dedup.set(key, item);
  }
  return Array.from(dedup.values());
}

export async function extractManifestItemsFromPdf(file) {
  const text = await extractPdfText(file);
  const items = parseItemsFromText(text);
  return { text, items };
}

