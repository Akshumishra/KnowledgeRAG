/** Settings component - Provider API keys & Models (DB-backed). */
import { state, notify, isOwner } from '../app.js';
import { providers } from '../api.js';

// Module-level caches
let _workspaceModels = {};
let _dbProviders = [];

export async function renderSettings(container) {
  if (!isOwner()) {

    container.innerHTML = `
      <div class="view-panel">
        <div class="view-header" style="margin-bottom:24px;">
          <div><div class="view-title">Settings &amp; LLM Providers</div></div>
        </div>
        <div style="padding:40px;text-align:center;color:var(--c-text-2);border:1px solid var(--c-border);border-radius:8px;">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom:16px;opacity:0.5;">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
            <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
          </svg>
          <h3 style="margin-bottom:8px;color:var(--c-text-1);">Access Denied</h3>
          <p>Only workspace owners can add or manage LLM providers.</p>
        </div>
      </div>
    `;
    return;
  }

  container.innerHTML = `
    <div class="view-panel">
      <div class="view-header" style="margin-bottom:24px;">
        <div>
          <div class="view-title">Settings &amp; LLM Providers</div>
          <div class="view-subtitle">Manage API keys and models for your workspace</div>
        </div>
      </div>

      <div class="view-title" style="margin-top:24px;font-size:16px;">Configured Providers</div>
      <div class="view-subtitle mb-16">Keys are workspace-scoped and available to all members.</div>
      <div class="data-table-wrap" style="overflow:auto;flex-shrink:0;">
        <table class="data-table" style="width:100%;border-collapse:collapse;text-align:left;">
          <thead>
            <tr>
              <th style="padding:12px;border-bottom:1px solid var(--c-border);">Provider</th>
              <th style="padding:12px;border-bottom:1px solid var(--c-border);">Key Preview</th>
              <th style="padding:12px;border-bottom:1px solid var(--c-border);">Models</th>
              <th style="padding:12px;border-bottom:1px solid var(--c-border);width:230px;">Actions</th>
            </tr>
          </thead>
          <tbody id="provider-list-workspace">
            <tr><td colspan="4" class="text-center text-muted" style="padding:16px;">Loading providers...</td></tr>
          </tbody>
        </table>
      </div>

      <div class="view-title" style="margin-top:48px;margin-bottom:8px;font-size:15px;">Add / Update Provider</div>
      <div class="view-subtitle" style="margin-bottom:16px;">Click a provider to set its API key and model list.</div>
      <div id="provider-cards-container" class="stat-cards" style="display:flex;gap:16px;flex-wrap:wrap;">
        <div style="padding:16px; color:var(--c-text-3);">Loading available providers...</div>
      </div>

      <div style="margin-top:48px; border-top:1px solid var(--c-border); padding-top:24px;">
        <div class="view-title" style="color:var(--c-danger); font-size:15px;">Danger Zone</div>
        <div class="view-subtitle" style="margin-bottom:16px;">Irreversible actions. Please be certain.</div>
        <div style="display:flex; justify-content:space-between; align-items:center; border:1px solid var(--c-danger); border-radius:8px; padding:16px; background:rgba(255, 59, 48, 0.05);">
          <div>
            <div style="font-weight:600; color:var(--c-text-1);">Delete this Workspace</div>
            <div style="font-size:13px; color:var(--c-text-2);">Once deleted, this workspace and all its data cannot be recovered.</div>
          </div>
          <button class="btn btn-danger" onclick="deleteWorkspace()">Delete Workspace</button>
        </div>
      </div>
    </div>
  `;

  await loadProviders();
}

window.deleteWorkspace = async () => {
  const confirmText = prompt('Are you absolutely sure you want to delete this workspace? This action cannot be undone. Type "DELETE" to confirm.');
  if (confirmText !== 'DELETE') return;
  
  try {
    const { workspaces } = await import('../api.js');
    await workspaces.delete(state.user.workspace_id);
    notify('Workspace deleted successfully', 'success');
    // Force a reload to clear state and send user to dashboard
    setTimeout(() => window.location.reload(), 1500);
  } catch (e) {
    notify(e.message, 'error');
  }
};

