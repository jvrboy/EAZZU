// Crossref works API. No key required. Indexes scholarly publications.

import { fetchJson } from '../utils/fetcher.js';
import { logger } from '../utils/logger.js';

export const name = 'crossref';

export async function search(query, { limit = 5 } = {}) {
  const url =
    `https://api.crossref.org/works?query=${encodeURIComponent(query)}` +
    `&rows=${limit}&select=DOI,title,abstract,issued,URL,container-title,author`;
  try {
    const data = await fetchJson(url, {
      headers: { 'user-agent': 'DeepResearchJS/1.0 (mailto:research@example.local)' },
    });
    const items = data?.message?.items || [];
    return items.map((it) => {
      const title = Array.isArray(it.title) ? it.title[0] : (it.title || 'Untitled');
      const container = Array.isArray(it['container-title']) ? it['container-title'][0] : '';
      const year = it.issued?.['date-parts']?.[0]?.[0];
      const abstract = (it.abstract || '').replace(/<[^>]+>/g, '').trim();
      return {
        url: it.URL || (it.DOI ? `https://doi.org/${it.DOI}` : ''),
        title,
        snippet: abstract ? abstract.slice(0, 400) : `${container}${year ? `, ${year}` : ''}`,
        publishedAt: year ? `${year}-01-01` : null,
        source: 'crossref',
      };
    }).filter((r) => r.url);
  } catch (err) {
    logger.warn('crossref search failed', { query, err: String(err) });
    return [];
  }
}
