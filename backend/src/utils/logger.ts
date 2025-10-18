/**
 * Simple logger utility with environment-controlled debugging
 * Set DEBUG_LOGGING=true in .env to enable debug logs
 */

const DEBUG_LOGGING = process.env.DEBUG_LOGGING === 'true';

export const logger = {
  debug: (message: string, ...args: any[]) => {
    if (DEBUG_LOGGING) {
      console.log(`🐛 DEBUG: ${message}`, ...args);
    }
  },

  info: (message: string, ...args: any[]) => {
    console.log(`ℹ️ INFO: ${message}`, ...args);
  },

  success: (message: string, ...args: any[]) => {
    console.log(`✅ SUCCESS: ${message}`, ...args);
  },

  warn: (message: string, ...args: any[]) => {
    console.warn(`⚠️ WARN: ${message}`, ...args);
  },

  error: (message: string, ...args: any[]) => {
    console.error(`❌ ERROR: ${message}`, ...args);
  },

  // Specific logging methods for different components
  api: (message: string, ...args: any[]) => {
    if (DEBUG_LOGGING) {
      console.log(`🌐 API: ${message}`, ...args);
    }
  },

  data: (message: string, ...args: any[]) => {
    if (DEBUG_LOGGING) {
      console.log(`📊 DATA: ${message}`, ...args);
    }
  },

  questrade: (message: string, ...args: any[]) => {
    if (DEBUG_LOGGING) {
      console.log(`🏦 QUESTRADE: ${message}`, ...args);
    }
  },

  portfolio: (message: string, ...args: any[]) => {
    if (DEBUG_LOGGING) {
      console.log(`📈 PORTFOLIO: ${message}`, ...args);
    }
  }
};