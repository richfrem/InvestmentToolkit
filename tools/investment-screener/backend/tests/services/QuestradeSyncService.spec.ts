import { expect } from 'chai';
import { QuestradeSyncService } from '../../src/services/QuestradeSyncService';
import path from 'path';
import fs from 'fs';

/**
 * QuestradeSyncService.spec.ts
 * ===========================
 * 
 * Purpose:
 *   Verify the Node.js bridge can correctly trigger the Python engine
 *   and handle success/failure conditions.
 */

describe('QuestradeSyncService', () => {
    let service: QuestradeSyncService;

    beforeEach(() => {
        service = new QuestradeSyncService();
    });

    it('should be correctly initialized with script paths', () => {
        // Accessing private members via cast for testing paths
        const s = service as any;
        expect(s.constructor.PYTHON_SCRIPT_PATH).to.contain('QuestradeDataEngine.py');
        expect(fs.existsSync(s.constructor.PYTHON_SCRIPT_PATH)).to.be.true;
    });

    // Note: Integration test with actual Python execution would require 
    // valid tokens/keyring setup which might not be available in CI.
    // Here we focus on pathing and existence verification.
});
