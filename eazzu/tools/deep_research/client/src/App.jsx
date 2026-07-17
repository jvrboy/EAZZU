import React, { useState } from 'react';
import PipelineView from './components/PipelineView.jsx';
import EventLog from './components/EventLog.jsx';
import ClaimTable from './components/ClaimTable.jsx';
import Report from './components/Report.jsx';
import { useResearchStream } from './hooks/useResearchStream.js';

const EXAMPLES = [
  'What is retrieval-augmented generation and how does it improve LLM accuracy?',
  'What are the leading approaches to protein structure prediction in 2025?',
  'How effective are GLP-1 agonists for long-term weight loss?',
  'What is the current scientific consensus on room-temperature superconductors?',
];

export default function App() {
  const [question, setQuestion] = useState(EXAMPLES[0]);
  const { events, result, error, running, start } = useResearchStream();

  return (
    <div className="app">
      <header className="app-header">
        <h1>🔎 Deep Research</h1>
        <p className="tagline">Pipeline-driven, multi-source, cross-verified answers.</p>
      </header>

      <section className="query-panel">
        <textarea
          rows={3}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Enter a research question…"
          disabled={running}
        />
        <div className="query-actions">
          <div className="examples">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                className="example"
                onClick={() => setQuestion(ex)}
                disabled={running}
                type="button"
              >
                {ex.slice(0, 48)}…
              </button>
            ))}
          </div>
          <button
            className="run-btn"
            onClick={() => start(question.trim())}
            disabled={running || !question.trim()}
          >
            {running ? 'Researching…' : 'Run research'}
          </button>
        </div>
      </section>

      <section>
        <h2>Pipeline</h2>
        <PipelineView events={events} running={running} />
      </section>

      <div className="grid">
        <section>
          <h2>Live event log</h2>
          <EventLog events={events} />
        </section>
        <section>
          <h2>Verified claims</h2>
          {result ? <ClaimTable verified={result.verified} /> : (
            <p className="muted">Claims appear here once verification completes.</p>
          )}
        </section>
      </div>

      <section>
        <h2>Report</h2>
        {error && <div className="error">Error: {error}</div>}
        {result ? <Report result={result} /> : (
          <p className="muted">The synthesized report and citations will appear here.</p>
        )}
      </section>

      <footer>
        <small>
          LLM provider: <code>{result?.llmProvider || 'auto'}</code> · Sources:
          DuckDuckGo, Wikipedia, arXiv, Crossref
        </small>
      </footer>
    </div>
  );
}
