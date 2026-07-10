/**
 * Enterprise AI Knowledge Platform — Main SPA Application
 * Client-side router and global state management.
 */
import * as API from './api.js';
import { renderAuth } from './components/auth.js';
import { renderSidebar, updateConversationList } from './components/sidebar.js';
import { renderChat, startNewChat } from './components/chat.js';
import { renderDocuments } from './components/documents.js';
import { renderUsers } from './components/users.js';
import { renderSettings } from './components/settings.js';
import { renderAdmin } from './components/admin.js';
import { renderDashboard } from './components/dashboard.js';

// ── Global State ──────────────────────────────────────────────────────
export const state = {
  user: null,
  currentRoute: 'chat',
  currentConversation: null,
  conversations: [],
  streaming: false,
  streamCancel: null,
  contextTokens: 0,
  maxContextTokens: 128000,
};
// ── Permission helpers (single source of truth) ─────────────────────────────
/**
 * Returns true if the current user is a workspace owner.
 * Always read from state.user which is set by /api/v1/auth/me.
 */
export function isOwner() {
  return state.user?.is_owner === true || state.user?.role === 'owner';
}

/**
 * Returns true if the current user has the given permission string.
 * e.g. hasPermission('manage_org')
 */
export function hasPermission(perm) {
  if (isOwner()) return true; // owners have all permissions
  return Array.isArray(state.user?.permissions) && state.user.permissions.includes(perm);
}


export function parseApiError(e) {
  if (!e) return 'An unexpected error occurred.';
  const msg = e?.message || String(e);
  
  // Exact matches or specific known prefixes
  if (msg === '401' || msg.includes('401 Unauthorized') || msg === 'Invalid or expired OTP') return 'You are not authorised to do this. Please log in again.';
  if (msg === '403' || msg === 'Insufficient permissions') return 'You do not have permission to do this.';
  if (msg === '404' || msg.includes('not found')) return 'The requested resource was not found.';
  if (msg === '422' || msg.includes('Unprocessable')) return 'Invalid input. Please check your data and try again.';
  if (msg === '500') return 'A server error occurred. Please try again later.';
  
  const map = {
    'Failed to fetch':          'Cannot reach the server. Check your internet connection.',
    'NetworkError':             'Network error. Please try again.',
    'network error':            'Network error. Please try again.',
    'Load failed':              'Cannot reach the server. Check your internet connection.',
    'Session expired':          'Your session has expired. Please log in again.',
    'No refresh token':         'Your session has expired. Please log in again.',
    'Chat error':               'Could not reach the AI model. Check your provider settings.',
    'Upload failed':            'File upload failed. Please try a smaller file or a different format.',
  };
  
  for (const [key, friendly] of Object.entries(map)) {
    if (msg.includes(key)) return friendly;
  }
  return msg;
}

