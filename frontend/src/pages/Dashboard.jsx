import { useState } from "react";
import { useResearch } from "../hooks/useResearch";
import AgentStatus from "../components/AgentStatus";
import ResearchSteps from "../components/ResearchSteps";
import ReportViewer from "../components/ReportViewer";
import SourceViewer from "../components/SourceViewer";

const MIN_GOAL_LENGTH = 5;

export default function Dashboard() {
  const [goalInput, setGoalInput] = useState("");
  const { status, events, result, error, run, reset } = useResearch();

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
    <div style={{ maxWidth: "800px", margin: "0 auto", padding: "2rem 1rem" }}>
      <header style={{ marginBottom: "2rem" }}>
        <h1 style={{ marginBottom: "0.25rem" }}>AgentIQ</h1>
        <p style={{ color: "#6b7280" }}>Autonomous Multi-Agent Research Assistant</p>
      </header>

      <form onSubmit={handleSubmit} style={{ marginBottom: "1.5rem" }}>
        <textarea
          value={goalInput}
          onChange={(e) => setGoalInput(e.target.value)}
          placeholder="What would you like AgentIQ to research?"
          disabled={isRunning}
          rows={3}
          style={{
            width: "100%",
            padding: "0.75rem",
            borderRadius: "8px",
            border: "1px solid #d1d5db",
            fontSize: "1rem",
            fontFamily: "inherit",
            resize: "vertical",
          }}
        />
        <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.75rem" }}>
          <button
            type="submit"
            disabled={!canSubmit}
            style={{
              padding: "0.6rem 1.5rem",
              borderRadius: "8px",
              border: "none",
              background: canSubmit ? "#111827" : "#d1d5db",
              color: "white",
              fontWeight: 600,
              cursor: canSubmit ? "pointer" : "not-allowed",
            }}
          >
            {isRunning ? "Researching..." : "Start Research"}
          </button>

          {(status === "completed" || status === "failed") && (
            <button
              type="button"
              onClick={handleReset}
              style={{
                padding: "0.6rem 1.5rem",
                borderRadius: "8px",
                border: "1px solid #d1d5db",
                background: "white",
                cursor: "pointer",
              }}
            >
              New Research
            </button>
          )}
        </div>
      </form>

      {status !== "idle" && (
        <>
          <AgentStatus events={events} />
          <ResearchSteps events={events} />
        </>
      )}

      {error && (
        <div
          style={{
            marginTop: "1rem",
            padding: "0.75rem 1rem",
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: "8px",
            color: "#b91c1c",
          }}
        >
          {error}
        </div>
      )}

      {result?.errors?.length > 0 && (
        <div
          style={{
            marginTop: "1rem",
            padding: "0.75rem 1rem",
            background: "#fffbeb",
            border: "1px solid #fde68a",
            borderRadius: "8px",
            color: "#92400e",
            fontSize: "0.85rem",
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
        <ReportViewer report={result.final_report} critique={result.critique} />
      )}
            {result?.evidence && <SourceViewer evidence={result.evidence} />}
    </div>
  );
}