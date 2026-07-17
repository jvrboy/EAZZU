// Stage 1: Plan. Ask the LLM to break the research question into subtopics
// and generate 3–5 diverse search queries.

import { json } from '../llm/index.js';

const PROMPT = (question) => `TASK: PLAN

You are a senior research planner. Break the research question into subtopics
and generate a small set of diverse web-search queries that together will
cover the topic comprehensively. Include at least one query that targets
recent developments and one that targets criticisms or counter-evidence.

RESEARCH QUESTION: "${question}"

Return JSON of the form:
{
  "subtopics": ["...", "..."],
  "queries":   ["...", "...", "..."],
  "angles":    ["definition", "current state", "evidence", "controversy", "outlook"]
}`;

export async function plan(question, bus) {
  bus.emitEvent('stage:start', { stage: 'plan' });
  const result = await json(PROMPT(question), { temperature: 0.3, maxTokens: 500 });

  // Guardrails / defaults
  const queries = Array.isArray(result?.queries) && result.queries.length
    ? result.queries.slice(0, 6)
    : [question];
  const subtopics = Array.isArray(result?.subtopics) ? result.subtopics.slice(0, 8) : [];

  bus.emitEvent('stage:done', { stage: 'plan', queries, subtopics });
  return { queries, subtopics };
}
