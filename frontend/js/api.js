/**
 * API client — all fetch calls, SSE streaming, token refresh logic.
 */

const BASE = '';
let _accessToken = localStorage.getItem('access_token') || '';
let _refreshToken = localStorage.getItem('refresh_token') || '';

export function setTokens(access, refresh) {
  _accessToken = access;
  _refreshToken = refresh;
  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', refresh);
}

export function clearTokens() {
  _accessToken = '';
  _refreshToken = '';
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}

export function hasToken() { return !!_accessToken; }

async function _refresh() {
  if (!_refreshToken) throw new Error('No refresh token');
  const res = await fetch(`${BASE}/api/v1/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: _refreshToken }),
  });
  if (!res.ok) { clearTokens(); throw new Error('Session expired'); }
  const data = await res.json();
  setTokens(data.access_token, data.refresh_token);
}

async function _fetch(url, options = {}, retried = false) {
  const headers = { ...(options.headers || {}) };
  if (_accessToken) headers['Authorization'] = `Bearer ${_accessToken}`;
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = headers['Content-Type'] || 'application/json';
  }
  const res = await fetch(`${BASE}${url}`, { ...options, headers });
  if (res.status === 401 && !retried && !url.includes('/auth/login') && !url.includes('/auth/refresh') && !url.includes('/auth/verify')) {
    try { await _refresh(); return _fetch(url, options, true); }
    catch { clearTokens(); window.location.reload(); }
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  if (res.status === 204) return null;
  return res.json();
}

// ── Auth ─────────────────────────────────────────────────────────────
export const auth = {
  register: (data) => _fetch('/api/v1/auth/register', { method: 'POST', body: JSON.stringify(data) }),
  verifyEmail: (data) => _fetch('/api/v1/auth/verify-email', { method: 'POST', body: JSON.stringify(data) }),
  resendOtp: (data) => _fetch('/api/v1/auth/resend-otp', { method: 'POST', body: JSON.stringify(data) }),
  provisionOrg: (data) => _fetch('/api/v1/auth/provision_org', { method: 'POST', body: JSON.stringify(data) }),
  login: (data) => _fetch('/api/v1/auth/login', { method: 'POST', body: JSON.stringify(data) }),
  createWorkspace: (data) => _fetch('/api/v1/auth/create_workspace', { method: 'POST', body: JSON.stringify(data) }),
  joinWorkspace: (data) => _fetch('/api/v1/auth/join_workspace', { method: 'POST', body: JSON.stringify(data) }),
  me: () => _fetch('/api/v1/auth/me'),
  forgotPassword: (email) => _fetch('/api/v1/auth/forgot-password', { method: 'POST', body: JSON.stringify({ email }) }),
  resetPassword: (data) => _fetch('/api/v1/auth/reset-password', { method: 'POST', body: JSON.stringify(data) }),
};

// ── Workspaces ────────────────────────────────────────────────────────
export const workspaces = {
  list: () => _fetch('/api/v1/auth/workspaces'),
  create: (data) => _fetch('/api/v1/auth/workspaces', { method: 'POST', body: JSON.stringify(data) }),
  join: (data) => _fetch('/api/v1/auth/workspaces/join', { method: 'POST', body: JSON.stringify(data) }),
  enter: (id) => _fetch(`/api/v1/auth/workspaces/${id}/enter`, { method: 'POST' }),
  delete: (id) => _fetch(`/api/v1/auth/workspaces/${id}`, { method: 'DELETE' }),
};


// ── Documents ────────────────────────────────────────────────────────
export const documents = {
  list: () => _fetch(`/api/v1/documents/`),
  get: (id) => _fetch(`/api/v1/documents/${id}`),
  delete: (id) => _fetch(`/api/v1/documents/${id}`, { method: 'DELETE' }),
  toggle: (id, isEnabled) => _fetch(`/api/v1/documents/${id}`, { method: 'PATCH', body: JSON.stringify({ is_enabled: isEnabled }) }),
  upload: async (file, onProgress) => {
    const form = new FormData();
    form.append('file', file);
    const headers = {};
    if (_accessToken) headers['Authorization'] = `Bearer ${_accessToken}`;
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${BASE}/api/v1/documents/`);
      Object.entries(headers).forEach(([k, v]) => xhr.setRequestHeader(k, v));
      xhr.upload.onprogress = (e) => { if (e.lengthComputable && onProgress) onProgress(e.loaded / e.total * 100); };
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) resolve(JSON.parse(xhr.responseText));
        else reject(new Error(JSON.parse(xhr.responseText)?.detail || 'Upload failed'));
      };
      xhr.onerror = () => reject(new Error('Network error'));
      xhr.send(form);
    });
  },
};

