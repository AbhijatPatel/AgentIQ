import { useState, useEffect } from "react";
import "./App.css";
import Dashboard from "./pages/Dashboard";
import HistoryPage from "./pages/HistoryPage";
import Auth from "./components/Auth";
import Sidebar from "./components/Sidebar";
import { useResearch } from "./hooks/useResearch";
import {
  getStoredUser,
  isAuthenticated,
  logoutUser,
  getResearchStatus,
} from "./services/api";
import logoIcon from "./assets/logo-icon.png";

function App() {
  const [authenticated, setAuthenticated] = useState(isAuthenticated());
  const [user, setUser] = useState(getStoredUser());
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // View state: "research" or "history"
  const [currentView, setCurrentView] = useState(() => {
    return window.location.hash === "#history" ? "history" : "research";
  });

  // Shared research state so ongoing tasks are preserved when browsing history
  const researchHook = useResearch();

  // Listen to browser hash changes (e.g. back/forward buttons)
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace("#", "");
      if (hash === "history" || hash === "research") {
        setCurrentView(hash);
      }
    };

    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  // Listen for session expiry from API responses
  useEffect(() => {
    function handleAuthExpired() {
      setAuthenticated(false);
      setUser(null);
    }
    window.addEventListener("agentiq_auth_expired", handleAuthExpired);
    return () => window.removeEventListener("agentiq_auth_expired", handleAuthExpired);
  }, []);

  const handleNavigate = (view) => {
    setCurrentView(view);
    window.location.hash = view;
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleSelectHistorySession = async (researchId) => {
    try {
      const sessionData = await getResearchStatus(researchId);
      researchHook.loadPastSession(sessionData);
      handleNavigate("research");
      setSidebarOpen(false);
    } catch (err) {
      console.error("Failed to load session details:", err);
    }
  };

  const handleStartNewResearch = () => {
    researchHook.reset();
    handleNavigate("research");
    setSidebarOpen(false);
  };

  function handleLogin(loggedInUser) {
    setUser(loggedInUser);
    setAuthenticated(true);
    setSidebarOpen(false);
  }

  function handleLogout() {
    logoutUser();
    setUser(null);
    setAuthenticated(false);
    setSidebarOpen(false);
  }

  if (!authenticated) {
    return (
      <div className="app-shell">
        <div className="auth-container">
          <Auth onLogin={handleLogin} />
        </div>
      </div>
    );
  }

  return (
    <div className="app-layout-workspace">
      {/* ChatGPT-style Left Sidebar (only opens when clicked) */}
      <Sidebar
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen((prev) => !prev)}
        activeResearchId={researchHook.researchId}
        onSelectSession={handleSelectHistorySession}
        onStartNewResearch={handleStartNewResearch}
        user={user}
        onLogout={handleLogout}
      />

      {/* Backdrop overlay when sidebar is open */}
      {sidebarOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Main Workspace Frame */}
      <div className="main-content-wrapper">
        {/* Top Navigation */}
        <nav className="top-nav" aria-label="Primary navigation">
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <button
              type="button"
              className="sidebar-nav-toggle-btn"
              onClick={() => setSidebarOpen((prev) => !prev)}
              title={sidebarOpen ? "Close sidebar menu" : "Open sidebar menu"}
              aria-label="Toggle sidebar menu"
            >
              <svg
                viewBox="0 0 24 24"
                width="18"
                height="18"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>

            <button
              type="button"
              className="brand-lockup-btn"
              onClick={() => handleNavigate("research")}
              aria-label="AgentIQ research home"
            >
              <div className="brand-logo-frame">
                <img src={logoIcon} alt="AgentIQ Logo" className="brand-logo-img" />
              </div>
              <span className="brand-name">
                Agent<span className="brand-name-iq">IQ</span>
              </span>
            </button>
          </div>

          <div className="nav-segmented-pill" role="tablist" aria-label="Main application sections">
            <button
              type="button"
              role="tab"
              aria-selected={currentView === "research"}
              className={`nav-pill-btn ${
                currentView === "research" ? "nav-pill-btn--active" : ""
              }`}
              onClick={() => handleNavigate("research")}
            >
              <svg
                viewBox="0 0 24 24"
                width="14"
                height="14"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              <span>Workspace</span>
              {researchHook.status === "running" && (
                <span className="nav-running-indicator" title="Research in progress" />
              )}
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={currentView === "history"}
              className={`nav-pill-btn ${
                currentView === "history" ? "nav-pill-btn--active" : ""
              }`}
              onClick={() => handleNavigate("history")}
            >
              <svg
                viewBox="0 0 24 24"
                width="14"
                height="14"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M12 8v4l3 3" />
                <circle cx="12" cy="12" r="9" />
              </svg>
              <span>History Library</span>
            </button>
          </div>

          <div className="user-profile-widget">
            <div className="user-badge">
              <div className="user-avatar-wrapper">
                <span className="user-avatar" aria-hidden="true">
                  {(user?.name || user?.email || "U").charAt(0).toUpperCase()}
                </span>
                <span className="user-status-dot" title="Active session" />
              </div>
              <div className="user-details">
                <span className="user-display-name">{user?.name || "Researcher"}</span>
                <span className="user-role-badge">Pro Workspace</span>
              </div>
            </div>
          </div>
        </nav>

        {/* Main View Area */}
        <main className="app-container">
          {currentView === "research" ? (
            <Dashboard
              researchHook={researchHook}
              onNavigateToHistory={() => handleNavigate("history")}
            />
          ) : (
            <HistoryPage
              onSelectSession={handleSelectHistorySession}
              onStartNewResearch={handleStartNewResearch}
            />
          )}
        </main>
      </div>
    </div>
  );
}

export default App;