import { expect } from 'chai';
import { ThesisSchema } from '../../src/utils/zod-schemas';
import { thesisService } from '../../src/services/ThesisService';

describe('Zod Schemas Validation', () => {
    it('should successfully validate the production thesis ground truth (Wave 8: domain_model.sqlite, not target-portfolio.json)', async () => {
        const data = await thesisService.getThesis('target-portfolio');
        expect(data).to.not.be.null;

        const parseResult = ThesisSchema.safeParse(data);

        if (!parseResult.success) {
            console.error('Validation Errors:', JSON.stringify(parseResult.error.format(), null, 2));
        }

        expect(parseResult.success).to.be.true;
    });
});
