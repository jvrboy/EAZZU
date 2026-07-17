// Stage 2: Search. Run every query across every source in parallel,
// then merge and rank.

import { multiSearch } from '../sources/index.js';
import { combinedSourceScore } from '../utils/domains.js';

export async function search(queries, bus) {
  bus.emitEvent('stage:start', { stage: 'search', queries });

  const perQueryResults = await Promise.all(
    queries.map(async (q) => {
      const r = await multiSearch(q, { limit: 12 });
      bus.emitEvent('search:query', {
        query: q,
        perSource: r.perSource.map((p) => ({ source: p.source, count: p.items.length })),
        merged: r.merged.length,
      });
      return { query: q, ...r };
    })
  );

  // Merge across queries, keeping track of which queries surfaced each URL
  // (multi-query corroboration is a mild independence signal).
  const byUrl = new Map();
  for (const { query, merged } of perQueryResults) {
    for (const item of merged) {
      const prev = byUrl.get(item.url);
      if (prev) {
        prev.foundBy = Array.from(new Set([...prev.foundBy, ...item.foundBy]));
        prev.queries = Array.from(new Set([...(prev.queries || []), query]));
      } else {
        byUrl.set(item.url, { ...item, queries: [query] });
      }
    }
  }

  const candidates = Array.from(byUrl.values()).map((c) => ({
    ...c,
    preScore: combinedSourceScore(c.url, c.publishedAt),
  }));

  candidates.sort((a, b) => {
    // Prefer items surfaced by multiple sources, then higher authority.
    const ad = (a.foundBy?.length || 0);
    const bd = (b.foundBy?.length || 0);
    if (ad !== bd) return bd - ad;
    return b.preScore - a.preScore;
  });

  bus.emitEvent('stage:done', { stage: 'search', candidateCount: candidates.length });
  return candidates.slice(0, 24); // cap before fetch stage
}
