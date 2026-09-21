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
 * Retrieve the report for a completed session.
 */
export async function getReport(sessionId) {
  const res = await fetch(`${API_BASE}/api/report/${sessionId}`);
  if (!res.ok) throw new Error(`Report request failed: ${res.status}`);
  return res.json();
}

export async function downloadReportPdf(sessionId) {
  const res = await fetch(`${API_BASE}/api/report/${sessionId}/pdf`);
  if (!res.ok) {
    throw new Error(await readApiError(res, `PDF download failed: ${res.status}`));
  }

  const disposition = res.headers.get("Content-Disposition") || "";
  const filenameMatch = disposition.match(/filename="?([^";]+)"?/i);
  return {
    blob: await res.blob(),
    filename: filenameMatch?.[1] || `troubleshooting-${sessionId.slice(0, 8)}.pdf`,
  };
}

async function readApiError(res, fallback) {
  try {
    const body = await res.json();
    return body.detail || fallback;
  } catch {
    return fallback;
  }
}

export async function getActiveKnowledgePack() {
  const res = await fetch(`${API_BASE}/api/knowledge/active`);
  if (!res.ok) {
    throw new Error(await readApiError(res, `Knowledge request failed: ${res.status}`));
  }
  return res.json();
}

export async function importKnowledgeSource(file) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/api/knowledge/sources/import`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    throw new Error(await readApiError(res, `Source import failed: ${res.status}`));
  }
  return res.json();
}

export async function deleteKnowledgeSource(sourceId) {
  const res = await fetch(`${API_BASE}/api/knowledge/sources/${sourceId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    throw new Error(await readApiError(res, `Source deletion failed: ${res.status}`));
  }
  return res.json();
}
