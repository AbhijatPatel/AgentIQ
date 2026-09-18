import { useState } from "react";
import { useResearch } from "../hooks/useResearch";
import AgentStatus from "../components/AgentStatus";
import ResearchSteps from "../components/ResearchSteps";
import ReportViewer from "../components/ReportViewer";
import SourceViewer from "../components/SourceViewer";
import HistoryPanel from "../components/HistoryPanel";
import VideoGallery from "../components/VideoGallery";
import ImageGallery from "../components/ImageGallery";


const MIN_GOAL_LENGTH = 5;

export default function Dashboard() {
const [goalInput, setGoalInput] = useState("");
const [activeFilter, setActiveFilter] = useState(null);
const [historyRefreshKey, setHistoryRefreshKey] = useState(0);
const { status, events, result, error, run, reset, loadPastSession } = useResearch();

  const isRunning = status === "running";
  const canSubmit = goalInput.trim().length >= MIN_GOAL_LENGTH && !isRunning;

  const handleSubmit = (e) => {
  e.preventDefault();
  if (!canSubmit) return;
  run(goalInput.trim());
  setTimeout(() => setHistoryRefreshKey((k) => k + 1), 90000); // refresh history ~90s later
};

  const handleReset = () => {
    reset();
    setGoalInput("");
  };

  return (
    <>
        <header className="app-header">
        <div className="logo-badge">✦ Multi-Agent AI System</div>
        <h1>AgentIQ</h1>
        <p>Autonomous Multi-Agent Research Assistant</p>
      </header>

            <HistoryPanel
        refreshKey={historyRefreshKey}
        onSelectSession={async (id) => {
          const res = await fetch(`http://localhost:8000/api/research/${id}`);
          const data = await res.json();
          loadPastSession(data);
        }}
      />

      <form onSubmit={handleSubmit} className="goal-form">
        <textarea
          className="goal-textarea"
          value={goalInput}
          onChange={(e) => setGoalInput(e.target.value)}
          placeholder="What would you like AgentIQ to research?"
          disabled={isRunning}
          rows={3}
        />
        <div className="button-row">
          <button type="submit" disabled={!canSubmit} className="start-research-btn">
            {isRunning ? "Researching..." : "Start Research"}
          </button>

          {(status === "completed" || status === "failed") && (
            <button type="button" onClick={handleReset} className="secondary-btn">
              New Research
            </button>
          )}
        </div>
      </form>

            {status !== "idle" && (
        <div className="pipeline-card">
          <AgentStatus events={events} activeFilter={activeFilter} onFilterChange={setActiveFilter} />
          <ResearchSteps events={events} activeFilter={activeFilter} />
        </div>
      )}

      {error && (
        <div
          style={{
            padding: "0.75rem 1rem",
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: "10px",
            color: "#b91c1c",
            marginBottom: "1.5rem",
          }}
        >
          {error}
        </div>
      )}

      {result?.errors?.length > 0 && (
        <div
          style={{
            padding: "0.75rem 1rem",
            background: "#fffbeb",
            border: "1px solid #fde68a",
            borderRadius: "10px",
            color: "#92400e",
            fontSize: "0.85rem",
            marginBottom: "1.5rem",
          }}
        >
          <strong>Note:</strong> some steps had issues but the pipeline continued:
          <ul style={{ marginTop: "0.35rem", paddingLeft: "1.25rem" }}>
            {result.errors.map((err, i) => (
              <li key={i}>{err}</li>
            ))}
          </ul>
        </div>
      )}

      {result?.final_report && (
        <div className="report-card">
          <ReportViewer report={result.final_report} critique={result.critique} />
        </div>
      )}

    {result?.evidence && result.evidence.length > 0 && (
  <div className="sources-card">
    <SourceViewer evidence={result.evidence} />
  </div>
)}

      {result?.images && result.images.length > 0 && (
        <div className="sources-card">
          <ImageGallery images={result.images} />
        </div>
      )}

          {result?.videos && result.videos.length > 0 && (
        <div className="sources-card">
          <VideoGallery videos={result.videos} />
        </div>
      )}
    </>
  );
}