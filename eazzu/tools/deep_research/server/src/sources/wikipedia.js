// Wikipedia via the official public REST + Action APIs. No key required.

import { fetchJson } from '../utils/fetcher.js';
import { logger } from '../utils/logger.js';

export const name = 'wikipedia';

export async function search(query, { limit = 5 } = {}) {
  const url =
    `https://en.wikipedia.org/w/api.php?action=query&list=search&format=json` +
    `&srsearch=${encodeURIComponent(query)}&srlimit=${limit}&origin=*`;
  try {
    const data = await fetchJson(url);
    const items = data?.query?.search || [];
    return items.map((it) => ({
      url: `https://en.wikipedia.org/wiki/${encodeURIComponent(it.title.replace(/ /g, '_'))}`,
      title: it.title,
      snippet: (it.snippet || '').replace(/<[^>]+>/g, ''),
      source: 'wikipedia',
    }));
  } catch (err) {
    logger.warn('wikipedia search failed', { query, err: String(err) });
    return [];
  }
}
