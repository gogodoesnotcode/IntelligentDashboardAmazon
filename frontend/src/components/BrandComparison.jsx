import { useMemo, useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

const ASPECTS = ["wheels", "handle", "zipper", "material", "size", "durability"];
const SERIES_COLORS = ["#1B4EF5", "#3874FF", "#5996FF", "#F4CEFF", "#0f39c4", "#8fb8ff"];
const MIN_SELECTED = 2;
const TOOLTIP_STYLE = { background: "#1f1c26", border: "1px solid #34303e", borderRadius: 8 };

export default function BrandComparison({ summary }) {
  const brandNames = Object.keys(summary.brands);
  const [selected, setSelected] = useState(new Set(brandNames));

  function toggle(name) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(name)) {
        if (next.size <= MIN_SELECTED) return prev; // keep a floor of 2
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  }

  const activeBrands = brandNames.filter((b) => selected.has(b));

  const aspectData = useMemo(
    () =>
      ASPECTS.map((aspect) => {
        const row = { aspect };
        activeBrands.forEach((b) => {
          row[b] = summary.brands[b].aspect_scores?.[aspect]?.score ?? null;
        });
        return row;
      }),
    [activeBrands, summary]
  );

  const vfmData = useMemo(
    () =>
      activeBrands.map((b) => ({
        brand: b,
        score: summary.brands[b].value_for_money?.score ?? null,
      })),
    [activeBrands, summary]
  );

  return (
    <div className="screen">
      <h2>Brand comparison</h2>

      <div className="chip-row">
        {brandNames.map((b) => {
          const isSelected = selected.has(b);
          return (
            <button
              key={b}
              className={`chip ${isSelected ? "selected" : ""}`}
              onClick={() => toggle(b)}
              disabled={isSelected && selected.size <= MIN_SELECTED}
              title={isSelected && selected.size <= MIN_SELECTED ? `At least ${MIN_SELECTED} brands must stay selected` : ""}
            >
              {b}
            </button>
          );
        })}
      </div>

      <div className="card">
        <h3>Aspect scores</h3>
        <div className="chart-box">
          <ResponsiveContainer>
            <BarChart data={aspectData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#34303e" />
              <XAxis dataKey="aspect" tick={{ fontSize: 12, fill: "#b8b4c4" }} />
              <YAxis domain={[0, 10]} tick={{ fontSize: 12, fill: "#b8b4c4" }} />
              <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: "#f1eee6" }} />
              <Legend wrapperStyle={{ color: "#b8b4c4", fontSize: 13 }} />
              {activeBrands.map((b, i) => (
                <Bar key={b} dataKey={b} fill={SERIES_COLORS[i % SERIES_COLORS.length]} radius={[4, 4, 0, 0]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card">
        <h3>Value for money</h3>
        <div className="chart-box">
          <ResponsiveContainer>
            <BarChart data={vfmData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#34303e" />
              <XAxis dataKey="brand" tick={{ fontSize: 12, fill: "#b8b4c4" }} />
              <YAxis domain={[0, 10]} tick={{ fontSize: 12, fill: "#b8b4c4" }} />
              <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: "#f1eee6" }} />
              <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                {vfmData.map((_, i) => (
                  <Cell key={i} fill={SERIES_COLORS[i % SERIES_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
