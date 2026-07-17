// Express server exposing:
//   POST /api/research        → { question } starts a run, returns { runId }
//   GET  /api/research/:id/stream (SSE)
//   GET  /api/research/:id    → final JSON result (once complete)
//   GET  /api/health

import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import { randomUUID } from 'node:crypto';
import { createRunBus } from './utils/events.js';
import { runResearch } from './orchestrator.js';
import { currentProvider } from './llm/index.js';
import { logger } from './utils/logger.js';

const PORT = Number(process.env.PORT || 8787);
const app = express();
app.use(cors());
app.use(express.json({ limit: '1mb' }));

// In-memory run registry. For a production deployment swap this for Redis
// or SQLite — the shape is small and self-contained.
const runs = new Map();

app.get('/api/health', (_req, res) => {
  res.json({ ok: true, llmProvider: currentProvider() });
});

app.post('/api/research', (req, res) => {
  const question = String(req.body?.question || '').trim();
  if (!question) return res.status(400).json({ error: 'question required' });
  const id = randomUUID();
  const bus = createRunBus();
  const state = {
    id,
    question,
    bus,
    events: [],
    result: null,
    error: null,
    startedAt: Date.now(),
    done: false,
  };
  bus.on('event', (evt) => state.events.push(evt));
  runs.set(id, state);

  // Fire-and-forget. Any error is captured on the state.
  runResearch(question, bus).then(
    (result) => {
      state.result = result;
      state.done = true;
      bus.emit('event', { type: 'run:complete', ts: Date.now() });
    },
    (err) => {
      state.error = String(err?.stack || err);
      state.done = true;
      logger.error('run failed', { id, err: state.error });
      bus.emit('event', { type: 'run:error', ts: Date.now(), error: String(err) });
    }
  );

  res.json({ id });
});

app.get('/api/research/:id', (req, res) => {
  const state = runs.get(req.params.id);
  if (!state) return res.status(404).json({ error: 'not found' });
  res.json({
    id: state.id,
    question: state.question,
    done: state.done,
    error: state.error,
    result: state.result,
  });
});

app.get('/api/research/:id/stream', (req, res) => {
  const state = runs.get(req.params.id);
  if (!state) return res.status(404).end();

  res.set({
    'content-type': 'text/event-stream',
    'cache-control': 'no-cache',
    connection: 'keep-alive',
    'x-accel-buffering': 'no',
  });
  res.flushHeaders?.();

  // Replay any events that already occurred.
  for (const evt of state.events) {
    res.write(`data: ${JSON.stringify(evt)}\n\n`);
  }
  if (state.done) {
    res.write(`data: ${JSON.stringify({ type: 'run:complete', ts: Date.now(), result: state.result, error: state.error })}\n\n`);
    return res.end();
  }

  const onEvent = (evt) => {
    res.write(`data: ${JSON.stringify(evt)}\n\n`);
    if (evt.type === 'run:complete' || evt.type === 'run:error') {
      res.write(`data: ${JSON.stringify({ type: 'stream:end', ts: Date.now(), result: state.result, error: state.error })}\n\n`);
      res.end();
    }
  };
  state.bus.on('event', onEvent);
  req.on('close', () => state.bus.off('event', onEvent));
});

app.listen(PORT, () => {
  logger.info(`deep-research server listening`, { port: PORT, llm: currentProvider() });
});
