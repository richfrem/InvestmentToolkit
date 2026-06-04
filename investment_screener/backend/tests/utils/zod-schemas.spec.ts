import { expect } from 'chai';
import fs from 'fs';
import path from 'path';
import { ThesisSchema } from '../../src/utils/zod-schemas';

describe('Zod Schemas Validation', () => {
    it('should successfully validate the production target-portfolio.json ground truth', () => {
        const targetPortfolioPath = path.resolve(__dirname, '../../data/theses/target-portfolio.json');
        expect(fs.existsSync(targetPortfolioPath)).to.be.true;

        const content = fs.readFileSync(targetPortfolioPath, 'utf-8');
        const data = JSON.parse(content);

        const parseResult = ThesisSchema.safeParse(data);
        
        if (!parseResult.success) {
            console.error('Validation Errors:', JSON.stringify(parseResult.error.format(), null, 2));
        }
        
        expect(parseResult.success).to.be.true;
    });
});
