// Stage 6: Refine. If coverage is below threshold, ask the LLM to identify
// gaps and produce additional targeted queries.

import { json } from '../llm/index.js';

const GAP_PROMPT = (question, verified) => {
  const weak = verified
    .filter((v) => v.verdict !== 'supported')
    .slice(0, 8)
    .map((v) => `- [${v.verdict}] ${v.claim.text}`)
    .join('\n');
  return `TASK: GAP_ANALYSIS

You are auditing an in-progress research report. Given the research question
and the list of claims that are NOT yet well-supported, propose 2–4 new
web-search queries that would help fill the gaps (each query should target
a specific missing angle or an authoritative source).

RESEARCH QUESTION: "${question}"

WEAK CLAIMS:
${weak || '(none)'}

Return JSON:
{ "gaps": ["query 1", "query 2"] }`;
};

export async function refine(question, verified, bus) {
  bus.emitEvent('stage:start', { stage: 'refine' });
  const r = await json(GAP_PROMPT(question, verified), { temperature: 0.3, maxTokens: 400 });
  const gaps = Array.isArray(r?.gaps) ? r.gaps.slice(0, 4) : [];
  bus.emitEvent('stage:done', { stage: 'refine', gaps });
  return gaps;
}
