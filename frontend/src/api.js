/** API client for the AutoSage backend. The Vite dev server proxies /api. */

const BASE = '';

// --- Token / user (persisted in localStorage) ---

export function getToken() {
  return localStorage.getItem('autosage_token');
}

export function getUser() {
  const raw = localStorage.getItem('autosage_user');
  return raw ? JSON.parse(raw) : null;
}

function saveAuth(data) {
  localStorage.setItem('autosage_token', data.token);
  localStorage.setItem('autosage_user', JSON.stringify(data.user));
}

export function logout() {
  localStorage.removeItem('autosage_token');
  localStorage.removeItem('autosage_user');
}

function authHeaders() {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

// --- Auth ---

export async function getAuthConfig() {
  try {
    const res = await fetch(`${BASE}/api/auth/config`);
    return res.ok ? res.json() : {};
  } catch {
    return {};
  }
}

export async function emailAuth(email) {
  const res = await fetch(`${BASE}/api/auth/email`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Sign in failed');
  }
  const data = await res.json();
  saveAuth(data);
  return data;
}

// --- Conversations ---

export async function createConversation(title = null) {
  const res = await fetch(`${BASE}/api/conversations`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error(`Failed to create conversation: ${res.status}`);
  return res.json();
}

export async function listConversations() {
  const res = await fetch(`${BASE}/api/conversations`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to list conversations: ${res.status}`);
  return res.json();
}

export async function deleteConversation(id) {
  const res = await fetch(`${BASE}/api/conversations/${id}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to delete conversation: ${res.status}`);
}

// --- Messages ---

export async function getMessages(conversationId) {
  const res = await fetch(`${BASE}/api/conversations/${conversationId}/messages`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to get messages: ${res.status}`);
  return res.json();
}

export async function sendMessage(conversationId, content, lang = 'en') {
  const res = await fetch(`${BASE}/api/conversations/${conversationId}/messages`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ content, lang }),
  });
  if (!res.ok) throw new Error(`Failed to send message: ${res.status}`);
  return res.json();
}
