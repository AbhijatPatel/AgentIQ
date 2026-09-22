import { useState, useEffect, useMemo, useRef } from "react";
import logoIcon from "../assets/logo-icon.png";
import { getResearchHistory, deleteResearchSession, renameResearchSession } from "../services/api";

/**
 * Group sessions chronologically into Today, Yesterday, Previous 7 Days, and Older.
 */
function groupSessionsChronologically(sessions) {
  const groups = {
    today: [],
    yesterday: [],
    previous7Days: [],
    older: [],
  };

  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfYesterday = new Date(startOfToday);
  startOfYesterday.setDate(startOfYesterday.getDate() - 1);
  const startOf7DaysAgo = new Date(startOfToday);
  startOf7DaysAgo.setDate(startOf7DaysAgo.getDate() - 7);

  sessions.forEach((session) => {
    const sessionDate = session.created_at ? new Date(session.created_at) : new Date();
    if (sessionDate >= startOfToday) {
      groups.today.push(session);
    } else if (sessionDate >= startOfYesterday) {
      groups.yesterday.push(session);
    } else if (sessionDate >= startOf7DaysAgo) {
      groups.previous7Days.push(session);
    } else {
      groups.older.push(session);
    }
  });

  return groups;
}

export default function Sidebar({
  isOpen,
  onToggle,
  activeResearchId,
  onSelectSession,
  onStartNewResearch,
  user,
  onLogout,
}) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState("");
  const [isSavingRename, setIsSavingRename] = useState(false);
  const editInputRef = useRef(null);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const data = await getResearchHistory(50);
      setSessions(data.sessions || []);
    } catch (err) {
      console.warn("Failed to load sidebar history:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [activeResearchId]);

  useEffect(() => {
    if (editingId && editInputRef.current) {
      editInputRef.current.focus();
      editInputRef.current.select();
    }
  }, [editingId]);

  const handleStartRename = (e, session) => {
    e.stopPropagation();
    setEditingId(session.research_id);
    setEditTitle(session.title || session.final_report_title || session.user_goal || "Research Session");
  };

  const handleSaveRename = async (e, researchId) => {
    e.stopPropagation();
    if (!editTitle.trim()) {
      setEditingId(null);
      return;
    }

    setIsSavingRename(true);
    try {
      await renameResearchSession(researchId, editTitle.trim());
      setSessions((prev) =>
        prev.map((s) =>
          s.research_id === researchId ? { ...s, title: editTitle.trim() } : s
        )
      );
      setEditingId(null);
    } catch (err) {
      alert(`Could not rename session: ${err.message}`);
    } finally {
      setIsSavingRename(false);
    }
  };

  const handleCancelRename = (e) => {
    e.stopPropagation();
    setEditingId(null);
    setEditTitle("");
  };

  const handleDeleteSession = async (e, researchId) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this research session?")) return;

    try {
      await deleteResearchSession(researchId);
      setSessions((prev) => prev.filter((s) => s.research_id !== researchId));
      if (activeResearchId === researchId) {
        onStartNewResearch();
      }
    } catch (err) {
      alert(`Could not delete session: ${err.message}`);
    }
  };

  const filteredSessions = useMemo(() => {
    if (!searchQuery.trim()) return sessions;
    const q = searchQuery.trim().toLowerCase();
    return sessions.filter((s) => {
      const title = (s.title || s.final_report_title || "").toLowerCase();
      const goal = (s.user_goal || "").toLowerCase();
      return title.includes(q) || goal.includes(q);
    });
  }, [sessions, searchQuery]);

  const grouped = useMemo(() => groupSessionsChronologically(filteredSessions), [filteredSessions]);

  const renderSessionItem = (session) => {
    const isEditing = editingId === session.research_id;
    const isActive = activeResearchId === session.research_id;
    const displayTitle = session.title || session.final_report_title || session.user_goal || "Untitled Research";

    return (
      <div
        key={session.research_id}
        className={`sidebar-session-item ${isActive ? "sidebar-session-item--active" : ""} ${
          isEditing ? "sidebar-session-item--editing" : ""
        }`}
        onClick={() => {
          if (!isEditing) onSelectSession(session.research_id);
        }}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (!isEditing && (e.key === "Enter" || e.key === " ")) {
            onSelectSession(session.research_id);
          }
        }}
        title={session.user_goal || displayTitle}
      >
        <span className="sidebar-session-icon" aria-hidden="true">
          {session.status === "running" ? (
            <span className="sidebar-pulse-dot" />
          ) : session.status === "completed" ? (
            "📄"
          ) : (
            "⚠️"
          )}
        </span>

        {isEditing ? (
          <div className="sidebar-edit-container" onClick={(e) => e.stopPropagation()}>
            <input
              ref={editInputRef}
              type="text"
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSaveRename(e, session.research_id);
                if (e.key === "Escape") handleCancelRename(e);
              }}
              className="sidebar-edit-input"
              disabled={isSavingRename}
              maxLength={120}
            />
            <div className="sidebar-edit-actions">
              <button
                type="button"
                className="sidebar-action-btn-mini check"
                onClick={(e) => handleSaveRename(e, session.research_id)}
                disabled={isSavingRename}
                title="Save title"
              >
                ✓
              </button>
              <button
                type="button"
                className="sidebar-action-btn-mini cancel"
                onClick={handleCancelRename}
                disabled={isSavingRename}
                title="Cancel"
              >
                ✕
              </button>
            </div>
          </div>
        ) : (
          <>
            <span className="sidebar-session-title">{displayTitle}</span>
            <div className="sidebar-item-actions">
              <button
                type="button"
                className="sidebar-action-btn"
                onClick={(e) => handleStartRename(e, session)}
                title="Rename research"
                aria-label="Rename research"
              >
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 20h9" />
                  <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
                </svg>
              </button>
              <button
                type="button"
                className="sidebar-action-btn danger"
                onClick={(e) => handleDeleteSession(e, session.research_id)}
                title="Delete research"
                aria-label="Delete research"
              >
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="3 6 5 6 21 6" />
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                </svg>
              </button>
            </div>
          </>
        )}
      </div>
    );
  };

  return (
    <aside className={`chatgpt-sidebar ${isOpen ? "chatgpt-sidebar--open" : "chatgpt-sidebar--closed"}`}>
      {/* Top Header & Brand */}
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <img src={logoIcon} alt="AgentIQ Logo" className="sidebar-logo-img" />
          <span className="sidebar-brand-name">
            Agent<span className="sidebar-brand-iq">IQ</span>
          </span>
        </div>
        <button
          type="button"
          className="sidebar-toggle-btn"
          onClick={onToggle}
          title={isOpen ? "Collapse sidebar" : "Open sidebar"}
          aria-label="Toggle sidebar"
        >
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
      </div>

      {/* Primary New Research Button */}
      <div className="sidebar-actions-top">
        <button
          type="button"
          className="sidebar-new-research-btn"
          onClick={onStartNewResearch}
          title="Start a new autonomous research workspace"
        >
          <span className="sidebar-plus-icon">+</span>
          <span>New Research</span>
        </button>
      </div>

      {/* Real-time search filter */}
      <div className="sidebar-search-box">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" className="sidebar-search-icon">
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          type="text"
          className="sidebar-search-input"
          placeholder="Search research history..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        {searchQuery && (
          <button
            type="button"
            className="sidebar-clear-search-btn"
            onClick={() => setSearchQuery("")}
            title="Clear search"
          >
            ✕
          </button>
        )}
      </div>

      {/* History List */}
      <div className="sidebar-history-container">
        {loading && sessions.length === 0 ? (
          <div className="sidebar-empty-state">Loading history...</div>
        ) : filteredSessions.length === 0 ? (
          <div className="sidebar-empty-state">
            {searchQuery ? "No matching research" : "No past research yet"}
          </div>
        ) : (
          <div className="sidebar-groups">
            {grouped.today.length > 0 && (
              <div className="sidebar-group">
                <div className="sidebar-group-heading">Today</div>
                {grouped.today.map(renderSessionItem)}
              </div>
            )}

            {grouped.yesterday.length > 0 && (
              <div className="sidebar-group">
                <div className="sidebar-group-heading">Yesterday</div>
                {grouped.yesterday.map(renderSessionItem)}
              </div>
            )}

            {grouped.previous7Days.length > 0 && (
              <div className="sidebar-group">
                <div className="sidebar-group-heading">Previous 7 Days</div>
                {grouped.previous7Days.map(renderSessionItem)}
              </div>
            )}

            {grouped.older.length > 0 && (
              <div className="sidebar-group">
                <div className="sidebar-group-heading">Older</div>
                {grouped.older.map(renderSessionItem)}
              </div>
            )}
          </div>
        )}
      </div>

      {/* User Profile Bar at bottom */}
      <div className="sidebar-user-footer">
        <div className="sidebar-user-info">
          <div className="sidebar-user-avatar">
            {(user?.name || user?.email || "U").charAt(0).toUpperCase()}
            <span className="sidebar-avatar-status" />
          </div>
          <div className="sidebar-user-text">
            <span className="sidebar-user-name">{user?.name || "Researcher"}</span>
            <span className="sidebar-user-email">{user?.email || "Workspace Active"}</span>
          </div>
        </div>
        <button
          type="button"
          className="sidebar-logout-btn"
          onClick={onLogout}
          title="Sign out of AgentIQ"
          aria-label="Log out"
        >
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
        </button>
      </div>
    </aside>
  );
}
