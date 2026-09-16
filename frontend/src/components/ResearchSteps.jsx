const AGENT_COLORS = {
  planner: "#4f46e5",
  researcher: "#0891b2",
  writer: "#d97706",
  critic: "#7c3aed",
};

export default function ResearchSteps({ events, activeFilter }) {
  const filtered = activeFilter ? events.filter((e) => e.agent === activeFilter) : events;

  if (events.length === 0) {
    return <p style={{ color: "#9ca3af", margin: 0 }}>Waiting for activity...</p>;
  }

  return (
    <div>
      {activeFilter && (
        <div style={{ fontSize: "0.8rem", color: "#6b7280", marginBottom: "0.5rem" }}>
          Showing only <strong style={{ color: AGENT_COLORS[activeFilter] }}>{activeFilter}</strong> events
        </div>
      )}
      <div
        style={{
          maxHeight: "320px",
          overflowY: "auto",
          border: "1px solid #e5e7eb",
          borderRadius: "10px",
          padding: "0.5rem",
          background: "#fafafa",
        }}
      >
        {filtered.map((event, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: "0.75rem",
              padding: "0.5rem 0.6rem",
              borderRadius: "8px",
              marginBottom: "0.25rem",
              background: event.status === "error" ? "#fef2f2" : "transparent",
              flexWrap: "nowrap",
            }}
          >
            <span
              style={{
                flexShrink: 0,
                fontSize: "0.7rem",
                fontWeight: 700,
                textTransform: "uppercase",
                color: "#fff",
                background: AGENT_COLORS[event.agent] || "#6b7280",
                padding: "0.2rem 0.6rem",
                borderRadius: "999px",
                marginTop: "0.1rem",
                whiteSpace: "nowrap",
                minWidth: "5.5rem",
                textAlign: "center",
              }}
            >
              {event.agent}
            </span>
            <span
              style={{
                fontSize: "0.88rem",
                color: event.status === "error" ? "#b91c1c" : "#374151",
                lineHeight: 1.5,
              }}
            >
              {event.message}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}