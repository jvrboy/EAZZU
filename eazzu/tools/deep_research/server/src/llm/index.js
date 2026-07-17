// Provider-agnostic LLM adapter. Exposes:
//   - complete(prompt, opts)  → string
//   - json(prompt, opts)      → parsed JSON (with retry / fenced-code stripping)
//
// Providers: openai | anthropic | ollama | mock
// Selection is driven by process.env.LLM_PROVIDER.

import { fetchUrl } from '../utils/fetcher.js';
import { logger } from '../utils/logger.js';
import { mockComplete } from './mock.js';

const PROVIDER = (process.env.LLM_PROVIDER || 'mock').toLowerCase();

async function openaiComplete(prompt, { temperature = 0.2, maxTokens = 1500, system } = {}) {
  const key = process.env.OPENAI_API_KEY;
  if (!key) throw new Error('OPENAI_API_KEY missing');
  const model = process.env.OPENAI_MODEL || 'gpt-4o-mini';
  const messages = [];
  if (system) messages.push({ role: 'system', content: system });
  messages.push({ role: 'user', content: prompt });

  const { body } = await fetchUrl('https://api.openai.com/v1/chat/completions', {
    headers: {
      authorization: `Bearer ${key}`,
      'content-type': 'application/json',
    },
    // undici fetchUrl uses GET by default; we need POST — use raw request instead.
    // (we shim via a tiny wrapper below)
  });
  throw new Error('openai transport not wired'); // placeholder — see openaiPost below
}

// We need POST support; the util fetcher is GET-only for simplicity, so we
// implement provider POSTs directly with undici.
import { request } from 'undici';

async function postJson(url, headers, payload, timeoutMs = 60000) {
  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), timeoutMs);
  try {
    const res = await request(url, {
      method: 'POST',
      headers: { 'content-type': 'application/json', ...headers },
      body: JSON.stringify(payload),
      signal: ac.signal,
    });
    const txt = await res.body.text();
    if (res.statusCode >= 400) {
      throw new Error(`LLM HTTP ${res.statusCode}: ${txt.slice(0, 400)}`);
    }
    return JSON.parse(txt);
  } finally {
    clearTimeout(timer);
  }
}

async function openai(prompt, { temperature = 0.2, maxTokens = 1500, system } = {}) {
  const key = process.env.OPENAI_API_KEY;
  if (!key) throw new Error('OPENAI_API_KEY missing');
  const model = process.env.OPENAI_MODEL || 'gpt-4o-mini';
  const messages = [];
  if (system) messages.push({ role: 'system', content: system });
  messages.push({ role: 'user', content: prompt });
  const data = await postJson(
    'https://api.openai.com/v1/chat/completions',
    { authorization: `Bearer ${key}` },
    { model, messages, temperature, max_tokens: maxTokens }
  );
  return data.choices?.[0]?.message?.content?.trim() || '';
}

async function anthropic(prompt, { temperature = 0.2, maxTokens = 1500, system } = {}) {
  const key = process.env.ANTHROPIC_API_KEY;
  if (!key) throw new Error('ANTHROPIC_API_KEY missing');
  const model = process.env.ANTHROPIC_MODEL || 'claude-3-5-sonnet-latest';
  const data = await postJson(
    'https://api.anthropic.com/v1/messages',
    {
      'x-api-key': key,
      'anthropic-version': '2023-06-01',
    },
    {
      model,
      max_tokens: maxTokens,
      temperature,
      system: system || undefined,
      messages: [{ role: 'user', content: prompt }],
    }
  );
  return (data.content || []).map((b) => b.text || '').join('').trim();
}

async function ollama(prompt, { temperature = 0.2, system } = {}) {
  const base = process.env.OLLAMA_BASE_URL || 'http://localhost:11434';
  const model = process.env.OLLAMA_MODEL || 'llama3.1';
  const data = await postJson(
    `${base.replace(/\/$/, '')}/api/generate`,
    {},
    { model, prompt: system ? `${system}\n\n${prompt}` : prompt, stream: false, options: { temperature } }
  );
  return (data.response || '').trim();
}

export async function complete(prompt, opts = {}) {
  try {
    switch (PROVIDER) {
      case 'openai':    return await openai(prompt, opts);
      case 'anthropic': return await anthropic(prompt, opts);
      case 'ollama':    return await ollama(prompt, opts);
      case 'mock':
      default:          return mockComplete(prompt, opts);
    }
  } catch (err) {
    logger.warn('LLM call failed, falling back to mock', { provider: PROVIDER, err: String(err) });
    return mockComplete(prompt, opts);
  }
}

function stripFences(s) {
  return s
    .replace(/^```(?:json)?\s*/i, '')
    .replace(/```$/i, '')
    .trim();
}

export async function json(prompt, opts = {}) {
  const raw = await complete(prompt, { ...opts, system: (opts.system || '') + '\n\nRespond with ONLY valid JSON. No prose, no code fences.' });
  const cleaned = stripFences(raw);
  try {
    return JSON.parse(cleaned);
  } catch {
    // Try to salvage the first {...} or [...] block.
    const m = cleaned.match(/(\{[\s\S]*\}|\[[\s\S]*\])/);
    if (m) {
      try { return JSON.parse(m[1]); } catch {}
    }
    logger.warn('LLM returned non-JSON', { snippet: cleaned.slice(0, 200) });
    return null;
  }
}

export function currentProvider() {
  return PROVIDER;
}
