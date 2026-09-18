import { lazy, Suspense, useState } from "react";
import { getResearchStatus } from "../services/api";
import { useResearch } from "../hooks/useResearch";
import AgentStatus from "../components/AgentStatus";
import ResearchSteps from "../components/ResearchSteps";
import HistoryPanel from "../components/HistoryPanel";

const ReportViewer = lazy(() => import("../components/ReportViewer"));
const SourceViewer = lazy(() => import("../components/SourceViewer"));
const ImageGallery = lazy(() => import("../components/ImageGallery"));
const VideoGallery = lazy(() => import("../components/VideoGallery"));

const MIN_GOAL_LENGTH = 5;

export default function Dashboard() {
const [goalInput, setGoalInput] = useState("");
const [activeFilter, setActiveFilter] = useState(null);
const { status, events, result, error, run, reset, loadPastSession } = useResearch();

  const isRunning = status === "running";
  const canSubmit = goalInput.trim().length >= MIN_GOAL_LENGTH && !isRunning;

  const handleSubmit = (e) => {
  e.preventDefault();
  if (!canSubmit) return;
  run(goalInput.trim());
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
  refreshKey={result}
  onSelectSession={async (id) => {
    const data = await getResearchStatus(id);
    loadPastSession(data);
  }}
/>

      <form onSubmit={handleSubmit} className="goal-form">
        <textarea
        id="research-goal"
         className="goal-textarea"
        value={goalInput}
        onChange={(e) => setGoalInput(e.target.value)}
        placeholder="What would you like AgentIQ to research?"
        disabled={isRunning}
         rows={3}
         minLength={MIN_GOAL_LENGTH}
         maxLength={1000}
         aria-label="Research goal"
         aria-describedby="goal-help"
       />

<div id="goal-help" className="goal-help">
  {goalInput.length}/1000 characters
  {goalInput.trim().length < MIN_GOAL_LENGTH && goalInput.length > 0
    ? ` — Enter at least ${MIN_GOAL_LENGTH} characters`
    : ""}
</div>
        <div className="button-row">
          <button
  type="submit"
  disabled={!canSubmit}
  className="start-research-btn"
  aria-busy={isRunning}
>
  {isRunning && <span className="loading-spinner" aria-hidden="true" />}
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
  <div className="pipeline-card" aria-live="polite">
    <div className="pipeline-header">
      <div>
        <h2>Research Pipeline</h2>
        <p>
          {status === "running"
            ? "AgentIQ is working through your research task..."
            : status === "completed"
              ? "Research completed successfully."
              : "Research ended with an error."}
        </p>
      </div>

      <span className={`status-badge status-${status}`}>
        {status}
      </span>
    </div>

    <AgentStatus
      events={events}
      activeFilter={activeFilter}
      onFilterChange={setActiveFilter}
    />

    <ResearchSteps
      events={events}
      activeFilter={activeFilter}
    />
  </div>
)}

      {error && (
      <div className="error-alert" role="alert">
      {error}
      </div>
     )}

      {result?.errors?.length > 0 && (
  <div className="warning-alert" role="status">
    <strong>Note:</strong> some steps had issues but the pipeline continued:
    <ul>
      {result.errors.map((err, i) => (
        <li key={i}>{err}</li>
      ))}
    </ul>
  </div>
)}

      {result?.final_report && (
  <Suspense fallback={<div className="report-card">Loading report...</div>}>
    <div className="report-card">
      <ReportViewer
        report={result.final_report}
        critique={result.critique}
      />
    </div>
  </Suspense>
)}

    {result?.evidence && result.evidence.length > 0 && (
  <Suspense fallback={<div className="sources-card">Loading sources...</div>}>
    <div className="sources-card">
      <SourceViewer evidence={result.evidence} />
    </div>
  </Suspense>
)}

      {result?.images && result.images.length > 0 && (
  <Suspense fallback={<div className="sources-card">Loading images...</div>}>
    <div className="sources-card">
      <ImageGallery images={result.images} />
    </div>
  </Suspense>
)}

          {result?.videos && result.videos.length > 0 && (
  <Suspense fallback={<div className="sources-card">Loading videos...</div>}>
    <div className="sources-card">
      <VideoGallery videos={result.videos} />
    </div>
  </Suspense>
)}
    </>
  );
}