// Stage 4: Extract. Turn raw HTML into clean text + metadata and re-score
// with the (now-known) publication date.

import { extractFromHtml } from '../utils/extract.js';
import { combinedSourceScore } from '../utils/domains.js';

export async function extractAll(docs, bus) {
  bus.emitEvent('stage:start', { stage: 'extract', total: docs.length });
  const extracted = [];

  for (const d of docs) {
    try {
      if (d.contentType && d.contentType.includes('application/json')) {
        // JSON endpoints (e.g. crossref direct hits) — keep the snippet only.
        extracted.push({
          ...d,
          title: d.title,
          text: d.snippet || '',
          wordCount: (d.snippet || '').split(/\s+/).length,
          score: combinedSourceScore(d.url, d.publishedAt),
        });
        continue;
      }
      const ex = extractFromHtml(d.html || '', d.url);
      // If the extractor didn't find a date, fall back to any date the source
      // adapter already provided (arXiv/Crossref know their publication years).
      const publishedAt = ex.publishedAt || d.publishedAt || null;
      extracted.push({
        url: d.url,
        title: ex.title || d.title,
        description: ex.description,
        publishedAt,
        text: ex.text,
        wordCount: ex.wordCount,
        foundBy: d.foundBy,
        queries: d.queries,
        snippet: d.snippet,
        score: combinedSourceScore(d.url, publishedAt),
      });
    } catch {
      // skip broken extractions
    }
  }

  extracted.sort((a, b) => b.score - a.score);
  bus.emitEvent('stage:done', { stage: 'extract', count: extracted.length });
  return extracted;
}
