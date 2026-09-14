/**
 * API service layer.
 *
 * Every fetch call to the backend goes through here - components never
 * call fetch() directly. This keeps the base URL and error handling
 * in one place.
 */

const API_BASE = "http://localhost:8000/api";

export async function startResearch(goal) {
  const response = await fetch(`${API_BASE}/research`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ goal }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to start research (${response.status})`);
  }

  return response.json(); // { research_id, status }
}

export async function getResearchStatus(researchId) {
  const response = await fetch(`${API_BASE}/research/${researchId}`);

  if (!response.ok) {
    throw new Error(`Failed to get research status (${response.status})`);
  }

  return response.json();
}

export function getResearchStreamUrl(researchId) {
  return `${API_BASE}/research/${researchId}/stream`;
}