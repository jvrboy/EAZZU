import React, { useMemo } from 'react';
import { marked } from 'marked';

export default function Report({ result }) {
  const html = useMemo(() => {
    if (!result?.report) return '';
    return marked.parse(result.report, { breaks: true });
  }, [result?.report]);

  if (!result) return null;
  return (
    <div className="report">
      <div className="report-stats">
        <span>⏱ {(result.stats.elapsedMs / 1000).toFixed(1)}s</span>
        <span>📄 {result.stats.docCount} docs</span>
        <span>✅ {result.stats.supported} supported</span>
        <span>⚖️ {result.stats.contested} contested</span>
        <span>🎯 {Math.round(result.stats.confidence * 100)}% confidence</span>
        <span>🔁 {result.stats.refineIterations} refine loops</span>
      </div>
      <div className="report-markdown" dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  );
}
