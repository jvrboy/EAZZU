// Stage 3: Fetch. Download each candidate URL with bounded concurrency.

import pLimit from 'p-limit';
import { fetchUrl } from '../utils/fetcher.js';
import { logger } from '../utils/logger.js';

const CONCURRENCY = Number(process.env.FETCH_CONCURRENCY || 5);

export async function fetchAll(candidates, bus) {
  bus.emitEvent('stage:start', { stage: 'fetch', total: candidates.length });
  const limit = pLimit(CONCURRENCY);
  let done = 0;

  const docs = await Promise.all(
    candidates.map((c) =>
      limit(async () => {
        try {
          const r = await fetchUrl(c.url, { retries: 1 });
          done++;
          bus.emitEvent('fetch:item', { url: c.url, status: r.status, done, total: candidates.length });
          return { ...c, html: r.body, contentType: r.contentType, status: r.status };
        } catch (err) {
          done++;
          logger.debug('fetch failed', { url: c.url, err: String(err) });
          bus.emitEvent('fetch:item', { url: c.url, status: 'error', done, total: candidates.length });
          return null;
        }
      })
    )
  );

  const ok = docs.filter(Boolean);
  bus.emitEvent('stage:done', { stage: 'fetch', ok: ok.length, failed: candidates.length - ok.length });
  return ok;
}
