/**
 * API helper — centralizes all backend API calls.
 *
 * All requests go to the FastAPI backend (NEXT_PUBLIC_BACKEND_URL).
 */

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

/**
 * Send a chat message and get the orchestrator's response.
 */
export async function sendMessage(sessionId, message) {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  if (!res.ok) throw new Error(`Chat request failed: ${res.status}`);
  return res.json();
}

/**
 * Trigger a full diagnosis run for a session.
 */
export async function runDiagnosis(sessionId) {
  const res = await fetch(`${API_BASE}/api/diagnose`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!res.ok) throw new Error(`Diagnose request failed: ${res.status}`);
  return res.json();
}

/**
 * Upload a dispensing defect image.
 */
export async function uploadImage(sessionId, file) {
  const formData = new FormData();
  formData.append("session_id", sessionId);
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/api/upload-image`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(`Upload request failed: ${res.status}`);
  return res.json();
}

/**
 * Retrieve the report for a completed session.
 */
export async function getReport(sessionId) {
  const res = await fetch(`${API_BASE}/api/report/${sessionId}`);
  if (!res.ok) throw new Error(`Report request failed: ${res.status}`);
  return res.json();
}
