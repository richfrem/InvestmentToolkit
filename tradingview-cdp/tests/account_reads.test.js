/**
 * account_reads.test.js - Jest tests for settling flaky account-dropdown reads.
 *
 * Purpose:
 *   The broker panel's account dropdown sometimes renders only some accounts
 *   (TFSA without RRSP on 2026-10-08). Verifies that a read is only accepted
 *   once two reads agree, and that the most complete read wins otherwise.
 *
 * Key Input Dependencies:
 *   - ../core/account_reads.js
 *
 * Key Output Dependencies:
 *   None (reports test execution results to Jest runner console)
 */

import { describe, it, expect } from '@jest/globals';
import { settleAccountReads, switchWithRetry } from '../core/account_reads.js';

const TFSA = 'TFSA - 12345678';
const RRSP = 'RRSP - 87654321';
const reader = reads => { let i = 0; const fn = async () => reads[Math.min(i++, reads.length - 1)]; fn.calls = () => i; return fn; };
const noWait = async () => {};

describe('settleAccountReads', () => {
  it('accepts a read as soon as two consecutive reads agree', async () => {
    const read = reader([[TFSA, RRSP], [TFSA, RRSP], [TFSA]]);
    expect(await settleAccountReads(read, { wait: noWait })).toEqual([TFSA, RRSP]);
    expect(read.calls()).toBe(2);
  });

  it('does not accept a partial first read', async () => {
    const read = reader([[TFSA], [TFSA, RRSP], [TFSA, RRSP]]);
    expect(await settleAccountReads(read, { wait: noWait })).toEqual([TFSA, RRSP]);
  });

  it('returns the most complete read when reads never agree', async () => {
    const read = reader([[TFSA], [], [TFSA, RRSP], [RRSP]]);
    expect(await settleAccountReads(read, { attempts: 4, wait: noWait })).toEqual([TFSA, RRSP]);
    expect(read.calls()).toBe(4);
  });

  it('removes duplicates and returns an empty list when nothing is ever read', async () => {
    expect(await settleAccountReads(reader([[TFSA, TFSA], [TFSA]]), { wait: noWait })).toEqual([TFSA]);
    expect(await settleAccountReads(reader([[]]), { attempts: 3, wait: noWait })).toEqual([]);
  });
});

describe('switchWithRetry', () => {
  const noWait = async () => {};
  const deps = ({ open = false, rows = [{ switched: 'TFSA - 1' }] } = {}) => {
    const log = [];
    let isOpen = open;
    let i = 0;
    return {
      log,
      isOpen: async () => isOpen,
      toggle: async () => { log.push('toggle'); isOpen = !isOpen; },
      close: async () => { log.push('close'); isOpen = false; },
      selectRow: async () => { log.push('select'); return rows[Math.min(i++, rows.length - 1)]; },
    };
  };

  it('does not toggle a dropdown that is already open (a blind toggle would close it)', async () => {
    const d = deps({ open: true });
    expect(await switchWithRetry({ ...d, wait: noWait })).toEqual({ switched: 'TFSA - 1' });
    expect(d.log).toEqual(['select']);
  });

  it('opens a closed dropdown once before selecting', async () => {
    const d = deps({ open: false });
    expect(await switchWithRetry({ ...d, wait: noWait })).toEqual({ switched: 'TFSA - 1' });
    expect(d.log).toEqual(['toggle', 'select']);
  });

  it('closes and retries when the row is not found, then succeeds', async () => {
    const d = deps({ open: false, rows: [{ error: 'Account not found in dropdown: TFSA' }, { switched: 'TFSA - 1' }] });
    expect(await switchWithRetry({ ...d, wait: noWait })).toEqual({ switched: 'TFSA - 1' });
    expect(d.log).toEqual(['toggle', 'select', 'close', 'toggle', 'select']);
  });

  it('returns the last error after the attempts are used up', async () => {
    const d = deps({ rows: [{ error: 'Account not found in dropdown: TFSA' }] });
    const result = await switchWithRetry({ ...d, attempts: 3, wait: noWait });
    expect(result.error).toMatch(/not found in dropdown: TFSA/);
    expect(d.log.filter(x => x === 'select')).toHaveLength(3);
  });
});
