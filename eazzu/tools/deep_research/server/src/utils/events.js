// Simple EventEmitter wrapper used by the orchestrator to fan pipeline
// progress out to the HTTP layer (SSE) and to the CLI printer.

import { EventEmitter } from 'node:events';

export function createRunBus() {
  const bus = new EventEmitter();
  bus.setMaxListeners(50);

  // Convenience: emit a typed event with a timestamp so consumers can order.
  bus.emitEvent = (type, payload = {}) => {
    bus.emit('event', { type, ts: Date.now(), ...payload });
  };

  return bus;
}
