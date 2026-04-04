const STORAGE_KEY = 'pixel_transactions_v1';

function loadAll() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function persist(map) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  } catch {
    /* quota or private mode */
  }
}

export function generateTransactionId() {
  const part = () => Math.random().toString(36).slice(2, 8);
  return `TXN-${Date.now().toString(36).toUpperCase()}-${part()}`.toUpperCase();
}

export function saveTransaction(record) {
  const map = loadAll();
  map[record.id] = { ...record, savedAt: new Date().toISOString() };
  persist(map);
  return record.id;
}

export function getTransactionById(id) {
  if (!id || typeof id !== 'string') return null;
  const map = loadAll();
  return map[id.trim()] ?? null;
}

export function listRecentTransactions(limit = 20) {
  const map = loadAll();
  return Object.values(map)
    .sort((a, b) => String(b.savedAt).localeCompare(String(a.savedAt)))
    .slice(0, limit);
}
