import { expect } from 'chai';
import fs from 'fs';
import path from 'path';
import {
    ACCEPTED_LIFECYCLE_STATUSES, INACTIVE_STATUSES, LIFECYCLE_STATUSES,
} from '../../src/utils/lifecycle';

function pythonSet(name: string): string[] {
    const source = fs.readFileSync(path.resolve(__dirname, '../../py_services/portfolio_io.py'), 'utf8');
    const match = new RegExp(`${name} = frozenset\\(\\{([^}]*)\\}\\)`).exec(source);
    if (!match) throw new Error(`${name} not found in portfolio_io.py`);
    return match[1].split(',').map(s => s.trim().replace(/['"]/g, '')).filter(Boolean).sort();
}

describe('lifecycle vocabulary', () => {
    it('matches py_services/portfolio_io.py LIFECYCLE_STATUSES', () => {
        expect([...LIFECYCLE_STATUSES].sort()).to.deep.equal(pythonSet('LIFECYCLE_STATUSES'));
    });

    it('matches py_services/portfolio_io.py INACTIVE_STATUSES', () => {
        expect([...INACTIVE_STATUSES].sort()).to.deep.equal(pythonSet('INACTIVE_STATUSES'));
    });

    it('accepts exactly the writer statuses plus the inactive ones', () => {
        const union = new Set<string>([...LIFECYCLE_STATUSES, ...INACTIVE_STATUSES]);
        expect([...ACCEPTED_LIFECYCLE_STATUSES].sort()).to.deep.equal([...union].sort());
    });
});
