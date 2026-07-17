import { useCallback, useRef, useState } from 'react';

// Manages the lifecycle of a research run: POST to start, then subscribe
// to the SSE stream and accumulate events + final result.

export function useResearchStream() {
  const [runId, setRunId] = useState(null);
  const [events, setEvents] = useState([]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [running, setRunning] = useState(false);
  const esRef = useRef(null);

  const stop = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
    setRunning(false);
  }, []);

  const start = useCallback(async (question) => {
    setEvents([]);
    setResult(null);
    setError(null);
    setRunning(true);
    try {
      const res = await fetch('/api/research', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ question }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const { id } = await res.json();
      setRunId(id);

      const es = new EventSource(`/api/research/${id}/stream`);
      esRef.current = es;
      es.onmessage = (msg) => {
        try {
          const evt = JSON.parse(msg.data);
          setEvents((prev) => [...prev, evt]);
          if (evt.type === 'run:complete' || evt.type === 'stream:end') {
            if (evt.result) setResult(evt.result);
            setRunning(false);
            es.close();
          } else if (evt.type === 'run:error') {
            setError(evt.error || 'unknown error');
            setRunning(false);
            es.close();
          }
        } catch {}
      };
      es.onerror = () => {
        // The server closes cleanly at end-of-stream; treat as termination.
        if (esRef.current) {
          esRef.current.close();
          esRef.current = null;
        }
        setRunning(false);
      };
    } catch (err) {
      setError(String(err));
      setRunning(false);
    }
  }, []);

  return { runId, events, result, error, running, start, stop };
}
