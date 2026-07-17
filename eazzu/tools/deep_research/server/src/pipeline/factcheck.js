// Stage 8: Claim-level fact-check. For each *supported* claim we run a fresh,
// targeted search specifically for that claim and re-score consensus against
// the newly-retrieved evidence. This catches cases where the initial corpus
// was self-consistent but not representative of the wider web.

import { multiSearch } from '../sources/index.js';
import { scoreClaim } from '../verify/consensus.js';
import { combinedSourceScore } from '../utils/domains.js';
import { extractFromHtml } from '../utils/extract.js';
import { fetchUrl } from '../utils/fetcher.js';
import pLimit from 'p-limit';

const MIN_SOURCES = Number(process.env.MIN_SOURCES_PER_CLAIM || 2);
const CONCURRENCY = Number(process.env.FETCH_CONCURRENCY || 5);

async function evidenceForClaim(claim, existingDocs) {
  // Focused query: prefer the claim's own keywords if the LLM gave us any,
  // otherwise use the first sentence itself.
  const kws = Array.isArray(claim.keywords) && claim.keywords.length
    ? claim.keywords.slice(0, 5).join(' ')
    : claim.text.slice(0, 120);
  const q = kws;

  const { merged } = await multiSearch(q, { limit: 8 });

  // De-duplicate against docs we already have — no point re-fetching.
  const seen = new Set(existingDocs.map((d) => d.url));
  const fresh = merged.filter((r) => !seen.has(r.url)).slice(0, 6);

  const limit = pLimit(CONCURRENCY);
  const fetched = await Promise.all(fresh.map((r) => limit(async () => {
    try {
      const res = await fetchUrl(r.url, { retries: 1 });
      const ex = extractFromHtml(res.body, r.url);
      const publishedAt = ex.publishedAt || r.publishedAt || null;
      return {
        url: r.url,
        title: ex.title || r.title,
        snippet: r.snippet,
        text: ex.text,
        publishedAt,
        score: combinedSourceScore(r.url, publishedAt),
      };
    } catch { return null; }
  })));

  return fetched.filter(Boolean);
}

export async function factCheck(verified, existingDocs, bus) {
  bus.emitEvent('stage:start', { stage: 'factcheck', total: verified.length });

  // Only re-check claims that were tentatively supported or contested —
  // spending budget on 'unsupported' claims is wasteful because they will
  // be dropped from the report anyway.
  const targets = verified.filter((v) => v.verdict === 'supported' || v.verdict === 'contested');
  const others = verified.filter((v) => v.verdict !== 'supported' && v.verdict !== 'contested');

  const rescored = [];
  let i = 0;
  for (const v of targets) {
    i++;
    bus.emitEvent('factcheck:item', { i, total: targets.length, claim: v.claim.text.slice(0, 120) });
    const extra = await evidenceForClaim(v.claim, existingDocs);
    // Combine original supporting docs with fresh ones, then re-score.
    const combined = [
      ...existingDocs,
      ...extra,
    ];
    const rs = scoreClaim(v.claim, combined, { minSources: MIN_SOURCES });
    // Keep the more conservative verdict of the two passes.
    const finalVerdict =
      (v.verdict === 'contested' || rs.verdict === 'contested') ? 'contested' :
      (v.verdict === 'supported' && rs.verdict === 'supported') ? 'supported' :
      rs.verdict;
    rescored.push({
      ...rs,
      verdict: finalVerdict,
      // preserve the union of supporting evidence
      supporting: mergeSources(v.supporting, rs.supporting),
      conflicting: mergeSources(v.conflicting, rs.conflicting),
      confidence: +Math.min(1, (v.confidence * 0.4 + rs.confidence * 0.6)).toFixed(3),
    });
  }

  const merged = [...rescored, ...others];
  const summary = {
    supported: merged.filter((v) => v.verdict === 'supported').length,
    contested: merged.filter((v) => v.verdict === 'contested').length,
    unsupported: merged.filter((v) => v.verdict === 'unsupported').length,
    unverified: merged.filter((v) => v.verdict === 'unverified').length,
  };
  bus.emitEvent('stage:done', { stage: 'factcheck', ...summary });
  return { verified: merged, summary };
}

function mergeSources(a = [], b = []) {
  const byHost = new Map();
  for (const s of [...a, ...b]) {
    const prev = byHost.get(s.host);
    if (!prev || s.score > prev.score) byHost.set(s.host, s);
  }
  return Array.from(byHost.values()).sort((x, y) => y.score - x.score).slice(0, 8);
}