async function loadProviders() {
  const tbody = document.getElementById('provider-list-workspace');
  if (!tbody) return;
  try {
    const [keys, modelsMap, dbProvidersList] = await Promise.all([
      providers.listKeys('workspace'),
      providers.getWorkspaceModels(),
      providers.list(),
    ]);
    _workspaceModels = modelsMap || {};
    _dbProviders = dbProvidersList || [];

    // Render provider cards dynamically
    const cardsContainer = document.getElementById('provider-cards-container');
    if (cardsContainer) {
      let cardsHtml = _dbProviders.map(p => `
        <div class="stat-card" style="cursor:pointer;flex:1;min-width:150px;padding:16px;border:1px solid var(--c-border);border-radius:8px;"
             onclick="showAddProvider('${p.slug}', '${p.name}', '${p.default_models || ''}')">
          <div class="stat-card-icon">${p.icon || ''}</div>
          <div class="stat-card-value" style="font-size:14px;margin-top:8px;">${p.name}</div>
        </div>
      `).join('');
      
      // Custom provider button removed as per user request
      cardsContainer.innerHTML = cardsHtml;
    }

    if (keys.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted" style="padding:40px;">No providers configured. Add one below.</td></tr>`;
      return;
    }

    let html = '';
    for (const key of keys) {
      const pInfo = _dbProviders.find(p => p.slug === key.provider_id) || { name: key.provider_id, icon: '' };
      const modelList = _workspaceModels[key.provider_id] || [];
      const modelPills = modelList.length
        ? modelList.map(m => `<span style="background:var(--c-surface2);border:1px solid var(--c-border);border-radius:12px;padding:2px 10px;font-size:11px;margin:2px;display:inline-block;">${m}</span>`).join('')
        : `<span style="color:var(--c-text-3);font-size:12px;font-style:italic;">No models — click "Edit Models"</span>`;

      html += `
        <tr style="opacity:${key.is_enabled ? '1' : '0.5'};border-bottom:1px solid var(--c-border);">
          <td style="font-weight:600;padding:12px;">${pInfo.icon || ''} ${pInfo.name} ${!key.is_enabled ? '<span style="font-size:11px;color:var(--c-danger);">(Disabled)</span>' : ''}</td>
          <td style="font-family:monospace;color:var(--c-text-2);padding:12px;">${key.key_preview || '••••••••••••••••'}</td>
          <td style="padding:12px;max-width:280px;">${modelPills}</td>
          <td style="padding:12px;">
            <div style="display:flex;gap:6px;flex-wrap:wrap;">
              <button class="btn btn-secondary btn-sm" onclick="showEditModels('${key.provider_id}', '${pInfo.name}')">Edit Models</button>
              <button class="btn ${key.is_enabled ? 'btn-secondary' : 'btn-primary'} btn-sm" onclick="toggleProviderStatus('${key.provider_id}', 'workspace', ${!key.is_enabled})">
                ${key.is_enabled ? 'Disable' : 'Enable'}
              </button>
              <button class="btn btn-danger btn-sm" onclick="deleteProvider('${key.provider_id}', 'workspace')">Remove</button>
            </div>
          </td>
        </tr>
      `;
    }
    tbody.innerHTML = html;
  } catch (e) {
    console.error('Error loading providers:', e);
    tbody.innerHTML = `<tr><td colspan="4" class="text-center" style="color:var(--c-text-2)">Error: ${e.message}</td></tr>`;
  }
}



