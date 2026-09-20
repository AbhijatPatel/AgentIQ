const STAGES = [
  { key: "planner", label: "Planner", icon: "🧭" },
  { key: "researcher", label: "Researcher", icon: "🔍" },
  { key: "writer", label: "Writer", icon: "✍️" },
  { key: "critic", label: "Critic", icon: "⚖️" },
];

function deriveStageStatus(events, stageKey) {
  const stageEvents = events.filter((e) => e.agent === stageKey);
  if (stageEvents.length === 0) return "pending";

  const last = stageEvents[stageEvents.length - 1];
  if (last.status === "error") return "error";
  if (
    last.event === "completed" ||
    last.event === "draft_created" ||
    last.event === "critique_created"
  ) {
    return "done";
  }
  return "active";
}

export default function AgentStatus({ events, activeFilter, onFilterChange }) {
  return (
    <div className="agent-stages-row">
      {STAGES.map((stage) => {
        const status = deriveStageStatus(events, stage.key);
        const isSelected = activeFilter === stage.key;
        const hasEvents = events.some((e) => e.agent === stage.key);

        return (
          <button
            key={stage.key}
            type="button"
            disabled={!hasEvents}
            onClick={() => onFilterChange(isSelected ? null : stage.key)}
            className={`agent-stage-pill agent-stage-pill--${status} ${
              isSelected ? "agent-stage-pill--selected" : ""
            } ${status === "active" ? "agent-stage-pill--pulsing" : ""}`}
            title={
              hasEvents
                ? `Filter activity by ${stage.label}`
                : `${stage.label} agent waiting`
            }
          >
            <span className="agent-stage-icon">{stage.icon}</span>
            <span className="agent-stage-label">{stage.label}</span>
            {status === "active" && (
              <span className="agent-spinner-icon" aria-hidden="true">
                ⟳
              </span>
            )}
            {status === "done" && (
              <span className="agent-check-icon" aria-hidden="true">
                ✓
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}