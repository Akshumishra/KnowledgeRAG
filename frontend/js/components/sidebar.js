/** Sidebar component. */
import { state, navigate, notify } from '../app.js';
import { conversations } from '../api.js';

const NAV_ITEMS = [
  { route: 'chat',        icon: '', label: 'Chat' },
  { route: 'documents',   icon: '', label: 'My Docs' },
  { route: 'users',       icon: '', label: 'Users' },
  { route: 'settings',    icon: '', label: 'Settings', perms: ['manage_org', 'manage_system'] },
];

export function renderSidebar(el) {
  const convHtml = state.conversations.slice(0, 30).map(c => `
    <div class="conv-item ${state.currentConversation?.id === c.id ? 'active' : ''}" data-conv-id="${c.id}" style="display:flex;justify-content:space-between;align-items:center;">
      <div style="display:flex;align-items:center;overflow:hidden;">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;margin-right:6px;">
          <polyline points="9 18 15 12 9 6"></polyline>
        </svg>
        <span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escHtml(c.title)}</span>
      </div>
      <button class="delete-conv-btn" data-delete-id="${c.id}" style="background:none;border:none;color:var(--c-text-3);cursor:pointer;padding:2px;display:none;">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"></path><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
      </button>
    </div>
  `).join('');

  const visibleNavItems = NAV_ITEMS.filter(item => {
    if (!item.perms) return true;
    if (!state.user) return false;
    if (state.user.is_owner || state.user.role === 'owner') return true;
    if (!state.user.permissions) return false;
    return item.perms.some(p => state.user.permissions.includes(p));
  });

  el.innerHTML = `
    <div style="padding:8px;">
      <button class="sidebar-new-chat" id="new-chat-btn">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:4px;">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
        <span class="nav-text">New Chat</span>
      </button>
    </div>
    <div class="sidebar-section">
      <div class="sidebar-section-label nav-text">Navigation</div>
      ${visibleNavItems.map(item => `
        <div class="nav-item ${state.currentRoute === item.route ? 'active' : ''}" data-route="${item.route}">
          <span class="nav-icon">${item.icon}</span>
          <span class="nav-text">${item.label}</span>
        </div>
      `).join('')}
    </div>
    <div class="sidebar-section" style="flex:1;overflow:hidden;display:flex;flex-direction:column;">
      <div class="sidebar-section-label nav-text">Recent Chats</div>
      <div class="conv-list">${convHtml || '<div style="padding:8px;font-size:12px;color:var(--c-text-3);">No conversations yet</div>'}</div>
    </div>
    <div style="padding:12px 8px;border-top:1px solid var(--c-border);">
      <div class="nav-item" id="logout-btn">
        <span class="nav-icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
            <polyline points="16 17 21 12 16 7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
        </span>
        <span class="nav-text">Sign Out</span>
      </div>
    </div>
  `;

  el.querySelector('#new-chat-btn')?.addEventListener('click', () => {
    state.currentConversation = null;
    navigate('chat');
  });

  el.querySelectorAll('.nav-item[data-route]').forEach(item => {
    item.addEventListener('click', () => navigate(item.dataset.route));
  });

  el.querySelectorAll('.conv-item[data-conv-id]').forEach(item => {
    // Show delete button on hover
    item.addEventListener('mouseenter', () => {
      const delBtn = item.querySelector('.delete-conv-btn');
      if (delBtn) delBtn.style.display = 'block';
    });
    item.addEventListener('mouseleave', () => {
      const delBtn = item.querySelector('.delete-conv-btn');
      if (delBtn) delBtn.style.display = 'none';
    });

    item.addEventListener('click', (e) => {
      // Don't navigate if clicking delete
      if (e.target.closest('.delete-conv-btn')) return;
      const conv = state.conversations.find(c => c.id === item.dataset.convId);
      state.currentConversation = conv || null;
      navigate('chat');
    });
  });

  el.querySelectorAll('.delete-conv-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const id = btn.dataset.deleteId;
      if (!confirm('Are you sure you want to delete this chat?')) return;
      try {
        await conversations.delete(id);
        state.conversations = state.conversations.filter(c => c.id !== id);
        if (state.currentConversation?.id === id) {
          state.currentConversation = null;
          navigate('chat');
        } else {
          updateConversationList();
        }
        notify('Chat deleted', 'success');
      } catch (err) {
        notify(err.message, 'error');
      }
    });
  });

  el.querySelector('#logout-btn')?.addEventListener('click', () => {
    window.API.clearTokens();
    window.location.reload();
  });
}

export function updateConversationList() {
  renderSidebar(document.getElementById('sidebar'));
}

function escHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
