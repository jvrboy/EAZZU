// Lightweight structured logger. Everything is JSON-friendly so it can also be
// forwarded straight into the SSE stream consumed by the dashboard.

const LEVELS = { debug: 10, info: 20, warn: 30, error: 40 };
const CURRENT = LEVELS[process.env.LOG_LEVEL || 'info'] ?? LEVELS.info;

function fmt(level, msg, meta) {
  const stamp = new Date().toISOString();
  const base = `[${stamp}] ${level.toUpperCase().padEnd(5)} ${msg}`;
  if (!meta || Object.keys(meta).length === 0) return base;
  try {
    return `${base} ${JSON.stringify(meta)}`;
  } catch {
    return `${base} [unserializable meta]`;
  }
}

function log(level, msg, meta) {
  if (LEVELS[level] < CURRENT) return;
  const line = fmt(level, msg, meta);
  if (level === 'error') console.error(line);
  else console.log(line);
}

export const logger = {
  debug: (m, meta) => log('debug', m, meta),
  info: (m, meta) => log('info', m, meta),
  warn: (m, meta) => log('warn', m, meta),
  error: (m, meta) => log('error', m, meta),
};
