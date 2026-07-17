// Stage 9: Synthesize. Produce the final markdown report using only claims
// that passed verification. Includes citation numbers and a "Contested claims"
// section for disagreements.

import { complete } from '../llm/index.js';

const SYNTH_PROMPT = (question, evidence, contested) => `TASK: SYNTHESIZE

You are writing a rigorous, well-cited research report. Use ONLY the evidence
provided below. Every substantive claim in the report MUST be followed by one
or more citation markers of the form [S1], [S2]… that correspond to the
numbered sources in the evidence block.

Structure:
1. "# Research report: <question>"
2. "## Summary" — 3–5 sentence executive summary.
3. "## Key findings" — bulleted, each ending with citation marker(s).
4. "## Contested claims" — include ONLY if provided; explain the disagreement.
5. "## Limitations" — briefly note gaps or uncertainties.

RESEARCH QUESTION: "${question}"

EVIDENCE:
${evidence}

${contested ? `CONTESTED CLAIMS:\n${contested}\n` : ''}
`;

export async function synthesize(question, factchecked, docs, bus) {
  bus.emitEvent('stage:start', { stage: 'synthesize' });

  // Build a numbered citation table from all supporting sources across all
  // supported claims (union, deduped by URL).
  const citationList = [];
  const urlToId = new Map();
  const supported = factchecked.filter((v) => v.verdict === 'supported');
  const contested = factchecked.filter((v) => v.verdict === 'contested');

  const registerSource = (s) => {
    if (urlToId.has(s.url)) return urlToId.get(s.url);
    const id = citationList.length + 1;
    urlToId.set(s.url, id);
    const doc = docs.find((d) => d.url === s.url);
    citationList.push({
      id,
      url: s.url,
      title: s.title || doc?.title || s.url,
      host: s.host,
      authority: s.authority,
      publishedAt: doc?.publishedAt || null,
    });
    return id;
  };

  const evidenceLines = [];
  for (const v of supported) {
    const ids = v.supporting.slice(0, 3).map(registerSource);
    evidenceLines.push(`- ${v.claim.text} ${ids.map((i) => `[S${i}]`).join(' ')}`);
  }

  const contestedLines = [];
  for (const v of contested) {
    const supIds = v.supporting.map(registerSource);
    const conIds = v.conflicting.map(registerSource);
    contestedLines.push(
      `- ${v.claim.text}\n  supported by: ${supIds.map((i) => `[S${i}]`).join(' ') || '(none)'}\n  disputed by: ${conIds.map((i) => `[S${i}]`).join(' ') || '(none)'}`
    );
  }

  const evidenceBlock = evidenceLines.join('\n') || '(no supported claims)';
  const contestedBlock = contestedLines.length ? contestedLines.join('\n') : '';

  const report = await complete(SYNTH_PROMPT(question, evidenceBlock, contestedBlock), {
    temperature: 0.2,
    maxTokens: 2000,
  });

  // Append citation list.
  const refs = citationList
    .map((c) => `- [S${c.id}] ${c.title} — ${c.url}${c.publishedAt ? ` (${c.publishedAt.slice(0, 10)})` : ''}`)
    .join('\n');

  const full = `${report.trim()}\n\n## Sources\n${refs || '(none)'}\n`;
  bus.emitEvent('stage:done', { stage: 'synthesize', citations: citationList.length });
  return { report: full, citations: citationList };
}
