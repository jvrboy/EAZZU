# Architecture

## Design goals

1. **Deterministic pipeline** — every research run passes through the same
   discrete, testable stages. No monolithic "agent loop".
2. **Multi-source independence** — a claim is only considered supported when
   corroborated by ≥ N *independent* domains, not just N URLs from the same
   site.
3. **Streaming observability** — every stage emits typed events. The dashboard
   consumes them via SSE, the CLI prints them, and they can be persisted for
   audit trails.
4. **Provider-agnostic LLM** — a thin adapter abstracts OpenAI / Anthropic /
   Ollama / mock. Mock mode lets the whole system run without any key.

## Data flow

```
question
   │
   ▼
┌────────┐         ┌───────────────────────────────────────┐
│  plan  │─────────► queries[], subtopics[], angles[]      │
└───┬────┘         └───────────────────────────────────────┘
    │
    ▼
┌────────┐   for every (query × source):
│ search │   duckduckgo · wikipedia · arxiv · crossref
└───┬────┘   merge on URL, dedupe, rank by pre-score
    │
    ▼
┌────────┐   fetch each URL (bounded concurrency, retry, timeout)
│ fetch  │
└───┬────┘
    │
    ▼
┌────────┐   HTML → clean text + title + description + publishedAt
│ extract│   re-score with domain authority + recency
└───┬────┘
    │
    ▼
┌────────┐   LLM extracts atomic factual claims from top evidence
│ verify │   for each claim: keyword-overlap match against all docs,
│        │   dedupe by host, compute confidence, verdict
└───┬────┘
    │  ┌── if avg-confidence < threshold ───┐
    │  ▼                                    │
    │  ┌──────────────┐   gap queries       │
    │  │    refine    │ ────────────► search again
    │  └──────────────┘
    │
    ▼
┌────────────┐   for each still-supported/contested claim:
│ fact-check │     run a FRESH targeted search
│            │     merge new evidence, re-score consensus
│            │     conservative verdict (worst of two passes)
└─────┬──────┘
      ▼
┌────────────┐   LLM writes markdown report using ONLY supported
│ synthesize │   claims. Every bullet gets numbered citations.
│            │   Contested claims get their own section.
└─────┬──────┘
      ▼
   final report + citations + verified claims + stats
```

## Verification math

For each candidate claim `c` and each retrieved document `d`:

1. Build a keyword set from `c` (LLM-provided or extracted from the text).
2. Compute overlap ratio = `|kw ∩ tokens(d)| / |kw|`.
3. Documents with overlap ≥ 0.4 are candidate supporters.
4. Group supporters by **registrable host** and keep only the highest-scoring
   doc per host (this enforces *source independence*).
5. If a negation keyword ("not", "no evidence", "debunked", ...) appears
   within 80 chars of a matched keyword, the doc goes into `conflicting`
   instead.

Confidence is:

```
coverage    = min(1, independentHosts / MIN_SOURCES)
confidence  = 0.6 · coverage + 0.3 · avgAuthority + 0.1 · avgOverlap
```

Verdict rules:

| condition                                               | verdict     |
|---------------------------------------------------------|-------------|
| `independentHosts == 0`                                 | unsupported |
| `#conflicting >= #supporting`                           | contested   |
| `independentHosts >= MIN_SOURCES` and `avgAuthority≥0.55` | supported |
| otherwise                                               | unverified  |

## Domain authority

`utils/domains.js` combines:

- A curated whitelist (`nature.com: 0.95`, `arxiv.org: 0.85`, `reuters.com: 0.9`, …).
- TLD heuristics (`.gov: 0.9`, `.edu: 0.8`, `.ac.uk: 0.8`, `.org: 0.55`).
- A recency bonus (0–1) computed from publication date extracted during the
  extract stage or provided directly by the source adapter.

Final source score = `0.7·authority + 0.3·recency`.

## Failure modes and mitigations

| failure                                | mitigation                                                |
|----------------------------------------|-----------------------------------------------------------|
| DuckDuckGo HTML endpoint returns 202/blocks | Wikipedia/arXiv/Crossref keep the run alive             |
| arXiv rate-limits (HTTP 429)          | Warned + skipped; other sources continue                  |
| LLM API fails                          | Adapter automatically falls back to mock                  |
| LLM returns non-JSON                   | Salvage first `{…}` block, otherwise return `null` + defaults |
| Site blocks HTML fetch                 | Doc dropped; ranking backfills from lower-ranked candidates |
| Two sources of the SAME site agree     | Deduped by registrable host — counts as ONE independent source |

## Extending

- **New source**: implement `{ name, search(query, {limit}) → items[] }` in
  `server/src/sources/` and add it to `SOURCES` in `sources/index.js`.
- **New LLM provider**: add a function to `server/src/llm/index.js` and route
  it in the `switch (PROVIDER)` block.
- **New pipeline stage**: create a module exposing `async fn(inputs, bus)` and
  wire it into `orchestrator.js`.
