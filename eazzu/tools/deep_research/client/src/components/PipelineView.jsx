import React from 'react';

const STAGES = [
  { key: 'plan',        label: 'Plan' },
  { key: 'search',      label: 'Search' },
  { key: 'fetch',       label: 'Fetch' },
  { key: 'extract',     label: 'Extract' },
  { key: 'verify',      label: 'Verify' },
  { key: 'refine',      label: 'Refine' },
  { key: 'factcheck',   label: 'Fact-check' },
  { key: 'synthesize',  label: 'Synthesize' },
];

// Compute a per-stage status from the event stream.
function stageStatus(events) {
  const s = {};
  for (const st of STAGES) s[st.key] = { state: 'pending', meta: {} };
  for (const e of events) {
    if (e.type === 'stage:start' && s[e.stage]) s[e.stage].state = 'running';
    if (e.type === 'stage:done' && s[e.stage])  { s[e.stage].state = 'done'; s[e.stage].meta = e; }
  }
  return s;
}

export default function PipelineView({ events, running }) {
  const statuses = stageStatus(events);
  return (
    <div className="pipeline">
      {STAGES.map((st, i) => {
        const s = statuses[st.key];
        return (
          <React.Fragment key={st.key}>
            <div className={`stage stage-${s.state}`}>
              <div className="stage-index">{i + 1}</div>
              <div className="stage-body">
                <div className="stage-label">{st.label}</div>
                <div className="stage-meta">
                  {s.state === 'pending' && '—'}
                  {s.state === 'running' && (running ? 'running…' : 'stopped')}
                  {s.state === 'done' && renderMeta(st.key, s.meta)}
                </div>
              </div>
            </div>
            {i < STAGES.length - 1 && <div className="stage-arrow">→</div>}
          </React.Fragment>
        );
      })}
    </div>
  );
}

function renderMeta(key, m) {
  switch (key) {
    case 'plan':       return `${(m.queries || []).length} queries`;
    case 'search':     return `${m.candidateCount ?? 0} candidates`;
    case 'fetch':      return `${m.ok ?? 0} ok / ${m.failed ?? 0} failed`;
    case 'extract':    return `${m.count ?? 0} docs`;
    case 'verify':     return `${m.supported ?? 0} supported, ${m.contested ?? 0} contested`;
    case 'refine':     return `${(m.gaps || []).length} gap queries`;
    case 'factcheck':  return `${m.supported ?? 0} confirmed`;
    case 'synthesize': return `${m.citations ?? 0} citations`;
    default:           return 'done';
  }
}
