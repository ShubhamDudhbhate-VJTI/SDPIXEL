import { getApiBaseUrl } from '../api/analyze';

const STORAGE_KEY = 'pixel_transactions_v1';

/**
 * Get the backend API base URL — same as analyze.js (single source of truth).
 */
function apiBase() {
  return getApiBaseUrl() || '';
}

// ── LocalStorage Helpers ──────────────────────────────────────────────

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

// ── ID Generation ─────────────────────────────────────────────────────

export function generateTransactionId() {
  const part = () => Math.random().toString(36).slice(2, 8);
  return `TXN-${Date.now().toString(36).toUpperCase()}-${part()}`.toUpperCase();
}

// ── Save Transaction (async → Supabase, fallback → localStorage) ─────

export async function saveTransaction(record) {
  const id = record.id || generateTransactionId();
  const enrichedRecord = {
    ...record,
    id,
    savedAt: new Date().toISOString(),
    transaction_id: id,
  };

  // Extract risk data properly from the risk object
  const riskObj = record.risk || {};
  const riskScore = record.riskScore ?? record.risk_score ?? riskObj.score ?? null;
  const riskLevel = record.riskLevel ?? record.risk_level ?? riskObj.level ?? riskObj.decision ?? null;

  // Always save to localStorage first (guaranteed to work)
  const map = loadAll();
  map[id] = enrichedRecord;
  persist(map);

  // Try to save to Supabase via backend API
  try {
    const payload = {
      transaction_id: id,
      request_id: record.requestId || record.request_id || null,
      container_id: record.containerId || record.container_id || null,
      risk_score: typeof riskScore === 'number' ? Math.round(riskScore) : null,
      risk_level: riskLevel || null,
      status: record.status || 'completed',
      metadata: record.metadata || {},
    };

    const response = await fetch(`${apiBase()}/api/transactions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.warn('Supabase transaction save failed:', errorText);
    } else {
      console.log('✓ Transaction saved to Supabase:', id);
    }
  } catch (error) {
    console.warn('Supabase save failed, localStorage-only:', error);
  }

  return id;
}

// ── Get Transaction By ID (sync — localStorage only) ──────────────────

export function getTransactionById(id) {
  if (!id || typeof id !== 'string') return null;
  return loadAll()[id.trim()] ?? null;
}

// ── List Recent Transactions (sync — localStorage only) ───────────────

export function listRecentTransactions(limit = 20) {
  const map = loadAll();
  return Object.values(map)
    .sort((a, b) => String(b.savedAt).localeCompare(String(a.savedAt)))
    .slice(0, limit);
}
