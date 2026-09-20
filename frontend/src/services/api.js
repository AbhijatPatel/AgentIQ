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

const API_BASE = import.meta.env.VITE_API_BASE || "/api";

// ─── Retry / resilience config ──────────────────────────────────────
const MAX_RETRIES = 3;
const RETRY_BASE_DELAY_MS = 800;   // doubles each attempt
const REQUEST_TIMEOUT_MS = 15_000; // 15-second timeout per attempt

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
 * We retry on:
 *   - Network errors  (TypeError – "Failed to fetch", DNS, socket, etc.)
 *   - 502 / 503 / 504 (backend not yet started or temporarily overloaded)
 *   - AbortError from our own timeout controller
 */
function isRetryable(error, response) {
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

      // If the server returned a retryable status, loop again
      if (isRetryable(null, response) && attempt < MAX_RETRIES) {
        lastError = new Error(`Server returned ${response.status}`);
        continue;
      }

      return response;
    } catch (err) {
      clearTimeout(timeoutId);
      lastError = err;

      if (!isRetryable(err, null) || attempt >= MAX_RETRIES) {
        break;
      }
      // else: loop and retry
    }
  }

  // All retries exhausted – throw a human-readable error
  if (lastError?.name === "AbortError") {
    throw new Error(
      "The server took too long to respond. Please check that the backend is running and try again."
    );
  }
  if (lastError?.name === "TypeError") {
    throw new Error(
      "Could not connect to the server. Please make sure the backend is running on port 8000 and try again."
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
      data.detail || `Could not send verification code (${response.status})`
    );
  }

  return data;
}

/**
 * Register a new user with verified OTP code.
 */
export async function registerUser(name, email, password, code) {
  const response = await apiFetch("/auth/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      name,
      email,
      password,
      code,
    }),
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
  if (!response.ok) throw new Error(data.detail || `Code verification failed (${response.status})`);
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

  if (!response.ok) {
    throw new Error(
      `Failed to get research status (${response.status})`
    );
  }

  return response.json();
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
export async function getResearchHistory(limit = 50) {
  const response = await apiFetch(`/research?limit=${limit}`, {
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