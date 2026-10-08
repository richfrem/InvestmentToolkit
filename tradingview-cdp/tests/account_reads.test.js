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
import { settleAccountReads } from '../core/account_reads.js';

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
