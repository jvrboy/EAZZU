// Stage 5+7: Verify. Extracts candidate claims from the strongest evidence,
// then scores each claim against the entire source corpus.

import { json } from '../llm/index.js';
import { verifyAll } from '../verify/consensus.js';

const MIN_SOURCES = Number(process.env.MIN_SOURCES_PER_CLAIM || 2);

const CLAIM_PROMPT = (question, evidence) => `TASK: EXTRACT_CLAIMS

You are a careful research analyst. Read the EVIDENCE below and extract 6–10
concise, atomic factual claims that are directly relevant to the RESEARCH
QUESTION. Each claim should be a single self-contained assertion (not a
question, opinion, or vague statement). Attach 3–5 salient keywords.

RESEARCH QUESTION: "${question}"

EVIDENCE:
${evidence}

Return JSON:
{
  "claims": [
    { "id": "c1", "text": "...", "keywords": ["...","..."] },
    ...
  ]
}`;

function buildEvidenceBlock(docs, maxChars = 8000) {
  // Take top-scored docs, dump a short excerpt from each.
  // Use structured markers that the mock claim-extractor knows to skip.
  let out = '';
  for (const d of docs.slice(0, 8)) {
    const excerpt = (d.text || d.snippet || '').slice(0, 900);
    const chunk = `<<SOURCE url="${d.url}" title="${(d.title || '').replace(/"/g, "'")}">>\n${excerpt}\n<<END>>\n`;
    if (out.length + chunk.length > maxChars) break;
    out += chunk;
  }
  return out;
}

export async function verify(question, docs, bus) {
  bus.emitEvent('stage:start', { stage: 'verify' });

  const evidence = buildEvidenceBlock(docs);
  const extracted = await json(CLAIM_PROMPT(question, evidence), { temperature: 0.1, maxTokens: 1200 });
  const claims = Array.isArray(extracted?.claims) ? extracted.claims : [];
  bus.emitEvent('verify:claims', { count: claims.length });

  const verified = verifyAll(claims, docs, { minSources: MIN_SOURCES });
  const summary = {
    supported: verified.filter((v) => v.verdict === 'supported').length,
    contested: verified.filter((v) => v.verdict === 'contested').length,
    unsupported: verified.filter((v) => v.verdict === 'unsupported').length,
    unverified: verified.filter((v) => v.verdict === 'unverified').length,
  };
  bus.emitEvent('stage:done', { stage: 'verify', ...summary });
  return { claims, verified, summary };
}
