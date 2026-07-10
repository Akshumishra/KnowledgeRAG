/** Documents component — upload, list, delete. */
import { state, notify, parseApiError } from '../app.js';
import { documents } from '../api.js';

export async function renderDocuments(container) {
  const isOwner = state.user?.permissions?.includes('manage_organization_documents') || state.user?.is_owner;
  const title = 'Workspace Documents';
  const subtitle = 'Manage documents in your workspace';
  
  const uploadSection = `
      <input type="file" id="file-input" multiple class="hidden" accept=".pdf,.docx,.pptx,.xlsx,.csv,.txt,.md,.html,.json,.xml" />
      <button class="btn btn-primary" id="add-doc-btn">Add Document</button>
  `;

  container.innerHTML = `
    <div class="view-panel">
      <div class="view-header" style="display:flex; justify-content:space-between; align-items:flex-start;">
        <div>
          <div class="view-title">${title}</div>
          <div class="view-subtitle">${subtitle}</div>
        </div>
        <div>
            ${uploadSection}
        </div>
      </div>
      
      <div id="upload-progress-container" style="display:flex;flex-direction:column;gap:6px;margin-top:10px;"></div>

      <!-- Document List -->
      <div class="data-table-wrap mt-16">
        <table class="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Uploaded By</th>
              <th>Status</th>
              <th>Size</th>
              <th>Uploaded</th>
              <th style="width:50px;"></th>
            </tr>
          </thead>
          <tbody id="doc-list">
            <tr><td colspan="6" class="text-center text-muted">Loading documents...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  `;

  const addBtn = container.querySelector('#add-doc-btn');
  const fileInput = container.querySelector('#file-input');
  
  addBtn.addEventListener('click', () => fileInput.click());
  
  fileInput.addEventListener('change', () => {
    if (fileInput.files.length) handleFiles(Array.from(fileInput.files));
    fileInput.value = '';
  });

  // Use DocumentStore for the initial load (avoids duplicate API calls)
  const cachedDocs = window.DocumentStore?.documents || [];
  if (cachedDocs.length > 0) {
    // Render immediately from cache
    _renderDocList(cachedDocs);
  }
  // Always refresh when navigating to documents page
  if (window.DocumentStore) {
    window.DocumentStore.refresh().then(docs => _renderDocList(docs));
  } else {
    await loadDocuments();
  }
  
  // Auto-update when DocumentStore fetches new data (e.g., polling)
  window.addEventListener('documents-updated', (e) => {
    if (state.currentRoute === 'documents') {
      _renderDocList(e.detail);
    }
  });
}

async function loadDocuments() {
  const docs = await window.DocumentStore?.load() || await API.documents.list().catch(() => []);
  _renderDocList(docs);
}

function _renderDocList(docs) {
  const tbody = document.getElementById('doc-list');
  if (!tbody) return;
  if (!docs || docs.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted" style="padding:40px;">No documents found.</td></tr>';
    return;
  }
    
    const isOwner = state.user?.permissions?.includes('manage_organization_documents') || state.user?.is_owner;
    const currentUserId = state.user?.id;

    tbody.innerHTML = docs.map(d => {
      let badge = 'badge-ready';
      if (d.status === 'pending') badge = 'badge-pending';
      if (d.status === 'processing') badge = 'badge-processing';
      if (d.status === 'failed') badge = 'badge-failed';
      
      const sizeStr = (d.file_size / 1024 / 1024).toFixed(2) + ' MB';
      const dateStr = new Date(d.created_at).toLocaleDateString();

      // Check if user can delete this doc
      let canDelete = false;
      if (isOwner) {
         canDelete = true;
      } else if (d.uploaded_by === currentUserId) {
         canDelete = true;
      }

      const toggleBtn = canDelete ? `<button class="btn ${d.is_enabled ? 'btn-secondary' : 'btn-primary'} btn-sm" onclick="toggleDocumentStatus('${d.id}', ${!d.is_enabled})" title="${d.is_enabled ? 'Disable' : 'Enable'}">${d.is_enabled ? 'Disable' : 'Enable'}</button>` : '';
      const deleteBtn = canDelete ? `<button class="btn btn-secondary btn-sm" onclick="deleteDocument('${d.id}')" title="Delete">Delete</button>` : '';

      return `
        <tr style="opacity: ${d.is_enabled ? '1' : '0.5'}">
          <td><div style="font-weight:600;">${escHtml(d.name)} ${!d.is_enabled ? '(Disabled)' : ''}</div><div style="font-size:11px;color:var(--c-text-3)">${escHtml(d.original_filename)}</div></td>
          <td>${escHtml(d.uploader_name || 'Unknown')}</td>
          <td><span class="badge ${badge}">${d.status}</span></td>
          <td>${sizeStr}</td>
          <td>${dateStr}</td>
          <td>${toggleBtn} ${deleteBtn}</td>
        </tr>
      `;
    }).join('');
}



async function handleFiles(files) {
  const container = document.getElementById('upload-progress-container');
  
  for (const file of files) {
    const id = 'up-' + Date.now() + Math.random().toString(36).substring(7);
    const item = document.createElement('div');
    item.className = 'upload-item';
    item.id = id;
    item.innerHTML = `
      <div style="font-size:24px;"></div>
      <div class="upload-info">
        <div class="upload-name">${escHtml(file.name)}</div>
        <div class="upload-size">${(file.size / 1024 / 1024).toFixed(2)} MB</div>
        <div class="upload-progress-bar"><div class="upload-progress-fill" id="fill-${id}" style="width:0%"></div></div>
      </div>
    `;
    container.appendChild(item);

    try {
      await documents.upload(file, (pct) => {
        const fill = document.getElementById(`fill-${id}`);
        if (fill) fill.style.width = `${pct}%`;
      });
      document.getElementById(id)?.remove();
      notify(`Uploaded ${file.name} successfully`, 'success');
    } catch (e) {
      document.getElementById(id).innerHTML = `<div style="color:var(--c-danger);font-size:12px; display:flex; align-items:center; gap:6px;"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>${parseApiError(e)}</div>`;
      notify(parseApiError(e), 'error');
    }
  }
  
  // Refresh DocumentStore after all uploads so banner and cache are updated
  try {
    if (window.DocumentStore) {
      await window.DocumentStore.refresh();
      _renderDocList(window.DocumentStore.documents);
    } else {
      loadDocuments();
    }
  } catch (e) {}
}

window.deleteDocument = async (id) => {
  if (!confirm('Are you sure you want to delete this document? All associated chunks will be removed.')) return;
  try {
    await documents.delete(id);
    notify('Document deleted', 'success');
    if (window.DocumentStore) {
      await window.DocumentStore.refresh();
      _renderDocList(window.DocumentStore.documents);
    } else {
      loadDocuments();
    }
  } catch (e) {
    notify(parseApiError(e), 'error');
  }
};

function escHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

window.toggleDocumentStatus = async (id, isEnabled) => {
  try {
    await documents.toggle(id, isEnabled);
    notify(`Document ${isEnabled ? 'enabled' : 'disabled'}`, 'success');
    if (window.DocumentStore) {
      await window.DocumentStore.refresh();
      _renderDocList(window.DocumentStore.documents);
    } else {
      loadDocuments();
    }
  } catch (e) {
    notify(parseApiError(e), 'error');
  }
};
