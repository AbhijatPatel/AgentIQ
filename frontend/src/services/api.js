/**
 * API service layer.
 *
 * Every fetch call to the backend goes through here.
 * Authentication tokens are automatically added to protected requests.
 *
 * In development the Vite proxy forwards /api/* → http://localhost:8000/api/*
 * so we use a relative path by default.  In production builds set
 * VITE_API_BASE to the absolute backend URL.
 */

function getApiBase() {
  const envUrl = (
    import.meta.env.VITE_API_URL ||
    import.meta.env.VITE_API_BASE ||
    ""
  ).trim();

  if (envUrl) {
    const cleanUrl = envUrl.replace(/\/+$/, "");
    return cleanUrl.endsWith("/api") ? cleanUrl : `${cleanUrl}/api`;
  }

  // If running in development (localhost), use relative /api with Vite dev proxy
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host === "localhost" || host === "127.0.0.1") {
      return "/api";
    }
  }

  // Default production backend URL on Render
  return "https://agentiq-backend-4ik5.onrender.com/api";
}

const API_BASE = getApiBase();

// ─── Retry / resilience config ──────────────────────────────────────
const MAX_RETRIES = 2;
const RETRY_BASE_DELAY_MS = 1000;  // doubles each attempt
const REQUEST_TIMEOUT_MS = 60_000; // 60-second timeout per attempt to accommodate Render cold starts

/**
 * Get authentication headers for protected API requests.
 */
function getAuthHeaders() {
  const token = localStorage.getItem("agentiq_token");

  if (!token) {
    return {};
  }

  return {
    Authorization: `Bearer ${token}`,
  };
}

/**
 * Determine whether a failed request is worth retrying.
 *
 * We retry only idempotent GET requests on:
 *   - Network errors  (TypeError – "Failed to fetch", DNS, socket, etc.)
 *   - 502 / 503 / 504 (backend not yet started or temporarily overloaded)
 *   - AbortError from our own timeout controller
 *
 * Non-GET requests (POST, PUT, DELETE) are NOT retried automatically
 * to prevent duplicate research session creations or duplicated operations.
 */
function isRetryable(error, response, method = "GET") {
  if (method.toUpperCase() !== "GET") {
    return false;
  }
  if (error && (error.name === "TypeError" || error.name === "AbortError")) {
    return true;
  }
  if (response && [502, 503, 504].includes(response.status)) {
    return true;
  }
  return false;
}

/**
 * Central fetch wrapper with timeout, retry + exponential back-off,
 * and user-friendly error messages.
 *
 * @param {string}       path     – path relative to API_BASE (e.g. "/auth/login")
 * @param {RequestInit}  options  – standard fetch options
 * @returns {Promise<Response>}
 */
async function apiFetch(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const method = (options.method || "GET").toUpperCase();
  let lastError;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    // Wait before retrying (skip delay on first attempt)
    if (attempt > 0) {
      const delay = RETRY_BASE_DELAY_MS * 2 ** (attempt - 1);
      await new Promise((r) => setTimeout(r, delay));
    }

    // Per-request timeout so we don't hang forever
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      // Handle 401 Unauthorized (expired token or wiped session)
      if (response.status === 401 && !path.includes("/auth/login") && !path.includes("/auth/register")) {
        localStorage.removeItem("agentiq_token");
        localStorage.removeItem("agentiq_user");
        if (typeof window !== "undefined") {
          window.dispatchEvent(new Event("agentiq_auth_expired"));
        }
      }

      // If the server returned a retryable status, loop again
      if (isRetryable(null, response, method) && attempt < MAX_RETRIES) {
        lastError = new Error(`Server returned ${response.status}`);
        continue;
      }

      return response;
    } catch (err) {
      clearTimeout(timeoutId);
      lastError = err;

      if (!isRetryable(err, null, method) || attempt >= MAX_RETRIES) {
        break;
      }
      // else: loop and retry
    }
  }

  // All retries exhausted – throw a human-readable error with backend context
  if (lastError?.name === "AbortError") {
    throw new Error(
      "The server request timed out. If the backend is waking up from a cold start, please retry in a moment."
    );
  }
  if (lastError?.name === "TypeError") {
    throw new Error(
      `Network error: Could not reach backend server (${lastError.message || "Failed to fetch"}). Please check backend status and retry.`
    );
  }
  throw new Error(
    lastError?.message ||
      "An unexpected network error occurred. Please try again."
  );
}

/**
 * Parse a JSON body from a response, returning a safe fallback on failure.
 */
async function parseJSON(response) {
  try {
    return await response.json();
  } catch {
    return {};
  }
}

// ─── Auth helpers ───────────────────────────────────────────────────

/**
 * Request an email verification OTP for registration.
 */
