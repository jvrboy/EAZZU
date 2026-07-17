// Consensus scoring and conflict detection.
//
// Approach:
//   1. Represent each claim by its keyword set.
//   2. For every source document, count how many of the claim's keywords
//      appear in the document text/title/snippet.
//   3. A source SUPPORTS the claim if it clears a keyword-overlap threshold.
//   4. Independence: only count each host ONCE (dedupe by registrable host).
//   5. Confidence combines (a) independent-source count vs threshold and
//      (b) average domain authority of supporting sources.
//   6. If some sources match strong negation keywords near the claim topic,
//      flag them as conflicts.

import { hostOf, domainAuthority } from '../utils/domains.js';

const NEG_TOKENS = [
  'not ', 'no evidence', 'incorrect', 'false', 'debunked', 'refuted',
  'contrary', 'however', 'disputes', 'contradicts', 'myth',
];

function tokenize(s) {
  return (s || '')
    .toLowerCase()
    .match(/[a-z][a-z0-9\-']{2,}/g) || [];
}

function keywordSet(claim) {
  const explicit = Array.isArray(claim.keywords) ? claim.keywords : [];
  if (explicit.length >= 3) return new Set(explicit.map((k) => k.toLowerCase()));
  // Fall back to salient words from the claim text itself.
  const stop = new Set('a an the and or of to in on for with by from as at is are be was were this that these those it its we you they i what which who whom whose how why when about into over under between within without through against during before after above below can could should would may might will shall do does did done being been has have had'.split(/\s+/));
  const words = tokenize(claim.text).filter((w) => !stop.has(w));
  return new Set(words.slice(0, 8));
}

function overlapCount(docText, kwSet) {
  if (!docText) return 0;
  const t = docText.toLowerCase();
  let hits = 0;
  for (const k of kwSet) {
    if (t.includes(k)) hits++;
  }
  return hits;
}

function nearbyNegation(docText, kwSet) {
  if (!docText) return false;
  const t = docText.toLowerCase();
  for (const k of kwSet) {
    const idx = t.indexOf(k);
    if (idx < 0) continue;
    const window = t.slice(Math.max(0, idx - 80), idx + 80);
    if (NEG_TOKENS.some((n) => window.includes(n))) return true;
  }
  return false;
}

export function scoreClaim(claim, docs, { minSources = 2 } = {}) {
  const kwSet = keywordSet(claim);
  const kwCount = kwSet.size || 1;

  const perHost = new Map();
  const supporting = [];
  const conflicting = [];

  for (const d of docs) {
    const combined = `${d.title || ''}\n${d.description || ''}\n${d.snippet || ''}\n${d.text || ''}`;
    const hits = overlapCount(combined, kwSet);
    const overlapRatio = hits / kwCount;
    if (overlapRatio < 0.4) continue; // not enough topical overlap to count

    const host = hostOf(d.url);
    if (!host) continue;

    const record = {
      url: d.url,
      title: d.title,
      host,
      authority: domainAuthority(d.url),
      overlap: +overlapRatio.toFixed(2),
      score: d.score ?? domainAuthority(d.url),
    };

    if (nearbyNegation(combined, kwSet)) {
      conflicting.push(record);
      continue;
    }

    // Keep only the STRONGEST document per host to enforce independence.
    const existing = perHost.get(host);
    if (!existing || record.score > existing.score) {
      perHost.set(host, record);
    }
  }

  for (const r of perHost.values()) supporting.push(r);

  const independentHosts = supporting.length;
  const avgAuthority = supporting.length
    ? supporting.reduce((s, r) => s + r.authority, 0) / supporting.length
    : 0;
  const avgOverlap = supporting.length
    ? supporting.reduce((s, r) => s + r.overlap, 0) / supporting.length
    : 0;

  // Confidence: 60% independence coverage, 30% authority, 10% overlap depth.
  const coverage = Math.min(1, independentHosts / Math.max(minSources, 1));
  const confidence = +(0.6 * coverage + 0.3 * avgAuthority + 0.1 * avgOverlap).toFixed(3);

  let verdict = 'unverified';
  if (independentHosts >= minSources && avgAuthority >= 0.55) verdict = 'supported';
  if (conflicting.length && conflicting.length >= supporting.length) verdict = 'contested';
  if (independentHosts === 0) verdict = 'unsupported';

  return {
    claim,
    verdict,
    confidence,
    independentHosts,
    supporting: supporting.sort((a, b) => b.score - a.score).slice(0, 6),
    conflicting: conflicting.slice(0, 4),
  };
}

export function verifyAll(claims, docs, opts = {}) {
  return claims.map((c) => scoreClaim(c, docs, opts));
}