window.showAddProvider = (id, name, defaultModels) => {
  const existingModels = (_workspaceModels[id] || []).join(', ') || defaultModels;
  
  const isOllama = (id === 'ollama');
  const keyLabel = isOllama ? 'Base URL' : 'API Key';
  const keyPlaceholder = isOllama ? 'http://127.0.0.1:11434' : 'sk-...';
  const keyType = isOllama ? 'text' : 'password';

  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `
    <div class="modal">
      <div class="modal-header">
        <div class="modal-title">Configure ${name}</div>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">x</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label class="form-label">${keyLabel}</label>
          <input type="${keyType}" id="np-key" class="form-control" placeholder="${keyPlaceholder}" autocomplete="new-password" />
        </div>
        <div class="form-group" style="margin-top:16px;">
          <label class="form-label">Available Models <span style="color:var(--c-text-3);font-weight:400;">(comma-separated)</span></label>
          <input type="text" id="np-models" class="form-control" value="${existingModels}" placeholder="e.g. gpt-4o, gpt-3.5-turbo" />
          <div style="font-size:11px;color:var(--c-text-3);margin-top:4px;">These model names appear in the chat dropdown, filtered per provider.</div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">Cancel</button>
        <button class="btn btn-primary" id="np-submit">Save Provider</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  overlay.querySelector('#np-submit').addEventListener('click', async () => {
    const btn = overlay.querySelector('#np-submit');
    const key = overlay.querySelector('#np-key').value.trim();
    const modelsRaw = overlay.querySelector('#np-models').value.trim();
    const modelList = modelsRaw.split(',').map(m => m.trim()).filter(Boolean);
    
    if (!key) {
      notify('API Key is required.', 'error');
      return;
    }
    if (modelList.length === 0) {
      notify('At least one model name is required.', 'error');
      return;
    }

    btn.disabled = true; btn.textContent = 'Saving...';
    try {
      await providers.saveKey({ provider_id: id, api_key: key }, 'workspace');
      await providers.saveProviderModels(id, modelList);
      notify(`${name} configured successfully`, 'success');
      overlay.remove();
      loadProviders();
    } catch (e) {
      notify(e.message, 'error');
      btn.disabled = false; btn.textContent = 'Save Provider';
    }
  });
};

window.showEditModels = (providerId, providerName) => {
  const currentModels = (_workspaceModels[providerId] || []).join(', ');
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `
    <div class="modal">
      <div class="modal-header">
        <div class="modal-title">Edit Models - ${providerName}</div>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">x</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label class="form-label">Model Names <span style="color:var(--c-text-3);font-weight:400;">(comma-separated)</span></label>
          <input type="text" id="edit-models-input" class="form-control" value="${currentModels}" placeholder="e.g. gpt-4o, gpt-3.5-turbo" />
          <div style="font-size:11px;color:var(--c-text-3);margin-top:4px;">Chat users will see these models when this provider is selected.</div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">Cancel</button>
        <button class="btn btn-primary" id="edit-models-submit">Save Models</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  overlay.querySelector('#edit-models-submit').addEventListener('click', async () => {
    const btn = overlay.querySelector('#edit-models-submit');
    btn.disabled = true; btn.textContent = 'Saving...';
    const modelsRaw = overlay.querySelector('#edit-models-input').value.trim();
    const modelList = modelsRaw.split(',').map(m => m.trim()).filter(Boolean);
    try {
      await providers.saveProviderModels(providerId, modelList);
      notify('Models updated', 'success');
      overlay.remove();
      loadProviders();
    } catch (e) {
      notify(e.message, 'error');
      btn.disabled = false; btn.textContent = 'Save Models';
    }
  });
};

window.deleteProvider = async (providerId, scope = 'workspace') => {
  if (!confirm('Remove this provider? Its model list will also be cleared.')) return;
  try {
    await providers.deleteKey(providerId, scope);
    await providers.saveProviderModels(providerId, []).catch(() => {});
    notify('Provider removed', 'success');
    loadProviders();
  } catch (e) {
    notify(e.message, 'error');
  }
};

window.toggleProviderStatus = async (providerId, scope, isEnabled) => {
  try {
    await providers.toggleKey(providerId, isEnabled, scope);
    notify(`Provider ${isEnabled ? 'enabled' : 'disabled'}`, 'success');
    loadProviders();
  } catch (e) {
    notify(e.message, 'error');
  }
};
