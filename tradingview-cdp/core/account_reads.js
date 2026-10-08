/**
 * account_reads.js - Settle flaky reads of the broker panel's account dropdown.
 *
 * Purpose:
 *   TradingView shows the account dropdown with a CSS toggle, and a read taken
 *   too early returns only some accounts. One short read used to be accepted as
 *   the full list, so a portfolio or trade sync silently skipped an account.
 *   A read is now accepted only when two consecutive reads agree; otherwise the
 *   most complete read seen is returned.
 *
 * Key Input Dependencies:
 *   None (the caller supplies the function that performs one read)
 *
 * Key Output Dependencies:
 *   None (returns the settled list of account display texts)
 */

const unique = list => [...new Set(list || [])];
const same = (a, b) => a.length === b.length && a.every(item => b.includes(item));

/**
 * Read the account list until two consecutive reads agree.
 *
 * @param {() => Promise<string[]>} readOnce One attempt at reading the dropdown
 * @param {{attempts?: number, wait?: () => Promise<void>}} [options]
 * @returns {Promise<string[]>} Settled list, or the longest read when none agree
 */
export async function settleAccountReads(readOnce, { attempts = 4, wait = async () => {} } = {}) {
  let best = [];
  let previous = null;
  for (let attempt = 0; attempt < attempts; attempt++) {
    const read = unique(await readOnce());
    if (read.length > best.length) best = read;
    if (read.length > 0 && previous && same(read, previous)) return read.length >= best.length ? read : best;
    previous = read;
    if (attempt < attempts - 1) await wait();
  }
  return best;
}
