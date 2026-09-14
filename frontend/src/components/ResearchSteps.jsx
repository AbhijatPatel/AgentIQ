export default function ResearchSteps({ events }) {
  if (events.length === 0) {
    return <p style={{ color: "#9ca3af" }}>Waiting for activity...</p>;
  }

  return (
    <div
      style={{
        maxHeight: "300px",
        overflowY: "auto",
        border: "1px solid #e5e7eb",
        borderRadius: "8px",
        padding: "0.75rem",
        fontFamily: "monospace",
        fontSize: "0.85rem",
        background: "#f9fafb",
      }}
    >
      {events.map((event, i) => (
        <div
          key={i}
          style={{
            padding: "0.25rem 0",
            color: event.status === "error" ? "#ef4444" : "#374151",
          }}
        >
          <span style={{ color: "#6b7280" }}>[{event.agent}]</span> {event.message}
        </div>
      ))}
    </div>
  );
}