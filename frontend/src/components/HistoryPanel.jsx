import { useEffect, useState } from "react";

const API_BASE = "http://localhost:8000/api";

const STATUS_COLORS = {
  completed: { bg: "#dcfce7", color: "#16a34a" },
  running: { bg: "#eef2ff", color: "#4f46e5" },
  failed: { bg: "#fee2e2", color: "#dc2626" },
};

function formatDate(isoString) {
  if (!isoString) return "";
  const date = new Date(isoString);
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function HistoryPanel({ onSelectSession, refreshKey }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadHistory() {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/research?limit=15`);
        if (!res.ok) throw new Error("Failed to load history");
        const data = await res.json();
        if (!cancelled) setSessions(data.sessions || []);
      } catch {
        if (!cancelled) setSessions([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadHistory();
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  if (sessions.length === 0 && !loading) return null;

  return (
    <div className="history-card">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="history-toggle"
      >
        <span>📜 Research History {sessions.length > 0 && `(${sessions.length})`}</span>
        <span>{open ? "−" : "+"}</span>
      </button>

      {open && (
        <div className="history-list">
          {loading && <p style={{ color: "#9ca3af", padding: "0.5rem" }}>Loading...</p>}
          {!loading &&
            sessions.map((s) => {
              const statusStyle = STATUS_COLORS[s.status] || STATUS_COLORS.running;
              return (
                <button
                  key={s.research_id}
                  className="history-item"
                  onClick={() => onSelectSession(s.research_id)}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="history-item-title">
                      {s.final_report_title || s.user_goal}
                    </div>
                    <div className="history-item-meta">{formatDate(s.created_at)}</div>
                  </div>
                  <span
                    className="history-status-pill"
                    style={{ background: statusStyle.bg, color: statusStyle.color }}
                  >
                    {s.status}
                  </span>
                </button>
              );
            })}
        </div>
      )}
    </div>
  );
}