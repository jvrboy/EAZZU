# Deep Research JS

A pipeline-driven deep research application built in JavaScript. It performs multi-source web research, cross-verifies claims across independent sources, and produces a synthesized, cited report.

## Highlights

- **Pipeline architecture** — every stage is a discrete, observable module
- **Multi-source** — DuckDuckGo, Wikipedia, arXiv, Crossref (no API keys required)
- **High accuracy** — claim extraction → per-claim re-search → consensus scoring, ≥2 independent sources required, weighted by domain authority + recency
- **Provider-agnostic LLM** — plug in OpenAI, Anthropic, Ollama, or run in mock mode
- **Iterative refinement** — gap analysis loop re-searches missing angles until confidence threshold reached
- **Streaming dashboard** — React UI shows every pipeline step live via Server-Sent Events

## Pipeline stages

```
 ┌──────┐   ┌────────┐   ┌───────┐   ┌─────────┐   ┌────────┐   ┌────────┐   ┌────────────┐   ┌───────────┐   ┌──────┐
 │ Plan │──▶│ Search │──▶│ Fetch │──▶│ Extract │──▶│ Verify │──▶│ Refine │──▶│ Fact-check │──▶│ Synthesize│──▶│ Cite │
 └──────┘   └────────┘   └───────┘   └─────────┘   └────────┘   └───┬────┘   └────────────┘   └───────────┘   └──────┘
                                                                    │ (gaps found)
                                                                    └──────── loop back to Search
```

## Quick start

```bash
# 1. Backend
cd server
npm install
cp .env.example .env         # optionally add OPENAI_API_KEY etc.
npm run dev                  # http://localhost:8787

# 2. Frontend (new terminal)
cd client
npm install
npm run dev                  # http://localhost:5173
```

Then open the dashboard, enter a research question, and watch the pipeline run live.

### CLI mode

```bash
cd server
node src/cli.js "What are the leading approaches to retrieval-augmented generation in 2025?"
```

## LLM configuration

Set one of the following in `server/.env`:

```
LLM_PROVIDER=openai        # openai | anthropic | ollama | mock
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# or
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-latest

# or
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
```

If no provider is configured, the system runs in **mock mode** using deterministic heuristics — enough to exercise the full pipeline end-to-end.

## Accuracy features

1. **Independent-source rule** — a claim is only accepted when supported by ≥2 sources from *different* domains
2. **Domain authority weighting** — a curated whitelist (nature.com, arxiv.org, nih.gov, reuters.com, wikipedia.org, …) plus TLD heuristics (.edu, .gov)
3. **Recency scoring** — publication date extracted from meta tags; older sources decay
4. **Claim-level re-search** — after synthesis, each key claim triggers a fresh targeted search; conflicting evidence is surfaced
5. **Gap analysis loop** — the planner inspects intermediate output, identifies missing angles, and re-runs search until coverage ≥ threshold or max-iterations reached
6. **Conflict reporting** — the final report includes a "Contested claims" section when sources disagree

## Project layout

```
deep-research/
├── server/                 Node.js backend
│   ├── src/
│   │   ├── pipeline/       Stage implementations
│   │   ├── sources/        DuckDuckGo, Wikipedia, arXiv, Crossref adapters
│   │   ├── llm/            Provider-agnostic LLM adapter
│   │   ├── verify/         Scoring, consensus, conflict detection
│   │   ├── utils/          fetch, extract, logger
│   │   ├── orchestrator.js Runs the pipeline
│   │   ├── server.js       Express + SSE
│   │   └── cli.js          Command-line entry
│   └── package.json
├── client/                 React (Vite) dashboard
│   └── src/
│       ├── components/     PipelineView, SourceList, Report, ClaimTable
│       ├── hooks/          useResearchStream (SSE consumer)
│       └── App.jsx
└── docs/                   Architecture notes
```

## License

MIT
