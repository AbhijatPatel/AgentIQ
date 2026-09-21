import { useState, useEffect, useRef } from "react";
import {
  loginUser,
  registerUser,
  requestOtp,
  verifyOtp,
  requestRegisterOtp,
} from "../services/api";
import logoIcon from "../assets/logo-icon.png";

function Auth({ onLogin }) {
  const [isRegister, setIsRegister] = useState(false);
  const [useOtp, setUseOtp] = useState(false);
  const [otpSent, setOtpSent] = useState(false);
  const [otp, setOtp] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [devHint, setDevHint] = useState("");
  const [loading, setLoading] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  const otpInputRef = useRef(null);

  // Cooldown countdown timer for resending OTP
  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setInterval(() => {
      setCooldown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [cooldown]);

  // Auto-focus OTP input when arriving at verification step
  useEffect(() => {
    if (otpSent && otpInputRef.current) {
      otpInputRef.current.focus();
    }
  }, [otpSent]);

  async function handleDirectRegister(e) {
    if (e && e.preventDefault) e.preventDefault();
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

    setError("");
    setDevHint("");
    setLoading(true);

    try {
      const data = await registerUser(name, email, password, null);
      onLogin(data.user);
    } catch (err) {
      setError(err.message || "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleSendRegistrationOtp() {
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

    setError("");
    setDevHint("");
    setLoading(true);

    try {
      const res = await requestRegisterOtp(name, email, password);
      setOtpSent(true);
      setCooldown(60);
      if (res.dev_code) {
        setDevHint(`Dev hint: Your verification code is ${res.dev_code}`);
        setOtp(res.dev_code);
      }
    } catch (err) {
      setError(err.message || "Failed to send verification code");
    } finally {
      setLoading(false);
    }
  }

  async function handleSendLoginOtp() {
    if (!email.trim()) {
      setError("Please enter your email address.");
      return;
    }

    setError("");
    setDevHint("");
    setLoading(true);

    try {
      const res = await requestOtp(email);
      setOtpSent(true);
      setCooldown(60);
      if (res.dev_code) {
        setDevHint(`Dev hint: Your login code is ${res.dev_code}`);
        setOtp(res.dev_code);
      }
    } catch (err) {
      setError(err.message || "Failed to send login code");
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    // If registering - standard flow is email verification
    if (isRegister) {
      if (!otpSent) {
        await handleSendRegistrationOtp();
        return;
      }

      if (!otp || otp.length < 6) {
        setError("Please enter the 6-digit verification code sent to your email.");
        return;
      }

      setLoading(true);
      try {
        const data = await registerUser(name, email, password, otp);
        onLogin(data.user);
      } catch (err) {
        setError(err.message || "Verification failed");
      } finally {
        setLoading(false);
      }
      return;
    }

    // If logging in with OTP and OTP has not been sent yet
    if (!isRegister && useOtp && !otpSent) {
      await handleSendLoginOtp();
      return;
    }

    // Verification / password login step
    setLoading(true);

    try {
      let data;
      if (useOtp) {
        data = await verifyOtp(email, otp);
      } else {
        data = await loginUser(email, password);
      }

      onLogin(data.user);
    } catch (err) {
      setError(err.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  function switchMode() {
    setIsRegister((current) => !current);
    setError("");
    setDevHint("");
    setName("");
    setEmail("");
    setPassword("");
    setOtp("");
    setUseOtp(false);
    setOtpSent(false);
    setShowPassword(false);
    setCooldown(0);
  }

  function handleBackToDetails() {
    setOtpSent(false);
    setOtp("");
    setError("");
    setDevHint("");
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
            {isRegister
              ? otpSent
                ? "Verify your email"
                : "Create your account"
              : useOtp && otpSent
              ? "Enter login code"
              : "Welcome back"}
          </h1>

          <p className="auth-subtitle">
            {isRegister ? (
              otpSent ? (
                <>
                  We sent a 6-digit verification code to{" "}
                  <strong className="auth-email-highlight">{email}</strong>.
                </>
              ) : (
                "Join AgentIQ to unlock autonomous intelligence workflows."
              )
            ) : useOtp && otpSent ? (
              <>
                Enter the 6-digit code sent to{" "}
                <strong className="auth-email-highlight">{email}</strong>.
              </>
            ) : (
              "Sign in to continue your AI research journey."
            )}
          </p>
        </div>

        {error && (
          <div className={`error-alert ${error.includes("connect") || error.includes("server") ? "error-alert--network" : ""}`}>
            <span className="error-alert-icon" aria-hidden="true">⚠️</span>
            <div className="error-alert-content">
              <span>{error}</span>
              {isRegister && (
                <div style={{ marginTop: "8px" }}>
                  <button
                    type="button"
                    className="auth-link-btn"
                    style={{ fontWeight: 600, textDecoration: "underline", color: "#4f46e5" }}
                    onClick={handleDirectRegister}
                  >
                    ⚡ Create Account directly with Password (skip email verification) →
                  </button>
                </div>
              )}
              {(error.toLowerCase().includes("create an account") || error.toLowerCase().includes("no account")) && !isRegister && (
                <div style={{ marginTop: "6px" }}>
                  <button
                    type="button"
                    className="auth-link-btn"
                    style={{ fontWeight: 600, textDecoration: "underline" }}
                    onClick={() => {
                      setIsRegister(true);
                      setError("");
                      setOtpSent(false);
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

        {devHint && (
          <div className="auth-dev-hint-banner" role="status">
            <span className="auth-dev-icon" aria-hidden="true">💡</span>
            <span>{devHint}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          {/* REGISTRATION STEP 1: Name, Email, Password */}
          {isRegister && !otpSent && (
            <>
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

              <div className="auth-field">
                <label htmlFor="email">Email address</label>
                <div className="auth-input-wrapper">
                  <span className="auth-input-icon" aria-hidden="true">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect width="20" height="16" x="2" y="4" rx="2" />
                      <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                    </svg>
                  </span>
                  <input
                    id="email"
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

              <div className="auth-field">
                <div className="auth-field-header">
                  <label htmlFor="password">Password</label>
                </div>
                <div className="auth-input-wrapper">
                  <span className="auth-input-icon" aria-hidden="true">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
                      <path d="m7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                  </span>
                  <input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="••••••••••••"
                    required
                    minLength={8}
                    autoComplete="new-password"
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
                <small>Must be at least 8 characters long.</small>
              </div>
            </>
          )}

          {/* REGISTRATION STEP 2: OTP Verification */}
          {isRegister && otpSent && (
            <div className="auth-otp-block">
              <div className="auth-field">
                <label htmlFor="reg-otp">6-Digit Verification Code</label>
                <div className="auth-input-wrapper">
                  <span className="auth-input-icon" aria-hidden="true">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
                      <path d="m7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                  </span>
                  <input
                    id="reg-otp"
                    ref={otpInputRef}
                    inputMode="numeric"
                    value={otp}
                    onChange={(event) =>
                      setOtp(event.target.value.replace(/\D/g, "").slice(0, 6))
                    }
                    placeholder="000000"
                    required
                    minLength={6}
                    maxLength={6}
                    autoComplete="one-time-code"
                    className="auth-input--with-icon auth-input--otp"
                  />
                </div>
              </div>

              <div className="auth-resend-row">
                <button
                  type="button"
                  className="auth-link-btn"
                  onClick={handleBackToDetails}
                >
                  ← Edit details
                </button>

                <button
                  type="button"
                  className="auth-link-btn"
                  style={{ color: "#4f46e5", fontWeight: 650 }}
                  onClick={handleDirectRegister}
                >
                  ⚡ Skip code & Register
                </button>

                <button
                  type="button"
                  className="auth-link-btn"
                  disabled={cooldown > 0 || loading}
                  onClick={handleSendRegistrationOtp}
                >
                  {cooldown > 0 ? `Resend (${cooldown}s)` : "Resend code"}
                </button>
              </div>
            </div>
          )}

          {/* LOGIN VIEW: Email & Password or OTP */}
          {!isRegister && (
            <>
              <div className="auth-field">
                <label htmlFor="login-email">Email address</label>
                <div className="auth-input-wrapper">
                  <span className="auth-input-icon" aria-hidden="true">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect width="20" height="16" x="2" y="4" rx="2" />
                      <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                    </svg>
                  </span>
                  <input
                    id="login-email"
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="name@company.com"
                    required
                    autoComplete="email"
                    disabled={useOtp && otpSent}
                    className="auth-input--with-icon"
                  />
                </div>
              </div>

              {/* Password field when NOT using OTP */}
              {!useOtp && (
                <div className="auth-field">
                  <div className="auth-field-header">
                    <label htmlFor="login-password">Password</label>
                  </div>
                  <div className="auth-input-wrapper">
                    <span className="auth-input-icon" aria-hidden="true">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
                        <path d="m7 11V7a5 5 0 0 1 10 0v4" />
                      </svg>
                    </span>
                    <input
                      id="login-password"
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      placeholder="••••••••••••"
                      required
                      minLength={8}
                      autoComplete="current-password"
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
                </div>
              )}

              {/* Login OTP field */}
              {useOtp && otpSent && (
                <div className="auth-otp-block">
                  <div className="auth-field">
                    <label htmlFor="login-otp">6-Digit Login Code</label>
                    <div className="auth-input-wrapper">
                      <span className="auth-input-icon" aria-hidden="true">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
                          <path d="m7 11V7a5 5 0 0 1 10 0v4" />
                        </svg>
                      </span>
                      <input
                        id="login-otp"
                        ref={otpInputRef}
                        inputMode="numeric"
                        value={otp}
                        onChange={(event) =>
                          setOtp(event.target.value.replace(/\D/g, "").slice(0, 6))
                        }
                        placeholder="000000"
                        required
                        minLength={6}
                        maxLength={6}
                        autoComplete="one-time-code"
                        className="auth-input--with-icon auth-input--otp"
                      />
                    </div>
                  </div>

                  <div className="auth-resend-row">
                    <button
                      type="button"
                      className="auth-link-btn"
                      onClick={handleBackToDetails}
                    >
                      ← Change email
                    </button>

                    <button
                      type="button"
                      className="auth-link-btn"
                      disabled={cooldown > 0 || loading}
                      onClick={handleSendLoginOtp}
                    >
                      {cooldown > 0 ? `Resend code (${cooldown}s)` : "Resend code"}
                    </button>
                  </div>
                </div>
              )}
            </>
          )}

          <button
            type="submit"
            className="auth-submit-btn"
            disabled={loading}
          >
            {loading ? (
              <span className="auth-submit-loading">
                <span className="loading-spinner" />
                {isRegister
                  ? otpSent
                    ? "Verifying code..."
                    : "Sending code..."
                  : useOtp
                  ? otpSent
                    ? "Verifying code..."
                    : "Sending code..."
                  : "Signing in..."}
              </span>
            ) : isRegister ? (
              otpSent ? (
                "Verify & Create Account"
              ) : (
                "Continue with Verification Code →"
              )
            ) : useOtp ? (
              otpSent ? (
                "Verify & Sign In"
              ) : (
                "Send Login Code"
              )
            ) : (
              "Sign In"
            )}
          </button>
        </form>

        {isRegister ? (
          <button
            type="button"
            className="auth-mode-switch"
            onClick={handleDirectRegister}
            title="Create account immediately using your password without email verification"
          >
            ⚡ Or create account directly with password
          </button>
        ) : (
          <button
            type="button"
            className="auth-mode-switch"
            onClick={() => {
              setUseOtp((current) => !current);
              setOtpSent(false);
              setOtp("");
              setError("");
              setDevHint("");
            }}
          >
            {useOtp ? "Use password instead" : "Sign in with email code"}
          </button>
        )}

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