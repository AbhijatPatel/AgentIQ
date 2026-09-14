const STAGES = [
  { key: "planner", label: "Planner" },
  { key: "researcher", label: "Researcher" },
  { key: "writer", label: "Writer" },
  { key: "critic", label: "Critic" },
];

function stageIcon(stageStatus) {
  if (stageStatus === "done") return "✓";
  if (stageStatus === "active") return "⟳";
  if (stageStatus === "error") return "✗";
  return "○";
}

function stageColor(stageStatus) {
  if (stageStatus === "done") return "#22c55e";
  if (stageStatus === "active") return "#3b82f6";
  if (stageStatus === "error") return "#ef4444";
  return "#9ca3af";
}

/**
 * Derives each stage's status (pending/active/done/error) from the
 * flat list of AgentEvents received so far over SSE.
 */
function deriveStageStatus(events, stageKey) {
  const stageEvents = events.filter((e) => e.agent === stageKey);
  if (stageEvents.length === 0) return "pending";

  const last = stageEvents[stageEvents.length - 1];
  if (last.status === "error") return "error";
  if (last.event === "completed" || last.event === "draft_created" || last.event === "critique_created") {
    return "done";
  }
  return "active";
}

export default function AgentStatus({ events }) {
  return (
    <div style={{ display: "flex", gap: "1.5rem", padding: "1rem 0", flexWrap: "wrap" }}>
      {STAGES.map((stage) => {
        const status = deriveStageStatus(events, stage.key);
        return (
          <div key={stage.key} style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ color: stageColor(status), fontSize: "1.2rem", fontWeight: "bold" }}>
              {stageIcon(status)}
            </span>
            <span style={{ color: status === "pending" ? "#9ca3af" : "#111827" }}>
              {stage.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}