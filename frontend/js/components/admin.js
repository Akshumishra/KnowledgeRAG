/** Admin/Analytics component. */
import { state } from '../app.js';
import { analytics, audit } from '../api.js';

export async function renderAdmin(container) {
  if (!state.user?.permissions?.includes('view_all_chats') && !state.user?.permissions?.includes('manage_system')) {
    container.innerHTML = `<div class="view-panel"><div class="empty-state">You don't have permission to view analytics.</div></div>`;
    return;
  }

  container.innerHTML = `
    <div class="view-panel">
      <div class="view-header">
        <div>
          <div class="view-title">Analytics Dashboard</div>
          <div class="view-subtitle">Platform usage and performance metrics</div>
        </div>
      </div>

      <div id="stats-container">
        <div class="text-center text-muted mt-16">Loading analytics...</div>
      </div>
      
      <div class="view-header mt-16" style="margin-top:32px;">
        <div>
          <div class="view-title" style="font-size:16px;">Audit Log</div>
          <div class="view-subtitle">Recent system activity</div>
        </div>
      </div>
      <div class="data-table-wrap mt-8">
        <table class="data-table">
          <thead>
            <tr>
              <th>Action</th>
              <th>User</th>
              <th>Resource</th>
              <th>IP Address</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody id="audit-list">
            <tr><td colspan="5" class="text-center text-muted">Loading logs...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  `;

  const canProvision = state.user?.permissions?.includes('manage_system');

  if (canProvision) {
    container.innerHTML += `
      <div class="view-header mt-16" style="margin-top:32px;">
        <div>
          <div class="view-title" style="font-size:16px;">Enroll Workspace Admin</div>
          <div class="view-subtitle">Create a new tenant and assign the default Workspace Admin</div>
        </div>
      </div>
      <div class="data-table-wrap mt-8" style="padding: 20px; background: var(--c-surface2);">
        <form id="provision-form" style="display: flex; flex-direction: column; gap: 14px; max-width: 500px;">
          <div class="form-group">
            <label class="form-label">Workspace Name</label>
            <input id="prov-org-name" class="form-control" type="text" placeholder="Acme Corp" required />
          </div>
          <div class="form-group">
            <label class="form-label">Workspace Slug</label>
            <input id="prov-org-slug" class="form-control" type="text" placeholder="acme-corp" pattern="[a-z0-9\\-]+" title="Lowercase letters, numbers, hyphens only" required />
          </div>
          <hr style="border:0; border-top:1px solid var(--c-border); margin: 8px 0;" />
          <div class="form-group">
            <label class="form-label">Admin Name</label>
            <input id="prov-head-name" class="form-control" type="text" placeholder="Admin User" required />
          </div>
          <div class="form-group">
            <label class="form-label">Admin Email</label>
            <input id="prov-head-email" class="form-control" type="email" placeholder="admin@acme.com" required />
          </div>
          <div class="form-group">
            <label class="form-label">Admin Default Password</label>
            <input id="prov-head-password" class="form-control" type="password" placeholder="••••••••" required minlength="8" />
          </div>
          <button class="btn btn-primary" type="submit" id="prov-submit" style="margin-top: 8px;">Enroll Workspace Admin</button>
        </form>
      </div>
    `;
  }

  await Promise.all([loadStats(), loadAudit()]);

  if (canProvision) {
    // Auto-generate slug
    const orgNameEl = document.getElementById('prov-org-name');
    const orgSlugEl = document.getElementById('prov-org-slug');
    if (orgNameEl && orgSlugEl) {
      orgNameEl.addEventListener('input', (e) => {
        if (!orgSlugEl._manuallyEdited) {
          orgSlugEl.value = e.target.value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
        }
      });
      orgSlugEl.addEventListener('input', (e) => { e.target._manuallyEdited = true; });
    }

    // Submit handler
    const form = document.getElementById('provision-form');
    if (form) {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('prov-submit');
        btn.disabled = true;
        btn.textContent = 'Provisioning...';
        try {
          const { auth } = await import('../api.js');
          const res = await auth.provisionOrg({
            org_name: orgNameEl.value,
            org_slug: orgSlugEl.value,
            head_name: document.getElementById('prov-head-name').value,
            head_email: document.getElementById('prov-head-email').value,
            head_password: document.getElementById('prov-head-password').value,
          });
          window.notify(res.message || 'Workspace provisioned successfully!', 'success');
          form.reset();
          orgSlugEl._manuallyEdited = false;
        } catch (err) {
          window.notify(err.message || 'Provisioning failed', 'error');
        } finally {
          btn.disabled = false;
          btn.textContent = 'Provision Tenant';
        }
      });
    }
  }
}

