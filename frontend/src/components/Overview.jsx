import { useMemo, useState } from "react";

export default function Overview({ summary }) {
  const brandNames = Object.keys(summary.brands);
  const [filter, setFilter] = useState("all");

  const rows = useMemo(() => {
    return brandNames
      .filter((b) => filter === "all" || b === filter)
      .map((b) => summary.brands[b]);
  }, [brandNames, filter, summary]);

  return (
    <div className="screen">
      <h2>Overview</h2>
      <p className="muted">Generated {new Date(summary.generated_at).toLocaleString()}</p>

      <div className="card">
        <h3>Cross-brand insights</h3>
        {summary.insights.length === 0 && <p className="muted">No cross-brand insights available yet.</p>}
        <ul className="insight-list">
          {summary.insights.map((ins, i) => (
            <li key={i}>
              <strong>{ins.headline}</strong>
              <p>{ins.explanation}</p>
            </li>
          ))}
        </ul>
      </div>

      <div className="card">
        <div className="row-between">
          <h3>Sentiment by brand</h3>
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="all">All brands</option>
            {brandNames.map((b) => (
              <option key={b} value={b}>{b}</option>
            ))}
          </select>
        </div>
        <table>
          <thead>
            <tr>
              <th>Brand</th>
              <th>Sentiment</th>
              <th>Products</th>
              <th>Reviews</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.brand}>
                <td>{r.brand}</td>
                <td>
                  <span className={`tag tag-${r.sentiment_label}`}>
                    {r.sentiment_score.toFixed(1)} · {r.sentiment_label}
                  </span>
                </td>
                <td>{r.product_count}</td>
                <td>{r.review_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
