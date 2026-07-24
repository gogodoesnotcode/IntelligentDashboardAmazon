import { useState } from "react";

export default function ProductDrilldown({ summary }) {
  const brandNames = Object.keys(summary.brands);
  const [selected, setSelected] = useState(brandNames[0]);
  const brand = summary.brands[selected];

  return (
    <div className="screen">
      <h2>Product drilldown</h2>

      <div className="row-between">
        <select value={selected} onChange={(e) => setSelected(e.target.value)}>
          {brandNames.map((b) => (
            <option key={b} value={b}>{b}</option>
          ))}
        </select>
      </div>

      {brand && (
        <div className="card">
          <h3>{brand.brand}</h3>
          <p className="muted">{brand.product_count} products · {brand.review_count} reviews</p>
          <p>{brand.sentiment_summary || "No sentiment summary available."}</p>

          <div className="theme-columns">
            <div>
              <h4>Praise themes</h4>
              <ul>
                {brand.praise_themes.length
                  ? brand.praise_themes.map((t, i) => <li key={i}>{t}</li>)
                  : <li className="muted">None recorded</li>}
              </ul>
            </div>
            <div>
              <h4>Complaint themes</h4>
              <ul>
                {brand.complaint_themes.length
                  ? brand.complaint_themes.map((t, i) => <li key={i}>{t}</li>)
                  : <li className="muted">None recorded</li>}
              </ul>
            </div>
          </div>

          {brand.value_for_money?.verdict && (
            <p><strong>Value-for-money verdict:</strong> {brand.value_for_money.verdict}</p>
          )}

          {brand.errors.length > 0 && (
            <div className="card-warning">
              <strong>Non-fatal errors during analysis:</strong>
              <ul>
                {brand.errors.map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
