// HTTP fetcher with timeout, User-Agent, and a small retry policy.
// Uses `undici` for connection pooling and modern HTTP handling.

import { request } from 'undici';
import { logger } from './logger.js';

const DEFAULT_UA =
  'Mozilla/5.0 (compatible; DeepResearchJS/1.0; +https://example.local/deep-research)';

const TIMEOUT = Number(process.env.FETCH_TIMEOUT_MS || 15000);

export async function fetchUrl(url, { retries = 1, headers = {} } = {}) {
  let lastErr;
  for (let attempt = 0; attempt <= retries; attempt++) {
    const ac = new AbortController();
    const timer = setTimeout(() => ac.abort(), TIMEOUT);
    try {
      const res = await request(url, {
        method: 'GET',
        headers: {
          'user-agent': DEFAULT_UA,
          accept: 'text/html,application/json;q=0.9,*/*;q=0.8',
          'accept-language': 'en-US,en;q=0.9',
          ...headers,
        },
        signal: ac.signal,
        maxRedirections: 5,
      });
      clearTimeout(timer);
      if (res.statusCode >= 400) {
        throw new Error(`HTTP ${res.statusCode} for ${url}`);
      }
      const contentType = res.headers['content-type'] || '';
      const body = await res.body.text();
      return { url, status: res.statusCode, contentType, body };
    } catch (err) {
      clearTimeout(timer);
      lastErr = err;
      logger.debug('fetch attempt failed', { url, attempt, err: String(err) });
      if (attempt < retries) {
        await new Promise((r) => setTimeout(r, 300 * (attempt + 1)));
      }
    }
  }
  throw lastErr;
}

export async function fetchJson(url, opts = {}) {
  const r = await fetchUrl(url, {
    ...opts,
    headers: { accept: 'application/json', ...(opts.headers || {}) },
  });
  return JSON.parse(r.body);
}
