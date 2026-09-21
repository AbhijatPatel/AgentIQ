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

  function switchMode() {
    setIsRegister((prev) => !prev);
    setError("");
    setName("");
    setEmail("");
    setPassword("");
    setShowPassword(false);
  }

  return (
    <div className="auth-page">
      <div className="auth-card-backdrop-glow" aria-hidden="true" />
      <div className="auth-card">
        <div className="auth-header">
          <div className="auth-brand-lockup">
            <div className="auth-emblem-frame">
              <img src={logoIcon} alt="AgentIQ Logo" className="auth-brand-emblem-img" />
            </div>
            <div className="auth-brand-identity">
              <span className="auth-brand-name">
                Agent<span className="auth-brand-name-iq">IQ</span>
              </span>
              <span className="auth-brand-pill">
                <span className="auth-brand-pill-dot" /> Autonomous AI
              </span>
            </div>
          </div>

          <h1 className="auth-title">
            {isRegister ? "Create your account" : "Welcome back"}
          </h1>

          <p className="auth-subtitle">
            {isRegister
              ? "Join AgentIQ to unlock autonomous intelligence workflows."
              : "Sign in with your email and password to continue."}
          </p>
        </div>

        {error && (
          <div className={`error-alert ${error.includes("connect") || error.includes("server") ? "error-alert--network" : ""}`}>
            <span className="error-alert-icon" aria-hidden="true">⚠️</span>
            <div className="error-alert-content">
              <span>{error}</span>
              {(error.toLowerCase().includes("create an account") || error.toLowerCase().includes("no account")) && !isRegister && (
                <div style={{ marginTop: "6px" }}>
                  <button
                    type="button"
                    className="auth-link-btn"
                    style={{ fontWeight: 600, textDecoration: "underline" }}
                    onClick={() => {
                      setIsRegister(true);
                      setError("");
                    }}
                  >
                    Click here to Create Account with this email →
                  </button>
                </div>
              )}
              {(error.includes("connect") || error.includes("server")) && (
                <small style={{ display: "block", marginTop: "4px", opacity: 0.85 }}>
                  Tip: Run <code>start-dev.ps1</code> to start the backend server.
                </small>
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
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                </span>
                <input
                  id="name"
                  type="text"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="Enter your name"
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
            <label htmlFor="auth-email">Email address</label>
            <div className="auth-input-wrapper">
              <span className="auth-input-icon" aria-hidden="true">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect width="20" height="16" x="2" y="4" rx="2" />
                  <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                </svg>
              </span>
              <input
                id="auth-email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="name@company.com"
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
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
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
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                    <line x1="1" x2="23" y1="1" y2="23" />
                  </svg>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
            {isRegister && <small>Must be at least 8 characters long.</small>}
          </div>

          <button
            type="submit"
            className="auth-submit-btn"
            disabled={loading}
          >
            {loading ? (
              <span className="auth-submit-loading">
                <span className="loading-spinner" />
                {isRegister ? "Creating account..." : "Signing in..."}
              </span>
            ) : isRegister ? (
              "Create Account"
            ) : (
              "Sign In"
            )}
          </button>
        </form>

        <div className="auth-switch">
          <span>
            {isRegister
              ? "Already have an account?"
              : "Don't have an account?"}
          </span>

          <button type="button" onClick={switchMode} className="auth-toggle-link">
            {isRegister ? "Sign In" : "Create Account"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default Auth;