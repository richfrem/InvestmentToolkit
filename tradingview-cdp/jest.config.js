/**
 * jest.config.js - Jest testing configuration for Node environment.
 * 
 * Purpose:
 *   Configures test environment, transformers, and match patterns for Jest testing framework.
 * 
 * Key Input Dependencies:
 *   None
 * 
 * Key Output Dependencies:
 *   None
 */

export default {
  testEnvironment: 'node',
  transform: {},
  testMatch: ['**/tests/**/*.test.js'],
};
