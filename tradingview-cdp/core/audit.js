/**
 * audit.js - Structured trade audit trail.
 * 
 * Purpose:
 *   Writes append-only JSON-lines audit records to a per-day log file.
 *   Captures order lifecycle event sequence for trading verification and post-trade analysis.
 * 
 * Key Input Dependencies:
 *   None
 * 
 * Key Output Dependencies:
 *   - plugins/tradingview/audit/ (stores daily orders YYYY-MM-DD.jsonl audit trails)
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const filename = fileURLToPath(import.meta.url);
const dirname  = path.dirname(filename);

const auditDir = process.env.TV_AUDIT_DIR ? path.resolve(process.env.TV_AUDIT_DIR) : path.resolve(dirname, '../../plugins/tradingview/audit');

/**
 * Get the absolute file path for today's audit trail file.
 * 
 * @returns {string} File path to today's jsonl file
 */
function _auditPath() {
  /**
   * Generates a date string YYYY-MM-DD and joins it with the audit directory.
   */
  const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
  return path.join(auditDir, `orders-${today}.jsonl`);
}

/**
 * Ensure that the audit logs directory exists.
 */
function _ensureDir() {
  /**
   * Helper that creates the audit log directory recursively if missing.
   */
  fs.mkdirSync(auditDir, { recursive: true });
}

/**
 * Append one JSON-lines record to today's audit trail.
 *
 * Appends one JSON-lines record. Silently swallows write errors — the audit
 * trail must never be able to block a user-confirmed trade.
 *
 * @param {string} event - Named lifecycle event (e.g. ORDER_REQUESTED)
 * @param {object} payload - Context: ticker, shares, account, prices, etc.
 */
export function appendAuditEvent(event, payload = {}) {
  /**
   * Safely formats audit record with a timestamp, ensures the directory exists,
   * and appends it to the daily JSONL file. Swallows errors.
   */
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
 * Read all audit records written today.
 *
 * Returns all records from today's log as an array. Returns [] if none.
 * 
 * @returns {object[]} Parsed audit records array
 */
export function readTodayAudit() {
  /**
   * Attempts to read and split the JSONL file, parsing each line to an object.
   */
  try {
    const raw = fs.readFileSync(_auditPath(), 'utf8');
    return raw.trim().split('\n').filter(Boolean).map(JSON.parse);
  } catch {
    return [];
  }
}
