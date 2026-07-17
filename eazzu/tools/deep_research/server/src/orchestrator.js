// Orchestrator: runs the full Plan → Search → Fetch → Extract → Verify
// → Refine (loop) → Fact-check → Synthesize pipeline, streaming events
// through the provided event bus.

import { plan } from './pipeline/plan.js';
import { search } from './pipeline/search.js';
import { fetchAll } from './pipeline/fetch.js';
import { extractAll } from './pipeline/extract.js';
import { verify } from './pipeline/verify.js';
import { refine } from './pipeline/refine.js';
import { factCheck } from './pipeline/factcheck.js';
import { synthesize } from './pipeline/synthesize.js';
import { currentProvider } from './llm/index.js';
import { logger } from './utils/logger.js';

const MAX_REFINE = Number(process.env.MAX_REFINE_ITERATIONS || 2);
const CONF_THRESHOLD = Number(process.env.CONFIDENCE_THRESHOLD || 0.7);

function overallConfidence(verified) {
  if (!verified.length) return 0;
  const supported = verified.filter((v) => v.verdict === 'supported');
  if (!supported.length) return 0;
  return supported.reduce((s, v) => s + v.confidence, 0) / supported.length;
}

export async function runResearch(question, bus) {
  const started = Date.now();
  bus.emitEvent('run:start', { question, llmProvider: currentProvider() });
  logger.info('research start', { question });

  // 1. Plan
  const { queries: initialQueries, subtopics } = await plan(question, bus);

  // 2-4. Search → Fetch → Extract (initial pass)
  let allQueries = [...initialQueries];
  let candidates = await search(initialQueries, bus);
  let rawDocs = await fetchAll(candidates, bus);
  let docs = await extractAll(rawDocs, bus);

  // 5. Verify (extract & score claims)
  let { claims, verified } = await verify(question, docs, bus);

  // 6. Refinement loop
  let iteration = 0;
  while (iteration < MAX_REFINE) {
    const conf = overallConfidence(verified);
    const supportedCount = verified.filter((v) => v.verdict === 'supported').length;
    bus.emitEvent('refine:assess', {
      iteration,
      confidence: +conf.toFixed(3),
      supported: supportedCount,
      threshold: CONF_THRESHOLD,
    });
    if (conf >= CONF_THRESHOLD && supportedCount >= 4) break;

    const gaps = await refine(question, verified, bus);
    if (!gaps.length) break;

    // Only run search on gap queries we haven't already tried.
    const newQueries = gaps.filter((q) => !allQueries.includes(q));
    if (!newQueries.length) break;
    allQueries.push(...newQueries);

    const extraCandidates = await search(newQueries, bus);
    // Skip already-fetched URLs.
    const known = new Set(docs.map((d) => d.url));
    const fresh = extraCandidates.filter((c) => !known.has(c.url));
    const extraDocs = await extractAll(await fetchAll(fresh, bus), bus);
    docs = [...docs, ...extraDocs].sort((a, b) => b.score - a.score);

    // Re-verify with the enlarged corpus.
    const rev = await verify(question, docs, bus);
    claims = rev.claims;
    verified = rev.verified;
    iteration++;
  }

  // 7. Claim-level fact-check with fresh, per-claim searches
  const { verified: factchecked } = await factCheck(verified, docs, bus);

  // 8. Synthesize final report
  const { report, citations } = await synthesize(question, factchecked, docs, bus);

  const result = {
    question,
    llmProvider: currentProvider(),
    subtopics,
    queries: allQueries,
    docs: docs.map((d) => ({
      url: d.url,
      title: d.title,
      publishedAt: d.publishedAt,
      score: d.score,
      wordCount: d.wordCount,
      foundBy: d.foundBy,
    })),
    verified: factchecked,
    citations,
    report,
    stats: {
      elapsedMs: Date.now() - started,
      docCount: docs.length,
      claimCount: factchecked.length,
      supported: factchecked.filter((v) => v.verdict === 'supported').length,
      contested: factchecked.filter((v) => v.verdict === 'contested').length,
      unsupported: factchecked.filter((v) => v.verdict === 'unsupported').length,
      confidence: +overallConfidence(factchecked).toFixed(3),
      refineIterations: iteration,
    },
  };

  bus.emitEvent('run:done', { stats: result.stats });
  logger.info('research done', result.stats);
  return result;
}
