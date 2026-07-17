// Deterministic, dependency-free mock LLM. It is NOT smart, but it is
// structured enough to exercise every stage of the pipeline end-to-end
// so the app is usable without any API keys.
//
// The mock inspects the prompt for well-known task markers emitted by the
// pipeline (planPrompt / claimExtractPrompt / synthPrompt / …) and returns
// a shape-appropriate response.

function pickKeywords(text, n = 6) {
  const stop = new Set(('a an the and or of to in on for with by from as at is are be was were '
    + 'this that these those it its it\'s we you they i what which who whom whose how why when '
    + 'about into over under between within without through against during before after above below')
    .split(/\s+/));
  const words = (text.toLowerCase().match(/[a-z][a-z0-9\-']{2,}/g) || [])
    .filter((w) => !stop.has(w));
  const freq = new Map();
  for (const w of words) freq.set(w, (freq.get(w) || 0) + 1);
  return Array.from(freq.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, n)
    .map(([w]) => w);
}

function extractQuestion(prompt) {
  const m = prompt.match(/RESEARCH QUESTION:\s*"?([^"\n]+)"?/i);
  return m ? m[1].trim() : '';
}

export function mockComplete(prompt) {
  // ---- Plan ------------------------------------------------------------
  if (/TASK:\s*PLAN/i.test(prompt)) {
    const q = extractQuestion(prompt);
    const kws = pickKeywords(q, 5);
    const queries = [
      q,
      ...(kws.length ? [`${kws.slice(0, 2).join(' ')} overview`] : []),
      ...(kws.length > 2 ? [`${kws.slice(0, 3).join(' ')} recent research`] : []),
      ...(kws.length ? [`${kws[0]} definition`] : []),
      ...(kws.length > 1 ? [`${kws.slice(0, 2).join(' ')} controversy OR criticism`] : []),
    ].filter(Boolean).slice(0, 5);
    return JSON.stringify({
      subtopics: kws.slice(0, 5),
      queries,
      angles: ['definition', 'current state', 'evidence', 'controversy', 'outlook'],
    });
  }

  // ---- Claim extraction ------------------------------------------------
  if (/TASK:\s*EXTRACT_CLAIMS/i.test(prompt)) {
    // Pull sentence-like fragments from the provided EVIDENCE block,
    // but strip out the <<SOURCE ...>> / <<END>> structural markers first.
    const ev = (prompt.split(/EVIDENCE:/i)[1] || '')
      .replace(/<<SOURCE[^>]*>>/g, '')
      .replace(/<<END>>/g, '')
      .replace(/^\s*SOURCE\s+https?:\/\/\S+.*$/gim, '')
      .replace(/^\s*TITLE:.*$/gim, '')
      .replace(/^\s*---+\s*$/gm, '');
    const sentences = ev
      .split(/(?<=[.!?])\s+/)
      .map((s) => s.replace(/\s+/g, ' ').trim())
      // heuristic: must look like a real sentence, not a URL/header line
      .filter((s) => s.length > 40 && s.length < 260)
      .filter((s) => !/^https?:\/\//i.test(s))
      .filter((s) => /[a-z]/.test(s) && / /.test(s))
      .slice(0, 8);
    const claims = sentences.map((text, i) => ({
      id: `c${i + 1}`,
      text,
      keywords: pickKeywords(text, 4),
    }));
    return JSON.stringify({ claims });
  }

  // ---- Gap analysis ----------------------------------------------------
  if (/TASK:\s*GAP_ANALYSIS/i.test(prompt)) {
    const q = extractQuestion(prompt);
    const kws = pickKeywords(q + ' ' + prompt.slice(-1500), 4);
    // Very simple heuristic: propose a couple of orthogonal follow-ups.
    return JSON.stringify({
      gaps: kws.length ? [
        `limitations of ${kws[0]}`,
        `${kws[0]} case study`,
      ] : [],
    });
  }

  // ---- Fact check ------------------------------------------------------
  if (/TASK:\s*FACT_CHECK/i.test(prompt)) {
    // Without a real LLM, treat the presence of multiple corroborating
    // snippets as support. The orchestrator computes an independent score
    // from source diversity, so this is mostly a passthrough.
    return JSON.stringify({ verdict: 'supported', rationale: 'Corroborated by multiple retrieved snippets (mock).', conflicts: [] });
  }

  // ---- Synthesis -------------------------------------------------------
  if (/TASK:\s*SYNTHESIZE/i.test(prompt)) {
    const q = extractQuestion(prompt);
    const ev = prompt.split(/EVIDENCE:/i)[1] || '';
    const bullets = ev
      .split(/\n+/)
      .map((s) => s.replace(/^[\s\-\d\.\)]+/, '').trim())
      .filter((s) => s.length > 60)
      .slice(0, 6);
    const body = bullets.map((b, i) => `- ${b} [S${(i % 5) + 1}]`).join('\n');
    return [
      `# Research report: ${q}`,
      '',
      '## Summary',
      `This report synthesizes findings across multiple independent sources to answer: **${q}**. Each supporting claim is cross-checked against at least two independent domains.`,
      '',
      '## Key findings',
      body || '- (no findings extracted)',
      '',
      '## Caveats',
      '- Report generated in mock LLM mode. Configure a real LLM provider in `.env` for higher-quality synthesis.',
    ].join('\n');
  }

  // ---- Default: echo shortened prompt ---------------------------------
  return '(mock) ' + prompt.slice(0, 200);
}
