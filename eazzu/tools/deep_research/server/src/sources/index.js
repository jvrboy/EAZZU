// Registry of source adapters. Each adapter exports { name, search(query, opts) }.

import * as duckduckgo from './duckduckgo.js';
import * as wikipedia from './wikipedia.js';
import * as arxiv from './arxiv.js';
import * as crossref from './crossref.js';

export const SOURCES = [duckduckgo, wikipedia, arxiv, crossref];

// Run all sources in parallel and merge, de-duplicating by URL.
export async function multiSearch(query, opts = {}) {
  const perSource = Math.max(3, Math.ceil((opts.limit || 12) / SOURCES.length) + 1);
  const results = await Promise.all(
    SOURCES.map((s) =>
      s.search(query, { limit: perSource }).then(
        (r) => ({ source: s.name, items: r }),
        (err) => ({ source: s.name, items: [], error: String(err) })
      )
    )
  );

  const merged = new Map();
  for (const { items } of results) {
    for (const item of items) {
      if (!item.url) continue;
      // Prefer the first sighting but keep note of every source that surfaced it.
      const existing = merged.get(item.url);
      if (existing) {
        existing.foundBy = Array.from(new Set([...(existing.foundBy || []), item.source]));
      } else {
        merged.set(item.url, { ...item, foundBy: [item.source] });
      }
    }
  }

  return {
    perSource: results,
    merged: Array.from(merged.values()),
  };
}
