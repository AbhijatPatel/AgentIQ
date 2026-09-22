/**
 * API service layer with high-resilience network and cold-start recovery.
 *
 * Features:
 * - Automatic detection of environment variables and fallback cloud endpoints
 * - Connection-level retries across all HTTP methods (handles Render free-tier cold starts)
 * - Exponential backoff with jitter on 502/503/504 gateway errors and socket resets
 * - Transparent fallback from disconnected localhost to live cloud API
 * - Proactive background server warmup
 */

const CLOUD_API_BASE = "https://agentiq-backend-4ik5.onrender.com/api";

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

  // If running in development on localhost, default to proxy with fallback to cloud
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host === "localhost" || host === "127.0.0.1") {
      return "/api";
    }
  }

  return CLOUD_API_BASE;
}

let currentApiBase = getApiBase();

export function getEffectiveApiBase() {
  return currentApiBase;
}

// ─── Retry / resilience config ──────────────────────────────────────
const MAX_RETRIES = 3;
const RETRY_BASE_DELAY_MS = 1500;
const REQUEST_TIMEOUT_MS = 75_000; // 75 seconds to smoothly absorb Render free-tier container wakeups

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
 * Determine whether a failed request is safe to retry.
 *
 * We retry:
 * 1. Connection-level network failures (TypeError: Failed to fetch, DNS failure, TCP reset)
 *    because the server NEVER received or executed the request.
 * 2. 502 (Bad Gateway), 503 (Service Unavailable), 504 (Gateway Timeout) from Render's proxy
 *    which indicate the container is booting up.
 * 3. AbortError if our client timeout triggered during server startup.
 */
function isConnectionOrGatewayError(error, response) {
  if (error && (error.name === "TypeError" || error.name === "AbortError")) {
    return true;
  }
  if (response && [502, 503, 504].includes(response.status)) {
    return true;
  }
  return false;
}

/**
 * Central fetch wrapper with timeout, auto-recovering retry logic,
 * and transparent local-to-cloud failover.
 *
 * @param {string}       path     – path relative to API_BASE (e.g. "/auth/login")
 * @param {RequestInit}  options  – standard fetch options
 * @returns {Promise<Response>}
 */
async function apiFetch(path, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  let lastError;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    // Wait before retrying (exponential backoff)
    if (attempt > 0) {
      const delay = RETRY_BASE_DELAY_MS * (2 ** (attempt - 1)) + Math.random() * 400;
      await new Promise((r) => setTimeout(r, delay));
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    const url = `${currentApiBase}${path}`;

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

      // If Render edge proxy returned 502/503/504 while waking up, retry
      if (isConnectionOrGatewayError(null, response) && attempt < MAX_RETRIES) {
        // If local dev proxy returned 502 because local backend is not running, failover to cloud
        if (currentApiBase === "/api" && response.status === 502) {
          console.warn("[AgentIQ API] Local backend not reachable. Auto-switching to cloud backend:", CLOUD_API_BASE);
          currentApiBase = CLOUD_API_BASE;
        }
        lastError = new Error(`Backend server initializing (${response.status})`);
        continue;
      }

      return response;
    } catch (err) {
      clearTimeout(timeoutId);
      lastError = err;

      // If local dev fetch threw a TypeError (connection refused), failover to cloud backend
      if (currentApiBase === "/api" && err && err.name === "TypeError") {
        console.warn("[AgentIQ API] Localhost connection failed. Auto-switching to cloud backend:", CLOUD_API_BASE);
        currentApiBase = CLOUD_API_BASE;
      }

      if (!isConnectionOrGatewayError(err, null) || attempt >= MAX_RETRIES) {
        break;
      }
      // Continue next attempt
    }
  }

  // All retries exhausted – throw user-friendly error with guidance
  if (lastError?.name === "AbortError") {
    throw new Error(
      "The server is taking longer than usual to wake up from sleep mode. Please retry in a few seconds."
    );
  }
  if (lastError?.name === "TypeError") {
    throw new Error(
      `Could not establish connection to the backend server. The server may be waking up. Please retry in a moment.`
    );
  }
  throw new Error(
    lastError?.message ||
      "Unable to connect to the backend server. Please check your network connection and retry."
  );
}

/**
 * Proactive server warmup: triggers non-blocking ping to ensure backend is warm.
 */
export async function warmupBackend() {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000);
    await fetch(`${currentApiBase}/health`, {
      method: "GET",
      signal: controller.signal,
      mode: "cors",
    });
    clearTimeout(timeoutId);
  } catch {
    // Non-blocking background warmup
  }
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
    if (response.status === 409) {
      throw new Error(data.message || data.detail || "An account with this email already exists. Please sign in.");
    }
    if (response.status === 422) {
      throw new Error(data.message || data.detail || "Invalid registration details. Please verify your inputs.");
    }
    if (response.status === 429) {
      throw new Error("Too many registration requests. Please wait a moment and try again.");
    }
    if (response.status >= 500) {
      throw new Error(data.message || data.detail || "Registration service temporarily unavailable. Please try again later.");
    }
    throw new Error(
      data.message || data.detail || `Registration failed (${response.status})`
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
    if (response.status === 401) {
      throw new Error(data.message || data.detail || "Invalid email or password.");
    }
    if (response.status === 404) {
      throw new Error(data.message || data.detail || "No account found with this email. Please register first.");
    }
    if (response.status === 429) {
      throw new Error("Too many login attempts. Please wait a moment and try again.");
    }
    if (response.status >= 500) {
      throw new Error(data.message || data.detail || "Authentication service temporarily unavailable. Please try again later.");
    }
    throw new Error(
      data.message || data.detail || `Login failed (${response.status})`
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
 * Rename a research session.
 */
export async function renameResearchSession(researchId, title) {
  const response = await apiFetch(`/research/${researchId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ title }),
  });

  if (!response.ok) {
    const data = await parseJSON(response);
    throw new Error(data.detail || data.message || `Failed to rename research session (${response.status})`);
  }

  return parseJSON(response);
}

/**
 * Clear all research sessions from history.
 */
export async function clearAllResearchHistory() {
  try {
    const response = await apiFetch("/research", {
      method: "DELETE",
      headers: {
        ...getAuthHeaders(),
      },
    });

    if (response.ok) {
      return parseJSON(response);
    }
  } catch (err) {
    console.warn("DELETE /research failed, trying POST /research/clear fallback:", err);
  }

  // Fallback endpoint in case of intermediate proxy restrictions on DELETE
  const fallbackResponse = await apiFetch("/research/clear", {
    method: "POST",
    headers: {
      ...getAuthHeaders(),
    },
  });

  if (!fallbackResponse.ok) {
    throw new Error(`Failed to clear research history (${fallbackResponse.status})`);
  }

  return parseJSON(fallbackResponse);
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