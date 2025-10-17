/**
 * Integration tests for Questrade API routes
 * Uses supertest to make HTTP requests to the running Express server
 */
import request from 'supertest';

// Adjust the import path to your Express app
import app from '../../src/index';

// Mock Questrade service functions to avoid real API calls
jest.mock('../../src/services/questradeService.ts', () => ({
  getBearerToken: jest.fn().mockResolvedValue({
    access_token: 'mock_access_token',
    api_server: 'https://mock.api/',
    refresh_token: 'mock_refresh_token',
  }),
  getAccounts: jest.fn().mockResolvedValue([
    {
      type: 'Individual',
      number: '123456',
      status: 'Active',
      isPrimary: true,
      isBilling: false,
      clientAccountType: 'Margin',
      userId: 'user1',
    },
  ]),
  getHoldings: jest.fn().mockResolvedValue([
    {
      symbol: 'AAPL',
      quantity: 10,
      bookValue: 1500,
      marketValue: 1700,
    },
  ]),
  getAllAccountData: jest.fn().mockResolvedValue({
    accounts: [
      {
        type: 'Individual',
        number: '123456',
        status: 'Active',
        isPrimary: true,
        isBilling: false,
        clientAccountType: 'Margin',
        userId: 'user1',
      },
    ],
    positions: [
      {
        symbol: 'AAPL',
        openQuantity: 10,
        averageEntryPrice: 150,
        currentMarketValue: 1700,
      },
    ],
    balances: [
      {
        currency: 'USD',
        cash: 1000,
      },
    ],
  }),
  getBalances: jest.fn().mockResolvedValue([
    {
      currency: 'USD',
      cash: 1000,
    },
  ]),
}));

describe('Questrade API Routes', () => {
  it('GET /questrade/accounts should get accounts', async () => {
  const res = await request(app).get('/api/questrade/accounts');
    expect(res.statusCode).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
  });

  it('GET /questrade/holdings should get holdings', async () => {
  const res = await request(app).get('/api/questrade/holdings');
    expect(res.statusCode).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
  });

  it('GET /questrade/refresh should get and return all data', async () => {
  const res = await request(app).get('/api/questrade/refresh');
    expect(res.statusCode).toBe(200);
    expect(res.body).toHaveProperty('success', true);
    expect(res.body).toHaveProperty('accounts');
    expect(res.body).toHaveProperty('positions');
    expect(res.body).toHaveProperty('balances');
  });

  // Add more route tests as needed (e.g., /balances if implemented)
});
