import { expect } from 'chai';
import { ThesisSchema } from '../../src/utils/zod-schemas';
import { ThesisService } from '../../src/services/ThesisService';
import { DOMAIN_MODEL_DB_FILE } from '../../src/utils/paths';

describe('Zod Schemas Validation', () => {
    it('should successfully validate the production thesis ground truth (Wave 8: domain_model.sqlite, not target-portfolio.json)', async () => {
        // Allow a real SQLite backup so worktree tests never need private data
        // copied over their own DB or a connection to the live main database.
        const service = new ThesisService(undefined, process.env.TEST_DOMAIN_MODEL_DB ?? DOMAIN_MODEL_DB_FILE);
        const data = await service.getThesis('target-portfolio');
        expect(data).to.not.be.null;

        const parseResult = ThesisSchema.safeParse(data);

        if (!parseResult.success) {
            console.error('Validation Errors:', JSON.stringify(parseResult.error.format(), null, 2));
        }

        expect(parseResult.success).to.be.true;
    });
});
