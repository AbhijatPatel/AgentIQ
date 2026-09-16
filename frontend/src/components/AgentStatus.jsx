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
  if (last.event === "completed" || last.event === "draft_created" || last.event === "critique_created") {
    return "done";
  }
  return "active";
}

const STATUS_STYLES = {
  pending: { background: "#f3f4f6", color: "#9ca3af", border: "1px solid #e5e7eb" },
  active: { background: "#eef2ff", color: "#4f46e5", border: "1px solid #c7d2fe" },
  done: { background: "#dcfce7", color: "#16a34a", border: "1px solid #bbf7d0" },
  error: { background: "#fee2e2", color: "#dc2626", border: "1px solid #fecaca" },
};

export default function AgentStatus({ events, activeFilter, onFilterChange }) {
  return (
    <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", marginBottom: "1.25rem" }}>
      {STAGES.map((stage) => {
        const status = deriveStageStatus(events, stage.key);
        const style = STATUS_STYLES[status];
        const isSelected = activeFilter === stage.key;
        const hasEvents = events.some((e) => e.agent === stage.key);

        return (
          <button
            key={stage.key}
            type="button"
            disabled={!hasEvents}
            onClick={() => onFilterChange(isSelected ? null : stage.key)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              padding: "0.55rem 1.2rem",
              borderRadius: "999px",
              fontSize: "0.9rem",
              fontWeight: 600,
              cursor: hasEvents ? "pointer" : "default",
              transition: "all 0.18s ease",
              outline: isSelected ? "2px solid currentColor" : "none",
              outlineOffset: "2px",
              transform: isSelected ? "scale(1.04)" : "scale(1)",
              boxShadow: isSelected ? "0 2px 8px rgba(0,0,0,0.1)" : "none",
              ...style,
            }}
            onMouseEnter={(e) => {
              if (hasEvents) e.currentTarget.style.filter = "brightness(0.96)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.filter = "none";
            }}
          >
            <span style={{ fontSize: "1.3rem", lineHeight: 1 }}>{stage.icon}</span>
            <span>{stage.label}</span>
            {status === "active" && <span style={{ fontSize: "0.75rem" }}>⟳</span>}
            {status === "done" && <span style={{ fontSize: "0.75rem" }}>✓</span>}
          </button>
        );
      })}
    </div>
  );
}