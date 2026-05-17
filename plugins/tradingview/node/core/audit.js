/**
 * audit.js — Structured trade audit trail
 *
 * Writes append-only JSON-lines audit records to a per-day log file under
 * plugins/tradingview/audit/. Each record captures one named event in the
 * order lifecycle so any trade can be reconstructed after the fact.
 *
 * Event sequence for a normal order:
 *   ORDER_REQUESTED → PREFLIGHT_PASSED → USER_CONFIRMED_PREFLIGHT →
 *   FORM_FILLED → USER_CONFIRMED_SUBMIT → ORDER_SUBMITTED → PORTFOLIO_SYNCED
 *
 * Blocked / failure events:
 *   PREFLIGHT_BLOCKED   — buying power insufficient or broker not connected
 *   SIZE_CAP_BLOCKED    — order value exceeds --max-order-value
 *   DATA_STALE_BLOCKED  — portfolio.json too old for safe trading
 *   DCF_CONFLICT_BLOCKED — buying a SELL-rated holding without override
 *   FORM_MISMATCH_ABORTED — verifyOrderForm() detected shares/price mismatch
 *   USER_CANCELLED      — user declined at CONFIRM prompt
 *   SUBMIT_FAILED       — order dialog click failed after submission attempt
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname  = path.dirname(__filename);

const AUDIT_DIR = path.resolve(__dirname, '../../audit');

function _auditPath() {
  const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
  return path.join(AUDIT_DIR, `orders-${today}.jsonl`);
}

function _ensureDir() {
  fs.mkdirSync(AUDIT_DIR, { recursive: true });
}

/**
 * appendAuditEvent(event, payload)
 *
 * Appends one JSON-lines record. Silently swallows write errors — the audit
 * trail must never be able to block a user-confirmed trade.
 *
 * @param {string} event  - Named lifecycle event (see list above)
 * @param {object} payload - Context: ticker, shares, account, prices, etc.
 */
export function appendAuditEvent(event, payload = {}) {
  try {
    _ensureDir();
    const record = {
      ts: new Date().toISOString(),
      event,
      ...payload,
    };
    fs.appendFileSync(_auditPath(), JSON.stringify(record) + '\n', 'utf8');
  } catch {
    // Never throw from audit — it is a side effect, not a gate
  }
}

/**
 * readTodayAudit()
 *
 * Returns all records from today's log as an array. Returns [] if none.
 */
export function readTodayAudit() {
  try {
    const raw = fs.readFileSync(_auditPath(), 'utf8');
    return raw.trim().split('\n').filter(Boolean).map(JSON.parse);
  } catch {
    return [];
  }
}
