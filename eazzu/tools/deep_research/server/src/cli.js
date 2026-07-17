#!/usr/bin/env node
// CLI entry: `node src/cli.js "your research question"`
// Streams pipeline events to the terminal and prints the final report.

import 'dotenv/config';
import { createRunBus } from './utils/events.js';
import { runResearch } from './orchestrator.js';

const question = process.argv.slice(2).join(' ').trim();
if (!question) {
  console.error('usage: node src/cli.js "your research question"');
  process.exit(1);
}

const bus = createRunBus();
bus.on('event', (evt) => {
  const { type, ts, ...rest } = evt;
  const t = new Date(ts).toISOString().slice(11, 19);
  console.log(`[${t}] ${type.padEnd(18)} ${JSON.stringify(rest)}`);
});

try {
  const result = await runResearch(question, bus);
  console.log('\n' + '='.repeat(72));
  console.log(result.report);
  console.log('='.repeat(72));
  console.log('\nStats:', JSON.stringify(result.stats, null, 2));
} catch (err) {
  console.error('research failed:', err);
  process.exit(1);
}
