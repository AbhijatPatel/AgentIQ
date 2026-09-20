const AGENT_COLORS = {
  planner: "#4f46e5",
  researcher: "#0891b2",
  writer: "#d97706",
  critic: "#7c3aed",
};

export default function ResearchSteps({ events, activeFilter }) {
  const filtered = activeFilter
    ? events.filter((e) => e.agent === activeFilter)
    : events;

  if (events.length === 0) {
    return (
      <div className="research-steps-empty">
        <span className="steps-idle-dot" />
        <span>Waiting for agent activity...</span>
      </div>
    );
  }

  return (
    <div className="research-steps-wrapper">
      {activeFilter && (
        <div className="research-filter-notice">
          Showing only{" "}
          <strong style={{ color: AGENT_COLORS[activeFilter] }}>
            {activeFilter}
          </strong>{" "}
          events
        </div>
      )}
      <div className="research-steps-container">
        {filtered.map((event, i) => (
          <div
            key={i}
            className={`research-step-row ${
              event.status === "error" ? "research-step-row--error" : ""
            }`}
          >
            <span
              className="research-step-agent-badge"
              style={{
                backgroundColor: AGENT_COLORS[event.agent] || "#64748b",
              }}
            >
              {event.agent}
            </span>
            <span className="research-step-message">{event.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}