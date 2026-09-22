import { useState } from "react";
import { loginUser, registerUser } from "../services/api";
import logoIcon from "../assets/logo-icon.png";

function Auth({ onLogin }) {
  const [isRegister, setIsRegister] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    if (isRegister) {
      if (!name.trim()) {
        setError("Please enter your full name.");
        return;
      }
      if (!email.trim()) {
        setError("Please enter your email address.");
        return;
      }
      if (password.length < 8) {
        setError("Password must be at least 8 characters long.");
        return;
      }

      setLoading(true);
      try {
        const data = await registerUser(name.trim(), email.trim().toLowerCase(), password);
        onLogin(data.user);
      } catch (err) {
        setError(err.message || "Registration failed. Please try again.");
      } finally {
        setLoading(false);
      }
      return;
    }

    // Login with Email + Password
    if (!email.trim()) {
      setError("Please enter your email address.");
      return;
    }
    if (!password) {
      setError("Please enter your password.");
      return;
    }

    setLoading(true);
    try {
      const data = await loginUser(email.trim().toLowerCase(), password);
      onLogin(data.user);
    } catch (err) {
      setError(err.message || "Invalid email or password");
    } finally {
      setLoading(false);
    }
  }

  function setMode(registerMode) {
    setIsRegister(registerMode);
    setError("");
    setPassword("");
    setShowPassword(false);
  }

  return (
    <div className="auth-page">
      {/* Dynamic Cosmic Glow Background Elements */}
      <div className="auth-nebula auth-nebula--cyan" aria-hidden="true" />
      <div className="auth-nebula auth-nebula--purple" aria-hidden="true" />
      <div className="auth-nebula auth-nebula--blue" aria-hidden="true" />
      <div className="auth-grid-overlay" aria-hidden="true" />

      {/* Main Glassmorphic Auth Card */}
      <div className="auth-card">
        {/* Glow Ring Border */}
        <div className="auth-card-glow-ring" aria-hidden="true" />

        <div className="auth-header">
          {/* Centered Holographic Logo Emblem */}
          <div className="auth-logo-centerpiece">
            <div className="auth-emblem-glow" aria-hidden="true" />
            <div className="auth-emblem-halo">
              <div className="auth-emblem-box">
                <img
                  src={logoIcon}
                  alt="AgentIQ Logo"
                  className="auth-emblem-img"
                />
              </div>
            </div>
          </div>

          <div className="auth-brand-identity">
            <span className="auth-brand-name">
              Agent<span className="auth-brand-name-iq">IQ</span>
            </span>
            <div className="auth-brand-pill">
              <span className="auth-brand-pill-dot" />
              <span>Autonomous AI Intelligence</span>
            </div>
          </div>

          <h1 className="auth-title">
            {isRegister ? "Create Workspace" : "Welcome Back"}
          </h1>

          <p className="auth-subtitle">
            {isRegister
              ? "Join AgentIQ to unlock multi-agent autonomous deep research."
              : "Sign in to access your personal research workspace & reports."}
          </p>

          {/* Interactive Mode Segmented Switcher */}
          <div className="auth-segmented-switcher" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={!isRegister}
              className={`auth-switcher-tab ${!isRegister ? "auth-switcher-tab--active" : ""}`}
              onClick={() => setMode(false)}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
                <polyline points="10 17 15 12 10 7" />
                <line x1="15" y1="12" x2="3" y2="12" />
              </svg>
              <span>Sign In</span>
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={isRegister}
              className={`auth-switcher-tab ${isRegister ? "auth-switcher-tab--active" : ""}`}
              onClick={() => setMode(true)}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <line x1="19" y1="8" x2="19" y2="14" />
                <line x1="22" y1="11" x2="16" y2="11" />
              </svg>
              <span>Create Account</span>
            </button>
          </div>
        </div>

        {/* Error Alert Box */}
        {error && (
          <div className="auth-error-alert" role="alert">
            <div className="auth-error-icon">⚠️</div>
            <div className="auth-error-text">
              <span>{error}</span>
              {(error.toLowerCase().includes("already exists") || error.toLowerCase().includes("409") || error.toLowerCase().includes("sign in")) && isRegister && (
                <div style={{ marginTop: "6px" }}>
                  <button
                    type="button"
                    className="auth-error-action-btn"
                    onClick={() => setMode(false)}
                  >
                    👉 Click here to Sign In →
                  </button>
                </div>
              )}
              {(error.toLowerCase().includes("create an account") || error.toLowerCase().includes("no account")) && !isRegister && (
                <div style={{ marginTop: "6px" }}>
                  <button
                    type="button"
                    className="auth-error-action-btn"
                    onClick={() => setMode(true)}
                  >
                    👉 Click here to Create Account →
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          {/* Full Name field (Register only) */}
          {isRegister && (
            <div className="auth-field">
              <label htmlFor="name">Full Name</label>
              <div className="auth-input-wrapper">
                <span className="auth-input-icon" aria-hidden="true">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                </span>
                <input
                  id="name"
                  type="text"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="e.g. Alex Morgan"
                  required
                  minLength={2}
                  autoComplete="name"
                  className="auth-input--with-icon"
                />
              </div>
            </div>
          )}

          {/* Email field */}
          <div className="auth-field">
            <label htmlFor="auth-email">Email Address</label>
            <div className="auth-input-wrapper">
              <span className="auth-input-icon" aria-hidden="true">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect width="20" height="16" x="2" y="4" rx="2" />
                  <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                </svg>
              </span>
              <input
                id="auth-email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@company.com"
                required
                autoComplete="email"
                className="auth-input--with-icon"
              />
            </div>
          </div>

          {/* Password field */}
          <div className="auth-field">
            <div className="auth-field-header">
              <label htmlFor="auth-password">Password</label>
            </div>
            <div className="auth-input-wrapper">
              <span className="auth-input-icon" aria-hidden="true">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
                  <path d="m7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
              </span>
              <input
                id="auth-password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="••••••••••••"
                required
                minLength={8}
                autoComplete={isRegister ? "new-password" : "current-password"}
                className="auth-input--with-icon auth-input--with-action"
              />
              <button
                type="button"
                className="auth-password-toggle-btn"
                onClick={() => setShowPassword((prev) => !prev)}
                title={showPassword ? "Hide password" : "Show password"}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                    <line x1="1" x2="23" y1="1" y2="23" />
                  </svg>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
            {isRegister && <small className="auth-field-hint">Must be at least 8 characters long.</small>}
          </div>

          <button
            type="submit"
            className="auth-submit-btn"
            disabled={loading}
          >
            {loading ? (
              <span className="auth-submit-loading">
                <span className="loading-spinner" />
                <span>{isRegister ? "Creating workspace..." : "Authenticating..."}</span>
              </span>
            ) : (
              <span className="auth-submit-content">
                <span>{isRegister ? "Create Free Account" : "Sign In to Workspace"}</span>
                <span className="auth-btn-arrow">→</span>
              </span>
            )}
          </button>
        </form>

        <div className="auth-footer-trust">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" className="auth-lock-icon">
            <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
            <path d="m7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          <span>256-Bit SSL Encrypted · Multi-Tenant Workspace Isolation</span>
        </div>
      </div>
    </div>
  );
}

export default Auth;