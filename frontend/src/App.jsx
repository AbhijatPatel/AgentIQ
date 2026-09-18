import { useState } from "react";
import "./App.css";
import Dashboard from "./pages/Dashboard";
import Auth from "./components/Auth";
import {
  getStoredUser,
  isAuthenticated,
  logoutUser,
} from "./services/api";

function App() {
  const [authenticated, setAuthenticated] = useState(isAuthenticated());
  const [user, setUser] = useState(getStoredUser());

  function handleLogin(loggedInUser) {
    setUser(loggedInUser);
    setAuthenticated(true);
  }

  function handleLogout() {
    logoutUser();
    setUser(null);
    setAuthenticated(false);
  }

  if (!authenticated) {
    return (
      <div className="app-shell">
        <div className="app-container">
          <Auth onLogin={handleLogin} />
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <div className="app-container">
        <div className="user-bar">
          <div>
            <strong>Welcome, {user?.name || "User"}</strong>
            <span className="user-email">{user?.email}</span>
          </div>

          <button
            type="button"
            className="secondary-btn logout-btn"
            onClick={handleLogout}
          >
            Logout
          </button>
        </div>

        <Dashboard />
      </div>
    </div>
  );
}

export default App;