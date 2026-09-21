import { useEffect, useState } from "react";
import { getResearchHistory, deleteResearchSession } from "../services/api";

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
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadHistory() {
      setLoading(true);
      try {
        const data = await getResearchHistory(20, searchTerm);
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
  }, [refreshKey, searchTerm]);

  const handleDelete = async (e, researchId) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this research session?")) return;

    try {
      await deleteResearchSession(researchId);
      setSessions((prev) => prev.filter((s) => s.research_id !== researchId));
    } catch (err) {
      console.error("Failed to delete session", err);
    }
  };

  if (sessions.length === 0 && !loading && !searchTerm) return null;

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
          <div style={{ padding: "0.5rem" }}>
            <input
              type="text"
              placeholder="Search past research..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="history-search-input"
              style={{
                width: "100%",
                padding: "0.4rem 0.6rem",
                borderRadius: "6px",
                border: "1px solid rgba(255,255,255,0.15)",
                background: "rgba(0,0,0,0.2)",
                color: "#fff",
                fontSize: "0.85rem",
              }}
            />
          </div>

          {loading && <p style={{ color: "#9ca3af", padding: "0.5rem" }}>Loading...</p>}
          {!loading && sessions.length === 0 && (
            <p style={{ color: "#9ca3af", padding: "0.5rem", fontSize: "0.85rem" }}>
              No previous research sessions found.
            </p>
          )}
          {!loading &&
            sessions.map((s) => {
              const statusStyle = STATUS_COLORS[s.status] || STATUS_COLORS.running;
              return (
                <div
                  key={s.research_id}
                  className="history-item"
                  onClick={() => onSelectSession(s.research_id)}
                  style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}
                >
                  <div style={{ flex: 1, minWidth: 0, cursor: "pointer" }}>
                    <div className="history-item-title">
                      {s.final_report_title || s.user_goal}
                    </div>
                    <div className="history-item-meta">{formatDate(s.created_at)}</div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <span
                      className="history-status-pill"
                      style={{ background: statusStyle.bg, color: statusStyle.color }}
                    >
                      {s.status}
                    </span>
                    <button
                      type="button"
                      onClick={(e) => handleDelete(e, s.research_id)}
                      title="Delete research report"
                      style={{
                        background: "none",
                        border: "none",
                        color: "#ef4444",
                        cursor: "pointer",
                        fontSize: "0.9rem",
                        padding: "0.2rem 0.4rem",
                      }}
                    >
                      🗑
                    </button>
                  </div>
                </div>
              );
            })}
        </div>
      )}
    </div>
  );
}