import { describe, it, expect } from 'vitest';
import { getBearerToken } from '../../src/services/questradeService.ts';

describe('Questrade Service Functions', () => {
  it('getBearerToken returns token object', async () => {
    const token = await getBearerToken();
    expect(token).toHaveProperty('access_token');
    expect(token).toHaveProperty('api_server');
  });
});
