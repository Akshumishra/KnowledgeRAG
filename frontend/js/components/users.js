/** Users component — user list and creation (RBAC). */
import { state, notify } from '../app.js';
import { users, workspaces } from '../api.js';

export async function renderUsers(container) {
  const isOwner = state.user?.is_owner || state.user?.permissions?.includes('manage_org') || state.user?.permissions?.includes('manage_users');

  let joinCode = '';
  if (isOwner) {
    try {
      const wlist = await workspaces.list();
      const currentWs = wlist.find(w => w.id === state.user.workspace_id);
      if (currentWs && currentWs.join_code) {
        joinCode = currentWs.join_code;
      }
    } catch (e) {
      console.warn("Could not fetch workspace join code", e);
    }
  }

  container.innerHTML = `
    <div class="view-panel">
      <div class="view-header">
        <div>
          <div class="view-title">Users</div>
          <div class="view-subtitle">Workspace members</div>
        </div>
        ${isOwner && joinCode ? `<button class="btn btn-primary" id="copy-code-btn">Copy Join Code: ${joinCode}</button>` : ''}
      </div>

      <div class="data-table-wrap mt-16">
        <table class="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Last Login</th>
              <th style="width:50px;"></th>
            </tr>
          </thead>
          <tbody id="user-list">
            <tr><td colspan="6" class="text-center text-muted">Loading...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  `;

  if (isOwner && joinCode) {
    container.querySelector('#copy-code-btn')?.addEventListener('click', () => {
      navigator.clipboard.writeText(joinCode);
      notify('Join code copied to clipboard', 'success');
    });
  }
  await loadUsers(isOwner);
}

async function loadUsers(isOwner) {
  const tbody = document.getElementById('user-list');
  if (!tbody) return;
  try {
    const data = await users.list();
    if (data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No users found.</td></tr>';
      return;
    }
    tbody.innerHTML = data.map(u => {
      const activeHtml = u.is_active ? '<span class="badge badge-ready">Active</span>' : '<span class="badge badge-failed">Disabled</span>';
      return `
        <tr>
          <td style="font-weight:600;">${escHtml(u.full_name)}</td>
          <td style="color:var(--c-text-2);">${escHtml(u.email)}</td>
          <td><span class="badge" style="background:var(--c-surface3)">${u.role}</span></td>
          <td>${activeHtml}</td>
          <td>${u.last_login ? new Date(u.last_login).toLocaleString() : 'Never'}</td>
          <td>
            ${(isOwner && u.id !== state.user.id) ? `<button class="btn btn-secondary btn-sm" onclick="removeUser('${u.id}')" title="Remove">Remove</button>` : ''}
          </td>
        </tr>
      `;
    }).join('');
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center" style="color:var(--c-danger)">Failed to load users</td></tr>`;
  }
}

window.removeUser = async (id) => {
  if (!confirm('Are you sure you want to remove this user from the workspace?')) return;
  try {
    await users.remove(id);
    notify('User removed', 'success');
    loadUsers(state.user?.is_owner || state.user?.permissions?.includes('manage_users'));
  } catch (e) {
    notify(e.message, 'error');
  }
};

function escHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
