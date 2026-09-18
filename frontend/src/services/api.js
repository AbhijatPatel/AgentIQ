/**
 * API service layer.
 *
 * Every fetch call to the backend goes through here.
 * Authentication tokens are automatically added to protected requests.
 */

const API_BASE = "http://localhost:8000/api";

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
 * Register a new user.
 */
export async function registerUser(name, email, password) {
  const response = await fetch(`${API_BASE}/auth/register`, {
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

  const data = await response.json().catch(() => ({}));

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
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email,
      password,
    }),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      data.detail || `Login failed (${response.status})`
    );
  }

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
  const response = await fetch(`${API_BASE}/research`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ goal }),
  });

  const data = await response.json().catch(() => ({}));

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
  const response = await fetch(`${API_BASE}/research/${researchId}`, {
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