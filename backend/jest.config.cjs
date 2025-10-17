/** @type {import('ts-jest').JestConfigWithTsJest} */
module.exports = {
  preset: 'ts-jest/presets/js-with-ts-esm',
  testEnvironment: 'node',
  extensionsToTreatAsEsm: ['.ts'],
  globals: {
    'ts-jest': {
      useESM: true,
    },
  },
  moduleNameMapper: {
    '^(\.{1,2}/.*)\.ts$': '$1',
  },
  transformIgnorePatterns: [
    '/node_modules/(?!axios)/',
  ],
  runner: 'jest-runner',
};
