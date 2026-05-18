import { computeScenario } from './src/utils/valuationMath.ts';
import fs from 'fs';

const input = JSON.parse(fs.readFileSync(0, 'utf8'));

const results = {
    bear: computeScenario(input.revenue, input.shares, input.discountRate, input.horizon, input.scenarios.bear),
    base: computeScenario(input.revenue, input.shares, input.discountRate, input.horizon, input.scenarios.base),
    bull: computeScenario(input.revenue, input.shares, input.discountRate, input.horizon, input.scenarios.bull),
};

const weightedFairValue = Math.round(
    (results.bear.presentValue * input.scenarios.bear.weight +
     results.base.presentValue * input.scenarios.base.weight +
     results.bull.presentValue * input.scenarios.bull.weight) * 100
) / 100;

console.log(JSON.stringify({
    weightedFairValue,
    scenarios: results
}));