export async function requestRegisterOtp(name, email, password) {
  const response = await apiFetch("/auth/register/request-otp", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      name,
      email,
      password,
    }),
  });

  const data = await parseJSON(response);

  if (!response.ok) {
    throw new Error(
      data.message || data.detail || `Could not send verification code (${response.status})`
    );
  }

  return data;
}

/**
 * Register a new user with name, email, and password.
 */
export async function registerUser(name, email, password, code = null) {
  const payload = { name, email, password };
  if (code) {
    payload.code = code;
  }

  const response = await apiFetch("/auth/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await parseJSON(response);

  if (!response.ok) {
    throw new Error(
      data.detail || `Registration failed (${response.status})`
    );
  }

  localStorage.setItem("agentiq_token", data.access_token);
  localStorage.setItem("agentiq_user", JSON.stringify(data.user));

  return data;
}

/**
 * Login an existing user.
 */
export async function loginUser(email, password) {
  const response = await apiFetch("/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email,
      password,
    }),
  });

  const data = await parseJSON(response);

  if (!response.ok) {
    throw new Error(
      data.detail || `Login failed (${response.status})`
    );
  }

  localStorage.setItem("agentiq_token", data.access_token);
  localStorage.setItem("agentiq_user", JSON.stringify(data.user));

  return data;
}

export async function requestOtp(email) {
  const response = await apiFetch("/auth/otp/request", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  const data = await parseJSON(response);
  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(data.detail || "No account exists with this email. Please create an account first.");
    }
    throw new Error(data.detail || `Could not send code (${response.status})`);
  }
  return data;
}

export async function verifyOtp(email, code) {
  const response = await apiFetch("/auth/otp/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, code }),
  });
  const data = await parseJSON(response);
  if (!response.ok) throw new Error(data.message || data.detail || `Code verification failed (${response.status})`);
  localStorage.setItem("agentiq_token", data.access_token);
  localStorage.setItem("agentiq_user", JSON.stringify(data.user));
  return data;
}

/**
 * Logout the current user.
 */
export function logoutUser() {
  localStorage.removeItem("agentiq_token");
  localStorage.removeItem("agentiq_user");
}

/**
 * Get the currently stored user.
 */
export function getStoredUser() {
  const user = localStorage.getItem("agentiq_user");

  if (!user) {
    return null;
  }

  try {
    return JSON.parse(user);
  } catch {
    return null;
  }
}

/**
 * Check whether a JWT token exists.
 */
export function isAuthenticated() {
  return Boolean(localStorage.getItem("agentiq_token"));
}

/**
 * Start a new research task.
 *
 * Requires authentication.
 */
export async function startResearch(goal) {
  const response = await apiFetch("/research", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ goal }),
  });

  const data = await parseJSON(response);

  if (!response.ok) {
    throw new Error(
      data.detail ||
        data.message ||
        `Failed to start research (${response.status})`
    );
  }

  return data;
}

/**
 * Get research status/result.
 */
export async function getResearchStatus(researchId) {
  const response = await apiFetch(`/research/${researchId}`, {
    headers: {
      ...getAuthHeaders(),
    },
  });

  const data = await parseJSON(response);

  if (!response.ok) {
    throw new Error(
      data.detail ||
        data.message ||
        `Failed to get research status (${response.status})`
    );
  }

  return data;
}

/**
 * Get the Server-Sent Events stream URL.
 *
 * The current backend SSE endpoint receives the JWT through
 * the query parameter because browser EventSource does not
 * support custom Authorization headers.
 */
export function getResearchStreamUrl(researchId) {
  const token = localStorage.getItem("agentiq_token");

  if (!token) {
    return `${API_BASE}/research/${researchId}/stream`;
  }

  return `${API_BASE}/research/${researchId}/stream?token=${encodeURIComponent(
    token
  )}`;
}

/**
 * List recent research sessions for history view.
 */
export async function getResearchHistory(limit = 50, search = "") {
  let path = `/research?limit=${limit}`;
  if (search && search.trim()) {
    path += `&search=${encodeURIComponent(search.trim())}`;
  }
  const response = await apiFetch(path, {
    headers: {
      ...getAuthHeaders(),
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to load research history (${response.status})`);
  }

  return parseJSON(response);
}

/**
 * Delete a research session.
 */
export async function deleteResearchSession(researchId) {
  const response = await apiFetch(`/research/${researchId}`, {
    method: "DELETE",
    headers: {
      ...getAuthHeaders(),
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to delete research session (${response.status})`);
  }

  return parseJSON(response);
}

/**
 * Upload a document or image to the RAG knowledge store.
 * @param {File} file
 * @returns {Promise<{ filename: string, chunks_added: number, status: string }>}
 */
export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiFetch("/documents/upload", {
    method: "POST",
    headers: {
      ...getAuthHeaders(),
      // Note: do not set Content-Type header so browser sets multipart boundary automatically
    },
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Upload failed (${response.status})`);
  }

  return response.json();
}