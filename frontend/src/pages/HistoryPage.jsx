import { useEffect, useState, useMemo } from "react";
import { getResearchHistory } from "../services/api";

function formatTimestamp(isoString) {
  if (!isoString) return "Recently";
  try {
    const date = new Date(isoString);
    return date.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return isoString;
  }
}

export default function HistoryPage({ onSelectSession, onStartNewResearch }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const loadHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getResearchHistory(50);
      setSessions(data.sessions || []);
    } catch (err) {
      setError(err.message || "Failed to load research history.");
      setSessions([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  // Filter sessions by search query and status tab
  const filteredSessions = useMemo(() => {
    return sessions.filter((s) => {
      const matchesStatus =
        statusFilter === "all" ? true : s.status === statusFilter;

      const query = searchQuery.trim().toLowerCase();
      const matchesSearch =
        !query ||
        (s.user_goal && s.user_goal.toLowerCase().includes(query)) ||
        (s.final_report_title && s.final_report_title.toLowerCase().includes(query)) ||
        (s.research_id && s.research_id.toLowerCase().includes(query));

      return matchesStatus && matchesSearch;
    });
  }, [sessions, statusFilter, searchQuery]);

  // Quick stats
  const completedCount = sessions.filter((s) => s.status === "completed").length;
  const runningCount = sessions.filter((s) => s.status === "running").length;
  const failedCount = sessions.filter((s) => s.status === "failed").length;

  return (
    <div className="history-page">
      {/* Header */}
      <header className="history-page-header">
        <div className="history-header-top">
          <div>
            <div className="eyebrow">Archive & Knowledge Base</div>
            <h1>Research Library & History</h1>
            <p>
              Browse, search, and revisit all past autonomous research reports,
              citations, visual assets, and videos.
            </p>
          </div>

          <div className="history-header-actions">
            <button
              type="button"
              onClick={onStartNewResearch}
              className="start-research-btn"
            >
              <span aria-hidden="true">+</span> New Research
            </button>
          </div>
        </div>

        {/* Stats Row */}
        <div className="history-stats-row">
          <div className="history-stat-box">
            <span className="history-stat-number">{sessions.length}</span>
            <span className="history-stat-label">Total Researches</span>
          </div>

          <div className="history-stat-box">
            <span className="history-stat-number history-stat--completed">
              {completedCount}
            </span>
            <span className="history-stat-label">Completed Reports</span>
          </div>

          <div className="history-stat-box">
            <span className="history-stat-number history-stat--completed">
              {sessions.length > 0
                ? `${Math.round((completedCount / sessions.length) * 100)}%`
                : "100%"}
            </span>
            <span className="history-stat-label">Success Rate</span>
          </div>

          {runningCount > 0 && (
            <div
              className="history-stat-box history-stat-box--active"
              onClick={onStartNewResearch}
              style={{ cursor: "pointer" }}
              title="Click to view live research"
            >
              <span className="history-stat-number history-stat--running">
                <span className="status-pulse-dot" />
                {runningCount}
              </span>
              <span className="history-stat-label">Currently Running (Live)</span>
            </div>
          )}

          {failedCount > 0 && (
            <div className="history-stat-box">
              <span className="history-stat-number history-stat--failed">
                {failedCount}
              </span>
              <span className="history-stat-label">Needs Attention</span>
            </div>
          )}
        </div>
      </header>

      {/* Controls Bar: Search & Status Filters */}
      <div className="history-controls-card">
        <div className="history-search-wrapper">
          <span className="history-search-icon" aria-hidden="true">
            🔍
          </span>
          <input
            type="text"
            className="history-search-input"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search past research by topic, title, or keywords..."
            aria-label="Search research history"
          />
          {searchQuery && (
            <button
              type="button"
              className="history-clear-btn"
              onClick={() => setSearchQuery("")}
              aria-label="Clear search"
            >
              ✕
            </button>
          )}
        </div>

        <div className="history-filter-tabs">
          <button
            type="button"
            className={`history-filter-pill ${
              statusFilter === "all" ? "history-filter-pill--active" : ""
            }`}
            onClick={() => setStatusFilter("all")}
          >
            All <span className="pill-count">{sessions.length}</span>
          </button>

          <button
            type="button"
            className={`history-filter-pill ${
              statusFilter === "completed" ? "history-filter-pill--active" : ""
            }`}
            onClick={() => setStatusFilter("completed")}
          >
            Completed <span className="pill-count">{completedCount}</span>
          </button>

          {runningCount > 0 && (
            <button
              type="button"
              className={`history-filter-pill ${
                statusFilter === "running" ? "history-filter-pill--active" : ""
              }`}
              onClick={() => setStatusFilter("running")}
            >
              Running <span className="pill-count">{runningCount}</span>
            </button>
          )}

          {failedCount > 0 && (
            <button
              type="button"
              className={`history-filter-pill ${
                statusFilter === "failed" ? "history-filter-pill--active" : ""
              }`}
              onClick={() => setStatusFilter("failed")}
            >
              Failed <span className="pill-count">{failedCount}</span>
            </button>
          )}

          <button
            type="button"
            onClick={loadHistory}
            className="history-refresh-btn"
            title="Refresh history"
            aria-label="Refresh research history"
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="error-alert" role="alert">
          {error}
          <button
            type="button"
            onClick={loadHistory}
            className="secondary-btn"
            style={{ marginLeft: "12px", padding: "4px 10px" }}
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="history-loading-container">
          <span className="loading-spinner" style={{ width: "24px", height: "24px" }} />
          <p>Loading research library...</p>
        </div>
      )}

      {/* Empty State: No sessions at all */}
      {!loading && sessions.length === 0 && !error && (
        <div className="history-empty-card">
          <div className="history-empty-icon">📚</div>
          <h3>No research history yet</h3>
          <p>
            When you run an autonomous research task, the report, citations,
            images, and videos will be saved here automatically.
          </p>
          <button
            type="button"
            onClick={onStartNewResearch}
            className="start-research-btn"
          >
            Start Your First Research →
          </button>
        </div>
      )}

      {/* Empty State: Filter/search yielded nothing */}
      {!loading && sessions.length > 0 && filteredSessions.length === 0 && (
        <div className="history-empty-card">
          <div className="history-empty-icon">🔎</div>
          <h3>No matches found</h3>
          <p>No research sessions matched "{searchQuery || statusFilter}".</p>
          <button
            type="button"
            onClick={() => {
              setSearchQuery("");
              setStatusFilter("all");
            }}
            className="secondary-btn"
          >
            Clear Filters
          </button>
        </div>
      )}

      {/* History Grid */}
      {!loading && filteredSessions.length > 0 && (
        <div className="history-grid">
          {filteredSessions.map((session) => {
            const isCompleted = session.status === "completed";
            const isRunning = session.status === "running";
            const isFailed = session.status === "failed";

            return (
              <div
                key={session.research_id}
                className={`history-session-card history-session-card--${session.status}`}
                onClick={() => onSelectSession(session.research_id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    onSelectSession(session.research_id);
                  }
                }}
              >
                <div className="session-card-topline">
                  <span
                    className={`status-badge status-${session.status}`}
                  >
                    {isRunning && <span className="status-pulse-dot" />}
                    {session.status}
                  </span>

                  <span className="session-date">
                    {formatTimestamp(session.created_at)}
                  </span>
                </div>

                <h3 className="session-title">
                  {session.final_report_title || session.user_goal}
                </h3>

                <div className="session-goal-box">
                  <span className="session-goal-label">Prompt:</span>
                  <p className="session-goal-text">{session.user_goal}</p>
                </div>

                <div className="session-card-footer">
                  <span className="session-id-tag">
                    #{session.research_id.slice(0, 8)}
                  </span>

                  <button
                    type="button"
                    className="session-open-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectSession(session.research_id);
                    }}
                  >
                    {isCompleted
                      ? "View Full Report →"
                      : isRunning
                      ? "View Progress →"
                      : "Inspect Session →"}
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