async function loadStats() {
  const container = document.getElementById('stats-container');
  if (!container) return;
  try {
    const data = await analytics.getDashboard();
    const s = data.stats;
    container.innerHTML = `
      <div class="stat-cards">
        <div class="stat-card" style="--card-color:var(--c-primary)">
          <div class="stat-card-icon"></div>
          <div class="stat-card-value">${s.total_documents.toLocaleString()}</div>
          <div class="stat-card-label">Total Documents</div>
        </div>
        <div class="stat-card" style="--card-color:var(--c-accent)">
          <div class="stat-card-icon"></div>
          <div class="stat-card-value">${s.total_chunks.toLocaleString()}</div>
          <div class="stat-card-label">Vector Chunks</div>
        </div>
        <div class="stat-card" style="--card-color:var(--c-success)">
          <div class="stat-card-icon"></div>
          <div class="stat-card-value">${s.total_messages.toLocaleString()}</div>
          <div class="stat-card-label">Messages Sent</div>
        </div>
        <div class="stat-card" style="--card-color:var(--c-warning)">
          <div class="stat-card-icon"></div>
          <div class="stat-card-value">${s.total_tokens_used.toLocaleString()}</div>
          <div class="stat-card-label">Tokens Used</div>
        </div>
      </div>
      <div class="stat-cards" style="margin-top:12px;">
        <div class="stat-card" style="--card-color:var(--c-text-2)">
          <div class="stat-card-icon"></div>
          <div class="stat-card-value">${s.avg_response_latency_ms}ms</div>
          <div class="stat-card-label">Avg Latency</div>
        </div>
        <div class="stat-card" style="--card-color:var(--c-text-2)">
          <div class="stat-card-icon"></div>
          <div class="stat-card-value">${s.total_users}</div>
          <div class="stat-card-label">Active Users</div>
        </div>
        <div class="stat-card" style="--card-color:var(--c-text-2)">
          <div class="stat-card-icon"></div>
          <div class="stat-card-value">${s.active_collections}</div>
          <div class="stat-card-label">Collections</div>
        </div>
        <div class="stat-card" style="--card-color:var(--c-text-2)">
          <div class="stat-card-icon"></div>
          <div class="stat-card-value">${(s.storage_used_bytes / 1024 / 1024).toFixed(1)} MB</div>
          <div class="stat-card-label">Storage Used</div>
        </div>
      </div>
    `;
  } catch (e) {
    container.innerHTML = `<div class="text-center" style="color:var(--c-text-2)">No data found</div>`;
  }
}

async function loadAudit() {
  const tbody = document.getElementById('audit-list');
  if (!tbody) return;
  try {
    const logs = await audit.getLogs(20, 0);
    if (!logs || logs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No data available</td></tr>';
      return;
    }
    tbody.innerHTML = logs.map(l => `
      <tr>
        <td style="font-weight:600;"><span class="badge" style="background:var(--c-surface3)">${l.action}</span></td>
        <td style="color:var(--c-text-2);">${l.user_id ? l.user_id.slice(0,8) : 'System'}</td>
        <td style="color:var(--c-text-3);">${l.resource_type || '-'} ${l.resource_id ? l.resource_id.slice(0,8) : ''}</td>
        <td style="font-family:monospace;font-size:11px;color:var(--c-text-3)">${l.ip_address || '-'}</td>
        <td>${new Date(l.created_at).toLocaleString()}</td>
      </tr>
    `).join('');
  } catch (e) {
    console.error(e);
    // If it's a 404 or similar, it might just mean no logs are available or feature is disabled
    tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">No data available</td></tr>`;
    if (e.message) {
      window.notify(e.message, 'error');
    }
  }
}
