import React from 'react';

const VERDICT_COLOR = {
  supported:   '#1f7a3a',
  contested:   '#b26a00',
  unsupported: '#9a1e1e',
  unverified:  '#5a5a5a',
};

export default function ClaimTable({ verified }) {
  if (!verified?.length) return null;
  return (
    <div className="claims">
      <h3>Claims &amp; verification</h3>
      <table>
        <thead>
          <tr>
            <th>Claim</th>
            <th>Verdict</th>
            <th>Conf.</th>
            <th>Indep. sources</th>
          </tr>
        </thead>
        <tbody>
          {verified.map((v, i) => (
            <tr key={i}>
              <td>
                <div className="claim-text">{v.claim.text}</div>
                {v.supporting?.length > 0 && (
                  <details>
                    <summary>{v.supporting.length} supporting</summary>
                    <ul>
                      {v.supporting.map((s, j) => (
                        <li key={j}>
                          <a href={s.url} target="_blank" rel="noreferrer">{s.host}</a>
                          <span className="claim-auth"> · auth {s.authority}</span>
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
                {v.conflicting?.length > 0 && (
                  <details>
                    <summary>{v.conflicting.length} conflicting</summary>
                    <ul>
                      {v.conflicting.map((s, j) => (
                        <li key={j}>
                          <a href={s.url} target="_blank" rel="noreferrer">{s.host}</a>
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </td>
              <td>
                <span className="verdict" style={{ background: VERDICT_COLOR[v.verdict] || '#555' }}>
                  {v.verdict}
                </span>
              </td>
              <td>{Math.round((v.confidence || 0) * 100)}%</td>
              <td>{v.independentHosts}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
