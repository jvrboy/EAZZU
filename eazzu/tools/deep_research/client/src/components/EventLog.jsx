import React, { useEffect, useRef } from 'react';

export default function EventLog({ events }) {
  const boxRef = useRef(null);
  useEffect(() => {
    if (boxRef.current) boxRef.current.scrollTop = boxRef.current.scrollHeight;
  }, [events.length]);

  return (
    <div className="event-log" ref={boxRef}>
      {events.map((e, i) => (
        <div key={i} className={`event event-${e.type.split(':')[0]}`}>
          <span className="event-time">
            {new Date(e.ts).toLocaleTimeString([], { hour12: false })}
          </span>
          <span className="event-type">{e.type}</span>
          <span className="event-payload">{summarize(e)}</span>
        </div>
      ))}
      {events.length === 0 && <div className="event-empty">No events yet.</div>}
    </div>
  );
}

function summarize(e) {
  const { type, ts, ...rest } = e;
  const s = JSON.stringify(rest);
  return s.length > 240 ? s.slice(0, 240) + '…' : s;
}
