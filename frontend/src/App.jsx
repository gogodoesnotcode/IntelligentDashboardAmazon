import { useEffect, useState } from "react";
import { fetchSummary } from "./api/client.js";
import Overview from "./components/Overview.jsx";
import BrandComparison from "./components/BrandComparison.jsx";
import BrandDrilldown from "./components/BrandDrilldown.jsx";

const SCREENS = [
  { id: "overview", label: "Overview" },
  { id: "comparison", label: "Brand comparison" },
  { id: "drilldown", label: "Brand drilldown" },
];

export default function App() {
  const [screen, setScreen] = useState("overview");
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchSummary().then(setSummary).catch((e) => setError(e.message));
  }, []);

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>BagBoard</h1>
        <nav>
          {SCREENS.map((s) => (
            <button
              key={s.id}
              className={`nav-btn ${screen === s.id ? "active" : ""}`}
              onClick={() => setScreen(s.id)}
            >
              {s.label}
            </button>
          ))}
        </nav>
      </header>

      <main>
        {error && (
          <div className="card-warning">
            Failed to load analysis data: {error}. Run{" "}
            <code>agent/run_analysis.py</code> then restart the backend.
          </div>
        )}
        {!error && !summary && <p className="muted">Loading...</p>}
        {summary && screen === "overview" && <Overview summary={summary} />}
        {summary && screen === "comparison" && <BrandComparison summary={summary} />}
        {summary && screen === "drilldown" && <BrandDrilldown summary={summary} />}
      </main>

      <footer className="app-footer">
        <a href="https://github.com/gogodoesnotcode/BagBoard" target="_blank" rel="noopener noreferrer">
          BagBoard on GitHub
        </a>
      </footer>
    </div>
  );
}
