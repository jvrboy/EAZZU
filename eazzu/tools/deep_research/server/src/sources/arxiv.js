// arXiv Atom API. No key required. Great for CS / physics / math queries.

import * as cheerio from 'cheerio';
import { fetchUrl } from '../utils/fetcher.js';
import { logger } from '../utils/logger.js';

export const name = 'arxiv';

export async function search(query, { limit = 5 } = {}) {
  const url =
    `http://export.arxiv.org/api/query?search_query=all:${encodeURIComponent(query)}` +
    `&start=0&max_results=${limit}`;
  try {
    const { body } = await fetchUrl(url);
    const $ = cheerio.load(body, { xmlMode: true });
    const out = [];
    $('entry').each((_, el) => {
      const title = $(el).find('title').text().trim().replace(/\s+/g, ' ');
      const summary = $(el).find('summary').text().trim().replace(/\s+/g, ' ');
      const link = $(el)
        .find('link[rel="alternate"], link[type="text/html"]')
        .first()
        .attr('href') || $(el).find('id').text().trim();
      const published = $(el).find('published').text().trim();
      if (!link || !title) return;
      out.push({
        url: link,
        title,
        snippet: summary.slice(0, 400),
        publishedAt: published || null,
        source: 'arxiv',
      });
    });
    return out;
  } catch (err) {
    logger.warn('arxiv search failed', { query, err: String(err) });
    return [];
  }
}
