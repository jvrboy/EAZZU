// DuckDuckGo HTML endpoint scraper — no API key required.
// Uses the `html.duckduckgo.com` endpoint which returns server-rendered results.

import * as cheerio from 'cheerio';
import { fetchUrl } from '../utils/fetcher.js';
import { logger } from '../utils/logger.js';

export const name = 'duckduckgo';

function decodeDdgHref(href) {
  // DDG wraps outbound links as //duckduckgo.com/l/?uddg=<encoded>&rut=...
  try {
    const u = new URL(href, 'https://duckduckgo.com');
    const uddg = u.searchParams.get('uddg');
    return uddg ? decodeURIComponent(uddg) : href;
  } catch {
    return href;
  }
}

export async function search(query, { limit = 6 } = {}) {
  const url = `https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}`;
  try {
    const { body } = await fetchUrl(url, { retries: 1 });
    const $ = cheerio.load(body);
    const results = [];
    $('.result').each((_, el) => {
      if (results.length >= limit) return;
      const a = $(el).find('a.result__a').first();
      const link = a.attr('href');
      const title = a.text().trim();
      const snippet = $(el).find('.result__snippet').text().trim();
      if (!link || !title) return;
      const cleanUrl = decodeDdgHref(link);
      if (!/^https?:\/\//i.test(cleanUrl)) return;
      results.push({ url: cleanUrl, title, snippet, source: 'duckduckgo' });
    });
    return results;
  } catch (err) {
    logger.warn('duckduckgo search failed', { query, err: String(err) });
    return [];
  }
}
