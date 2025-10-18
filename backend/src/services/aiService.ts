// @ts-ignore - optional dependency; ensure OPENAI_API_KEY is set in env when using AI features
import OpenAI from 'openai';
import { logger } from '../utils/logger.ts';

const apiKey = process.env.OPENAI_API_KEY || '';
if (!apiKey) {
  logger.warn('OPENAI_API_KEY not set. AI features will be disabled.');
}

const client = new OpenAI({ apiKey });

export async function runChatCompletion(prompt: string, options: { maxTokens?: number; temperature?: number } = {}) {
  if (!apiKey) {
    // Friendly error to surface to callers
    throw new Error('OPENAI_API_KEY is not configured on the server. Set OPENAI_API_KEY in your .env to enable AI features.');
  }

  const max_tokens = options.maxTokens ?? Number(process.env.BACKEND_AI_MAX_TOKENS || 800);
  const temperature = options.temperature ?? Number(process.env.BACKEND_AI_TEMPERATURE || 0.2);
  logger.info('Calling OpenAI chat completion...');
  const model = process.env.CHAT_GPT_TRIAGE_MODEL || 'gpt-4o-mini';
  const res = await client.chat.completions.create({
    model,
    messages: [
      { role: 'system', content: 'You are a concise portfolio analyst.' },
      { role: 'user', content: prompt }
    ],
    max_tokens,
    temperature,
  });
  // The SDK can return multiple choices; concatenate content
  const content = (res.choices || []).map((c: any) => c.message?.content || '').join('\n\n');
  return content;
}

export default { runChatCompletion };
