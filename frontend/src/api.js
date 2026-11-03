const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function api(path, options = {}) {
  const token = localStorage.getItem('fittrack_token');
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(options.headers || {}) },
  });
  if (response.status === 204) return null;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || 'Something went wrong');
  return body;
}
export function saveSession(payload) { localStorage.setItem('fittrack_token', payload.access_token); localStorage.setItem('fittrack_user', JSON.stringify(payload.user)); }
export function clearSession() { localStorage.removeItem('fittrack_token'); localStorage.removeItem('fittrack_user'); }
export function getStoredUser() { try { return JSON.parse(localStorage.getItem('fittrack_user')) || null; } catch { return null; } }
export const today = () => new Date().toISOString().slice(0, 10);
export const formatDate = (value) => value ? new Date(`${value}T00:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : '—';