// ── Notification system ───────────────────────────────────────────
export function notify(message, type = 'info', duration) {
  const container = document.getElementById('notifications') || (() => {
    const el = document.createElement('div');
    el.id = 'notifications';
    el.className = 'notifications';
    document.body.appendChild(el);
    return el;
  })();

  const icons = {
    info:    `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`,
    success: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
    error:   `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
    warning: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
  };

  const displayMsg = type === 'error' ? parseApiError(message) : message;
  const dismissMs = duration ?? (type === 'error' ? 7000 : 3500);

  const el = document.createElement('div');
  el.className = `notif ${type}`;
  el.innerHTML = `
    <span class="notif-icon">${icons[type] || icons.info}</span>
    <span class="notif-msg">${displayMsg}</span>
    <button class="notif-close" title="Dismiss" aria-label="Dismiss notification">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
    </button>
  `;
  container.appendChild(el);

  const dismiss = () => {
    el.style.opacity = '0';
    el.style.transform = 'translateX(20px)';
    setTimeout(() => el.remove(), 300);
  };

  el.querySelector('.notif-close').addEventListener('click', dismiss);
  const timer = setTimeout(dismiss, dismissMs);
  el.addEventListener('mouseenter', () => clearTimeout(timer));
  el.addEventListener('mouseleave', () => setTimeout(dismiss, 1500));
}

// ── Router ────────────────────────────────────────────────────────────
export function navigate(route, params = {}) {
  if (route === 'settings' && !isOwner()) {
    notify('You do not have permission to view this page.', 'warning');
    route = 'chat';
  }

  state.currentRoute = route;
  Object.assign(state, params);
  
  localStorage.setItem('last_route', route);
  let convIdToSave = null;
  if (route === 'chat' && state.currentConversation) {
    convIdToSave = state.currentConversation.id;
    localStorage.setItem('last_conversation_id', convIdToSave);
  } else if (route === 'chat' && !state.currentConversation) {
    localStorage.removeItem('last_conversation_id');
  }

  // Update server in background
  if (state.user) {
    API.users.updateActivity({ last_route: route, last_conversation_id: convIdToSave }).catch(e => {
        console.warn('Failed to sync user activity to server', e);
    });
  }

  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.route === route);
  });

  renderMainContent(route);
}

function renderMainContent(route) {
  const main = document.getElementById('main');
  if (!main) return;

  switch (route) {
    case 'chat':       renderChat(main); break;
    case 'documents':  renderDocuments(main); break;
    case 'users':      renderUsers(main); break;
    case 'settings':   renderSettings(main); break;
    case 'admin':      renderAdmin(main); break;
    default:           renderChat(main);
  }
}

// ── Bootstrap ─────────────────────────────────────────────────────────
async function boot() {
  if (!API.hasToken()) {
    renderAuth(() => afterLogin());
    return;
  }

  try {
    await afterLogin();
  } catch (e) {
    API.clearTokens();
    renderAuth(() => afterLogin());
  }
}

async function afterLogin() {
  state.user = await API.auth.me();

  const authPage = document.getElementById('auth-page');
  if (authPage) authPage.remove();

  if (!state.user.workspace_id) {
    const appEl = document.getElementById('app');
    import('./components/dashboard.js').then(({ renderDashboard }) => {
      renderDashboard(appEl, async () => {
        await afterLogin();
      });
    });
    return;
  }

  try {
    state.conversations = await API.conversations.list();
  } catch (e) {
    state.conversations = [];
  }

  buildLayout();
  
  let lastRoute = localStorage.getItem('last_route');
  let lastConvId = localStorage.getItem('last_conversation_id');
  
  if (!lastRoute) {
    try {
      const activity = await API.users.getActivity();
      if (activity && activity.last_route) {
        lastRoute = activity.last_route;
        lastConvId = activity.last_conversation_id;
      }
    } catch (e) {
      lastRoute = 'chat';
    }
  }
  
  if (!lastRoute) lastRoute = 'chat';
  
  if (lastRoute === 'chat' && lastConvId) {
    const conv = state.conversations.find(c => c.id === lastConvId);
    if (conv) {
      state.currentConversation = conv;
    }
  }

  navigate(lastRoute);
}

function buildLayout() {
  document.getElementById('app').innerHTML = `
    <div id="topbar">
      <button id="sidebar-toggle-btn" class="sidebar-toggle-btn" title="Toggle sidebar">
        <svg id="menu-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
        </svg>
      </button>
      <div class="topbar-logo"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:var(--c-primary);margin-right:8px;"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>KnowledgeAI</div>
      <div class="topbar-spacer"></div>

      <div id="global-progress-banner" style="display:none; background:var(--c-surface3); padding: 4px 12px; border-radius: 99px; font-size:12px; font-weight: 500; color:var(--c-primary); align-items:center; gap:8px; margin-right:12px; animation: pulse 2s infinite;">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="animation: spin 2s linear infinite;"><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/></svg>
        <span id="global-progress-text">Processing documents...</span>
      </div>
      <div class="topbar-avatar" id="user-avatar-btn" title="Profile">${(state.user?.full_name || 'U')[0].toUpperCase()}</div>
    </div>
    <div id="sidebar"></div>
    <div id="main"></div>
    <div id="user-dropdown" class="user-dropdown hidden"></div>
  `;

  renderSidebar(document.getElementById('sidebar'));

  // Sidebar toggle
  let sidebarOpen = true;
  document.getElementById('sidebar-toggle-btn')?.addEventListener('click', () => {
    sidebarOpen = !sidebarOpen;
    document.getElementById('app').classList.toggle('sidebar-collapsed', !sidebarOpen);
    const iconEl = document.getElementById('menu-icon');
    if (iconEl) {
      if (sidebarOpen) {
        iconEl.innerHTML = '<line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>';
      } else {
        iconEl.innerHTML = '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>';
      }
    }
  });




  // User dropdown
  document.getElementById('user-avatar-btn')?.addEventListener('click', (e) => {
    e.stopPropagation();
    toggleUserDropdown();
  });

  document.addEventListener('click', () => {
    document.getElementById('user-dropdown')?.classList.add('hidden');
  });

  // Initial document load via DocumentStore (uses cache, no polling unless pending docs exist)
  DocumentStore.load();
}

function toggleUserDropdown() {
  const dropdown = document.getElementById('user-dropdown');
  if (!dropdown) return;

  const isHidden = dropdown.classList.contains('hidden');
  if (!isHidden) { dropdown.classList.add('hidden'); return; }

  const role = state.user?.role || (state.user?.is_owner ? 'owner' : 'member');
  const roleLabel = role === 'owner' ? 'Workspace Owner' : 'Member';
  const roleBadgeClass = role === 'owner' ? 'role-badge-owner' : 'role-badge-member';

  dropdown.innerHTML = `
    <div class="user-dropdown-header">
      <div class="user-dropdown-avatar">${(state.user?.full_name || 'U')[0].toUpperCase()}</div>
      <div>
        <div class="user-dropdown-name">${state.user?.full_name || 'User'}</div>
        <div class="user-dropdown-email">${state.user?.email || ''}</div>
      </div>
    </div>
    <div class="user-dropdown-role ${roleBadgeClass}">${roleLabel}</div>
    <div class="user-dropdown-divider"></div>
    ${role === 'owner' ? `
    <div class="user-dropdown-item" id="dd-settings">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
        <circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
      </svg>
      Settings
    </div>
    ` : ''}
    <div class="user-dropdown-item user-dropdown-signout" id="dd-signout">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
      </svg>
      Sign Out
    </div>
  `;

  dropdown.classList.remove('hidden');

  dropdown.querySelector('#dd-settings')?.addEventListener('click', (e) => {
    e.stopPropagation();
    dropdown.classList.add('hidden');
    navigate('settings');
  });

  dropdown.querySelector('#dd-signout')?.addEventListener('click', (e) => {
    e.stopPropagation();
    window.API.clearTokens();
    window.location.reload();
  });
}

window.addEventListener('DOMContentLoaded', boot);
window.navigate = navigate;
window.notify = notify;
window.state = state;
window.API = API;
window.parseApiError = parseApiError;

export const DocumentStore = (() => {
  let _documents = [];
  let _lastFetch = null;
  let _isLoading = false;
  let _inflightPromise = null;
  let _pollTimer = null;
  let _lastActivity = Date.now();
  const CACHE_TTL_MS = 30_000; 
  const IDLE_TIMEOUT_MS = 60_000; 

  ['mousemove', 'keydown', 'click', 'scroll'].forEach(evt => {
    window.addEventListener(evt, () => {
      _lastActivity = Date.now();
    }, { passive: true });
  });

  function _updateBanner(docs) {
    const banner = document.getElementById('global-progress-banner');
    if (!banner) return;
    const pending = docs.filter(d => d.status === 'pending' || d.status === 'processing');
    if (pending.length > 0) {
      banner.style.display = 'flex';
      document.getElementById('global-progress-text').textContent =
        `Processing ${pending.length} document${pending.length > 1 ? 's' : ''}...`;
      banner.title = pending.map(d => d.name).join(', ');
      _startPoll();
    } else {
      banner.style.display = 'none';
      _stopPoll(); 
    }
  }

  function _startPoll() {
    if (_pollTimer) return;
    console.debug('[DocumentStore] Starting pending-docs poll (5s interval)');
    _pollTimer = setInterval(async () => {
      const isIdle = (Date.now() - _lastActivity) > IDLE_TIMEOUT_MS;
      const isHidden = document.visibilityState !== 'visible';
      
      if (isIdle || isHidden) {
        console.debug('[DocumentStore] Skipping poll (user idle or tab hidden)');
        return;
      }
      
      await _fetch(true);
    }, 5000);
  }

  function _stopPoll() {
    if (!_pollTimer) return;
    console.debug('[DocumentStore] No pending docs — stopping poll.');
    clearInterval(_pollTimer);
    _pollTimer = null;
  }

  async function _fetch(force = false) {
    if (!state.user || !state.user.workspace_id) return [];

    const now = Date.now();
    if (!force && _lastFetch && (now - _lastFetch < CACHE_TTL_MS) && _documents.length > 0) {
      console.debug('[DocumentStore] Cache hit. Age:', Math.round((now - _lastFetch) / 1000), 's');
      return _documents;
    }

    if (_inflightPromise) {
      console.debug('[DocumentStore] Request in flight — deduplicating.');
      return _inflightPromise;
    }

    console.debug('[DocumentStore] Fetching /documents. Reason:', force ? 'forced refresh' : 'cache miss', '| Time:', new Date().toISOString());

    _isLoading = true;
    _inflightPromise = API.documents.list(null, 'workspace')
      .then(docs => {
        _documents = docs || [];
        _lastFetch = Date.now();
        _updateBanner(_documents);
        window.dispatchEvent(new CustomEvent('documents-updated', { detail: _documents }));
        return _documents;
      })
      .catch(e => {
        console.warn('[DocumentStore] Fetch failed:', e);
        return _documents;
      })
      .finally(() => {
        _isLoading = false;
        _inflightPromise = null;
      });

    return _inflightPromise;
  }

  return {
    /** Load documents, using cache if still valid (no extra requests for idle users). */
    load() { return _fetch(false); },

    /** Force a fresh fetch, e.g. after upload/delete/rename. */
    refresh() {
      console.debug('[DocumentStore] Forced refresh requested.');
      _lastFetch = null;
      return _fetch(true);
    },

    /** Invalidate the cache (next load() will re-fetch). */
    invalidate() { _lastFetch = null; },

    get documents() { return _documents; },
    get isLoading() { return _isLoading; },
  };
})();

window.DocumentStore = DocumentStore;