export const conversations = {
  list: () => _fetch('/api/v1/conversations/'),
  create: (data) => _fetch('/api/v1/conversations/', { method: 'POST', body: JSON.stringify(data) }),
  get: (id) => _fetch(`/api/v1/conversations/${id}`),
  update: (id, data) => _fetch(`/api/v1/conversations/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id) => _fetch(`/api/v1/conversations/${id}`, { method: 'DELETE' }),
  getMessageStatus: (convId, msgId) => _fetch(`/api/v1/chat/${convId}/messages/${msgId}/status`),
};


// ── Providers ─────────────────────────────────────────────────────────
export const providers = {
  list: () => _fetch('/api/v1/providers'),
  create: (data) => _fetch('/api/v1/providers', { method: 'POST', body: JSON.stringify(data) }),
  listActive: () => _fetch('/api/v1/providers/active'),
  listKeys: (scope = 'user') => _fetch(`/api/v1/providers/keys?scope=${scope}`),
  saveKey: (data, scope = 'user') => _fetch(`/api/v1/providers/keys?scope=${scope}`, { method: 'POST', body: JSON.stringify(data) }),
  deleteKey: (provider, scope = 'user') => _fetch(`/api/v1/providers/keys/${provider}?scope=${scope}`, { method: 'DELETE' }),
  toggleKey: (provider, isEnabled, scope = 'user') => _fetch(`/api/v1/providers/keys/${provider}?scope=${scope}`, { method: 'PATCH', body: JSON.stringify({ is_enabled: isEnabled }) }),
  listModels: (provider, baseUrl) => _fetch(`/api/v1/providers/${provider}/models${baseUrl ? `?base_url=${baseUrl}` : ''}`),
  healthCheck: (provider) => _fetch(`/api/v1/providers/${provider}/health`),
  getWorkspaceModels: () => _fetch('/api/v1/providers/workspace-models'),
  saveProviderModels: (providerId, models, apiKeyId) => _fetch(`/api/v1/providers/${providerId}/models`, { method: 'POST', body: JSON.stringify({ models, api_key_id: apiKeyId }) }),
};

export const users = {
  list: () => _fetch('/api/v1/users/'),
  create: (data) => _fetch('/api/v1/users/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => _fetch(`/api/v1/users/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  remove: (id) => _fetch(`/api/v1/users/${id}`, { method: 'DELETE' }),
  getActivity: () => _fetch('/api/v1/users/activity'),
  updateActivity: (data) => _fetch('/api/v1/users/activity', { method: 'POST', body: JSON.stringify(data) }),
};


export const analytics = {
  getDashboard: () => _fetch('/api/v1/analytics/dashboard'),
};

// ── Audit ─────────────────────────────────────────────────────────────
export const audit = {
  getLogs: (limit = 50, offset = 0) => _fetch(`/api/v1/audit/?limit=${limit}&offset=${offset}`),
};

// ── Streaming Base ────────────────────────────────────────────────────
function _streamBase(url, options, callbacks) {
  const { onToken, onSources, onStats, onDone, onError, onThinking } = callbacks;
  const controller = new AbortController();

  const headers = { ...options.headers };
  if (_accessToken) headers['Authorization'] = `Bearer ${_accessToken}`;

  const doFetch = (retried = false) => {
    fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    }).then(async (res) => {
      if (res.status === 401 && !retried) {
        try {
          await _refresh();
          headers['Authorization'] = `Bearer ${_accessToken}`;
          return doFetch(true);
        } catch {
          clearTokens();
          window.location.reload();
          return;
        }
      }
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        onError?.(err.detail || 'Chat error');
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let currentEvent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (currentEvent === 'thinking') onThinking?.(data);
              else if (currentEvent === 'token') onToken?.(data.text);
              else if (currentEvent === 'sources') onSources?.(data);
              else if (currentEvent === 'stats') onStats?.(data);
              else if (currentEvent === 'done') onDone?.();
              else if (currentEvent === 'error') onError?.(data.message);
            } catch (e) {}
            currentEvent = '';
          }
        }
      }
      onDone?.();
    }).catch((err) => {
      if (err.name !== 'AbortError') onError?.(err.message);
    });
  };

  doFetch();

  return { cancel: () => controller.abort() };
}

export function streamChat(request, callbacks) {
  const { conversation_id, ...bodyData } = request;
  return _streamBase(
    `${BASE}/api/v1/chat/${conversation_id}/stream`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(bodyData),
    },
    callbacks
  );
}

export function reconnectStream(conversationId, messageId, callbacks) {
  return _streamBase(
    `${BASE}/api/v1/chat/${conversationId}/messages/${messageId}/stream`,
    {
      method: 'GET',
      headers: {},
    },
    callbacks
  );
}

export const fetchAPI = _fetch;
