function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

export async function renderDashboard(container, onEnterWorkspace) {
  // Instead of replacing #app, create a dedicated full-screen overlay like auth-page
  const page = document.createElement('div');
  page.id = 'dashboard-page';
  page.style.cssText = `
    position: fixed; inset: 0; z-index: 998;
    background: var(--c-bg);
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    background-image: radial-gradient(ellipse at 50% 0%, rgba(99,102,241,0.15) 0%, transparent 60%),
                      radial-gradient(ellipse at 100% 100%, rgba(34,211,238,0.1) 0%, transparent 50%);
    padding: 20px;
    overflow-y: auto;
  `;
  document.body.appendChild(page);

  page.innerHTML = `
    <div style="width: 100%; max-width: 800px; animation: slideUp 0.5s ease;">
      <div style="text-align: center; margin-bottom: 40px;">
        <div style="display:inline-flex; align-items:center; justify-content:center; width:64px; height:64px; border-radius:16px; background:linear-gradient(135deg, var(--c-primary), var(--c-accent)); color:#fff; font-size:32px; margin-bottom:20px; box-shadow: 0 10px 30px rgba(99,102,241,0.3);">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:var(--c-primary);"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
        </div>
        <h1 style="font-weight: 800; font-size: 32px; letter-spacing: -1px; margin-bottom: 12px; background: linear-gradient(135deg, #fff, var(--c-text-2)); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Select a Workspace</h1>
        <p style="color: var(--c-text-2); font-size: 15px; max-width: 400px; margin: 0 auto;">Choose a workspace to continue, or create a new one to start organizing your team's knowledge.</p>
      </div>
      
      <div id="workspace-list" style="display:grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap:20px; width:100%; margin-bottom:40px; min-height: 100px;">
        <div style="grid-column: 1 / -1; text-align:center; color:var(--c-text-3); padding: 40px;">Loading workspaces...</div>
      </div>

      <div style="display:flex; justify-content:center; gap: 16px; flex-wrap: wrap;">
        <button class="btn btn-primary" id="btn-create-ws" style="padding: 12px 24px; font-size: 14px; border-radius: 99px; box-shadow: 0 4px 20px rgba(99,102,241,0.3);">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right:8px;"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
          Create Workspace
        </button>
        <button class="btn btn-secondary" id="btn-join-ws" style="padding: 12px 24px; font-size: 14px; border-radius: 99px;">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right:8px;"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path><polyline points="10 17 15 12 10 7"></polyline><line x1="15" y1="12" x2="3" y2="12"></line></svg>
          Join Workspace
        </button>
      </div>
      
      <div style="text-align:center; margin-top: 40px;">
          <button class="btn" id="btn-logout-global" style="background:transparent; border:none; color:var(--c-text-3); font-size: 13px;">Sign Out</button>
      </div>
    </div>
  `;

  // Fetch workspaces
  const listContainer = page.querySelector('#workspace-list');
  try {
    const workspaces = await window.API.workspaces.list();
    if (workspaces.length === 0) {
      listContainer.innerHTML = `<div style="grid-column: 1 / -1; text-align:center; color:var(--c-text-2); padding:40px; background:var(--glass-bg); backdrop-filter:blur(20px); border-radius:var(--radius-lg); border:1px dashed var(--c-border2);">No workspaces found. Create or join one to get started!</div>`;
    } else {
      listContainer.innerHTML = workspaces.map(w => `
        <div class="ws-card" data-id="${w.id}" style="padding: 24px; background:var(--glass-bg); backdrop-filter:blur(10px); border:1px solid var(--c-border); border-radius:var(--radius-lg); cursor:pointer; transition:all 0.3s cubic-bezier(0.4,0,0.2,1); position:relative; overflow:hidden;">
          <div style="position:absolute; top:0; left:0; width:100%; height:4px; background:linear-gradient(90deg, var(--c-primary), var(--c-accent)); opacity:0; transition:opacity 0.3s;" class="card-highlight"></div>
          <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
            <div style="font-weight:700; font-size:18px; color:#fff;">${escHtml(w.name)}</div>
            <div style="font-size:11px; font-weight:600; color:${w.is_owner ? '#fbbf24' : 'var(--c-text-3)'}; background:${w.is_owner ? 'rgba(251,191,36,0.1)' : 'var(--c-surface2)'}; padding:4px 10px; border-radius:99px;">
              ${w.is_owner ? 'Owner' : 'Member'}
            </div>
          </div>
          <div style="font-size:13px; color:var(--c-text-2); display:flex; align-items:center; gap:6px;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
            ${w.is_owner ? 'Manage Workspace' : 'Enter Workspace'}
          </div>
        </div>
      `).join('');

      listContainer.querySelectorAll('.ws-card').forEach(card => {
        card.addEventListener('mouseenter', () => {
          card.style.transform = 'translateY(-4px)';
          card.style.borderColor = 'var(--c-primary)';
          card.style.boxShadow = '0 15px 30px rgba(0,0,0,0.4)';
          card.querySelector('.card-highlight').style.opacity = '1';
        });
        card.addEventListener('mouseleave', () => {
          card.style.transform = 'translateY(0)';
          card.style.borderColor = 'var(--c-border)';
          card.style.boxShadow = 'none';
          card.querySelector('.card-highlight').style.opacity = '0';
        });
        card.addEventListener('click', async () => {
            card.style.opacity = '0.5';
            try {
                const res = await window.API.workspaces.enter(card.dataset.id);
                window.API.setTokens(res.access_token, res.refresh_token);
                page.remove(); // Remove overlay on success
                window.location.reload();
            } catch(e) {
                window.notify(e.message || 'Failed to enter workspace', 'error');
                card.style.opacity = '1';
            }
        });
      });
    }
  } catch (e) {
    listContainer.innerHTML = `<div style="grid-column: 1 / -1; text-align:center; color:var(--c-danger); padding:20px; background:rgba(239,68,68,0.1); border-radius:var(--radius); border:1px solid rgba(239,68,68,0.3);">${escHtml(e.message || 'Failed to load workspaces')}</div>`;
  }

  // Modals for Create/Join
  page.querySelector('#btn-create-ws').addEventListener('click', () => {
    const name = prompt("Enter new workspace name:");
    if (!name) return;
    
    window.API.workspaces.create({ workspace_name: name })
    .then(res => {
      window.API.setTokens(res.access_token, res.refresh_token);
      page.remove();
      window.location.reload();
    }).catch(e => window.notify(e.message, 'error'));
  });

  page.querySelector('#btn-join-ws').addEventListener('click', () => {
    const code = prompt("Enter workspace join code (e.g. ABC-1234):");
    if (!code) return;
    
    window.API.workspaces.join({ join_code: code })
    .then(res => {
      window.API.setTokens(res.access_token, res.refresh_token);
      page.remove();
      window.location.reload();
    }).catch(e => window.notify(e.message, 'error'));
  });
  
  page.querySelector('#btn-logout-global').addEventListener('click', () => {
      window.API.clearTokens();
      window.location.reload();
  });
}
