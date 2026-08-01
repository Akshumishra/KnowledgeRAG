import { state, notify, parseApiError } from '../app.js';
import { streamChat, reconnectStream, conversations, providers } from '../api.js';

function md(text) {
  if (!text) return '';

  if (typeof marked !== 'undefined') {
    let html = marked.parse(text, { gfm: true, breaks: true });

    html = html.replace(/<pre><code class="(.*?)">([\s\S]*?)<\/code><\/pre>/g, (match, cls, code) => {
      const lang = cls.replace('language-', '');
      return `<pre><button class="code-copy-btn" onclick="copyCode(this)">Copy</button><code class="${lang}">${code}</code></pre>`;
    });
    html = html.replace(/<pre><code>([\s\S]*?)<\/code><\/pre>/g, (match, code) => {
      return `<pre><button class="code-copy-btn" onclick="copyCode(this)">Copy</button><code>${code}</code></pre>`;
    });

    return `<div class="md-content">${html}</div>`;
  }

  let html = text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
      `<pre><button class="code-copy-btn" onclick="copyCode(this)">Copy</button><code class="${lang}">${code.trim()}</code></pre>`)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
    .replace(/^\s*[-*+] (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/^(?!<[hbupoli])(.+)$/gm, '$1');
  return `<div class="md-content"><p>${html}</p></div>`;
}

window.copyCode = function (btn) {
  const code = btn.nextSibling?.textContent || '';
  navigator.clipboard.writeText(code).then(() => {
    btn.textContent = 'Copied!';
    setTimeout(() => btn.textContent = 'Copy', 2000);
  });
};

function escHtml(str) {
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

let _messages = [];

function estimateTokens(text) {
  return Math.max(1, Math.round((text || '').length / 4));
}

function tokenBadgeHtml(info) {
  if (!info) return '';
  const parts = [];
  if (info.total != null) parts.push(`<span class="token-badge" title="Total tokens">${info.total.toLocaleString()} tok</span>`);
  if (info.prompt != null) parts.push(`<span class="token-badge dim" title="Prompt tokens">↑${info.prompt.toLocaleString()}</span>`);
  if (info.completion != null) parts.push(`<span class="token-badge dim" title="Completion tokens">↓${info.completion.toLocaleString()}</span>`);
  if (info.estimated) parts.push(`<span class="token-badge dim" title="Estimated (client-side)">~est</span>`);
  if (info.model != null) parts.push(`<span class="token-badge" title="Model">${info.model}</span>`);
  if (info.latency_ms != null) parts.push(`<span class="token-badge" title="Latency">${info.latency_ms.toFixed(0)} ms</span>`);
  return parts.join('');
}

export function renderChat(container) {
  _messages = [];
  container.innerHTML = `
    <div id="chat-panel">
      <div class="chat-header">
        <div class="chat-header-title">${state.currentConversation?.title || 'New Conversation'}</div>
        <div style="flex:1;"></div>
      </div>

      <div class="messages-container" id="messages-container">
        ${state.currentConversation ? '' : renderEmptyState()}
      </div>

      <div class="input-area">
        <div class="provider-selector-bar" id="provider-selector-bar" style="display:flex; gap:8px; flex-wrap:wrap; background:var(--c-surface); padding:8px; border-bottom:1px solid var(--c-border); align-items:center;">
          <span style="font-size:11px;color:var(--c-text-3);">Provider:</span>
          <select id="provider-select" class="provider-select" style="min-width:100px;">
            <option value="">Loading...</option>
          </select>
          <span style="font-size:11px;color:var(--c-text-3); margin-left:8px;">Model:</span>
          <select id="model-select" class="form-control" style="width:140px; padding:4px 8px; font-size:12px; height:26px;">
            <!-- Populated dynamically -->
          </select>
          <div style="flex: 1;"></div>
        </div>
        <div class="input-wrapper" style="position:relative;">
          <textarea id="chat-input" placeholder="Ask your Knowledge Base..." rows="1"></textarea>
          <div class="input-actions">
            <button class="send-btn" id="send-btn" title="Send">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"/>
                <polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
            </button>
            <button class="stop-btn hidden" id="stop-btn" title="Stop generation">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="4" y="4" width="16" height="16" rx="2"/></svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  `;

  const input = container.querySelector('#chat-input');
  input?.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = (input.scrollHeight) + 'px';
  });
  input?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });

  const sendBtn = container.querySelector('#send-btn');
  sendBtn?.addEventListener('click', () => {
    sendMessage();
  });

  const providerSelect = container.querySelector('#provider-select');
  const modelSelect = container.querySelector('#model-select');

  let _wsModels = {};

  const updateModels = () => {
    const provider = providerSelect.value;
    const models = (_wsModels[provider] || []).filter(Boolean);
    if (models.length === 0) {
      modelSelect.innerHTML = '<option value="">No models configured</option>';
    } else {
      modelSelect.innerHTML = models.map(m => {
        const name = m.name || m.model_name || m;
        return `<option value="${name}">${name}</option>`;
      }).join('');
    }
  };

  const loadActiveProviders = async () => {
    try {
      const [activeKeys, wsModels, allProviders] = await Promise.all([
        providers.listActive().catch(() => []),
        providers.getWorkspaceModels().catch(() => ({})),
        providers.list().catch(() => []),
      ]);
      _wsModels = wsModels || {};

      const enabledKeys = (activeKeys || []).filter(k => k.is_enabled !== false);
      const uniqueProviderIds = [...new Set(enabledKeys.map(k => k.provider_id))];

      if (uniqueProviderIds.length === 0) {
        providerSelect.innerHTML = '<option value="">No Providers Configured</option>';
        modelSelect.innerHTML = '<option value="">—</option>';
        return;
      }

      // Map dynamic provider info
      providerSelect.innerHTML = uniqueProviderIds.map(p => {
        const dbProvider = allProviders.find(x => x.id === p || x.slug === p);
        const name = dbProvider ? dbProvider.name : p;
        return `<option value="${p}">${name}</option>`;
      }).join('');

      updateModels();
    } catch (e) {
      console.error('Failed to load providers:', e);
      providerSelect.innerHTML = '<option value="">Error loading</option>';
    }
  };

  loadActiveProviders();
  providerSelect.addEventListener('change', updateModels);

  if (state.currentConversation) loadMessages(state.currentConversation.id);
}

function renderEmptyState() {
  return `
    <div class="empty-state">
      <div class="empty-icon">
        <svg width="52" height="52" viewBox="0 0 52 52" fill="none">
          <rect width="52" height="52" rx="16" fill="rgba(99,102,241,0.15)"/>
          <path d="M16 26 L26 16 L36 26" stroke="#6366f1" stroke-width="2.5" stroke-linecap="round" fill="none"/>
          <path d="M26 16 L26 38" stroke="#6366f1" stroke-width="2.5" stroke-linecap="round"/>
          <path d="M18 34 L34 34" stroke="#22d3ee" stroke-width="2" stroke-linecap="round"/>
        </svg>
      </div>
      <div class="empty-title">Ask your Knowledge Base</div>
      <div class="empty-subtitle">Ask anything. I'll retrieve relevant documents and provide accurate, cited answers.</div>
    </div>
  `;
}

async function loadMessages(id) {
  const container = document.getElementById('messages-container');
  if (!container) return;
  try {
    const conv = await conversations.get(id);
    if (!conv.messages || conv.messages.length === 0) {
      container.innerHTML = renderEmptyState();
      return;
    }

    container.innerHTML = '';
    let pendingMsgId = null;

    conv.messages.forEach(msg => {
      if (msg.status === 'thinking' || msg.status === 'generating') {
        pendingMsgId = msg.id;
        return;
      }

      if (msg.status === 'failed') {
        const errMsg = msg.error_message || 'Generation failed.';
        const el = appendMessage(msg.role, `**Error:** ${errMsg}`, false, null, null);
        el.querySelector('.message-bubble')?.classList.add('error-bubble');
        return;
      }

      let tokenInfo = null;
      if (msg.role === 'assistant' && msg.total_tokens != null) {
        tokenInfo = {
          total: msg.total_tokens,
          prompt: msg.prompt_tokens ?? null,
          completion: msg.completion_tokens ?? null,
          model: msg.model_id ?? null,
          latency_ms: msg.latency_ms ?? null,
        };
      } else if (msg.role === 'user') {
        tokenInfo = { total: estimateTokens(msg.content), estimated: true };
      }
      appendMessage(msg.role, msg.content, false, msg.sources, tokenInfo);
    });

    container.scrollTop = container.scrollHeight;

    if (pendingMsgId) {
      startMessagePolling(id, pendingMsgId);
    }
  } catch (e) {
    notify(`Failed to load messages: ${parseApiError(e)}`, 'error');
  }
}

function createStreamCallbacks(typingId) {
  let assistantText = '';
  let assistantMsgEl = null;
  let lastStats = null;
  let messageSources = null;

  return {
    onSources: (sources) => {
      messageSources = sources;
    },
    onToken: (token) => {
      document.getElementById(typingId)?.remove();
      assistantText += token;
      if (!assistantMsgEl) {
        assistantMsgEl = appendMessage('assistant', assistantText, true, messageSources);
      } else {
        const bubble = assistantMsgEl.querySelector('.message-bubble');
        if (bubble) bubble.innerHTML = md(assistantText);
      }
      const mc = document.getElementById('messages-container');
      if (mc) mc.scrollTop = mc.scrollHeight;
    },
    onStats: (stats) => {
      lastStats = stats;
      window.dispatchEvent(new CustomEvent('stats-update', { detail: stats }));
    },
    onDone: () => {
      document.getElementById(typingId)?.remove();
      if (assistantMsgEl && lastStats) {
        const meta = assistantMsgEl.querySelector('.message-meta');
        if (meta) {
          const promptTok = lastStats.prompt_tokens + (lastStats.context_tokens || 0);
          const compTok = lastStats.completion_tokens;
          const totalTok = lastStats.total_tokens;
          meta.innerHTML = `
            ${tokenBadgeHtml({
            total: totalTok,
            prompt: promptTok,
            completion: compTok,
            model: lastStats.model,
            latency_ms: lastStats.latency_ms
          })}
            <button class="message-action" onclick="navigator.clipboard.writeText(this.closest('.message').querySelector('.md-content')?.innerText||'')">Copy</button>
          `;
        }
      }
      state.streaming = false;
      state.streamCancel = null;
      updateStreamingState(false);
    },
    onError: (msg) => {
      document.getElementById(typingId)?.remove();
      const mc = document.getElementById('messages-container');
      if (mc) {
        const errEl = document.createElement('div');
        errEl.className = 'chat-error-banner';
        errEl.innerHTML = `
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          <span>${parseApiError(msg || 'Chat error')}</span>
          <button onclick="this.parentElement.remove()" style="background:none;border:none;color:inherit;cursor:pointer;margin-left:auto;opacity:0.7;">✕</button>
        `;
        mc.appendChild(errEl);
        mc.scrollTop = mc.scrollHeight;
      }
      notify(parseApiError(msg || 'Chat error'), 'error');
      state.streaming = false;
      state.streamCancel = null;
      updateStreamingState(false);
    },
  };
}

function startMessagePolling(convId, msgId) {
  const typingId = `msg-${msgId}`;
  appendTyping(typingId);
  updateStreamingState(true);

  const callbacks = createStreamCallbacks(typingId);
  state.streamCancel = reconnectStream(convId, msgId, callbacks);
}


async function sendMessage() {
  if (state.streaming) return;
  const input = document.getElementById('chat-input');
  const msg = input?.value.trim();
  if (!msg) return;

  input.value = '';
  input.style.height = 'auto';

  const emptyState = document.querySelector('.empty-state');
  if (emptyState) emptyState.remove();

  const userTokenEst = estimateTokens(msg);
  appendMessage('user', msg, false, null, { total: userTokenEst, estimated: true });

  const typingId = 'typing-' + Date.now();
  appendTyping(typingId);

  updateStreamingState(true);

  if (!state.currentConversation) {
    try {
      const conv = await conversations.create({
        title: msg.slice(0, 60) + (msg.length > 60 ? '...' : ''),
      });
      state.currentConversation = conv;
      state.conversations.unshift(conv);

      localStorage.setItem('last_conversation_id', conv.id);
      if (state.user) {
        API.users.updateActivity({ last_route: 'chat', last_conversation_id: conv.id }).catch(() => { });
      }

      const sidebar = document.getElementById('sidebar');
      if (sidebar) { const { renderSidebar } = await import('./sidebar.js'); renderSidebar(sidebar); }
    } catch (e) { notify(parseApiError(e), 'error'); }
  }

  const selProvider = document.getElementById('provider-select')?.value || 'openai';
  const selModel = document.getElementById('model-select')?.value || 'gpt-4o';

  const callbacks = createStreamCallbacks(typingId);

  const cancel = streamChat(
    {
      conversation_id: state.currentConversation?.id,
      message: msg,
      model_provider: selProvider,
      model_name: selModel,
      stream: true,
    },
    callbacks
  );

  state.streamCancel = cancel;
}

function appendMessage(role, content, live = false, sources = null, tokenInfo = null) {
  const container = document.getElementById('messages-container');
  if (!container) return null;

  const avatar = role === 'user'
    ? (state.user?.full_name?.[0] || 'U')
    : 'AI';

  let sourcesHtml = '';
  if (sources && sources.length > 0) {
    const items = sources.map((s, i) => {
      const imgUrl = s.image_url || s.metadata?.image_url;
      const imgHtml = imgUrl ? `<div style="margin-top:8px;"><img src="${imgUrl}" style="max-width:100%; border-radius:4px;" /></div>` : '';
      return `<div class="citation-item" style="margin-bottom:8px;padding:8px;background:var(--c-surface-hover);border-radius:6px;border:1px solid var(--c-border);font-size:12px;">
        <strong>[${i + 1}] ${escHtml(s.document_name || s.metadata?.document_name || 'Document')}</strong>
        ${s.similarity_score ? `(Score: ${s.similarity_score.toFixed(2)})` : ''}
        <div style="margin-top:4px;color:var(--c-text-2);overflow-wrap:break-word;max-height:80px;overflow-y:auto;">${escHtml(s.content || s.text || '')}</div>
        ${imgHtml}
      </div>`;
    }).join('');

    sourcesHtml = `
      <details class="message-sources-dropdown" style="margin-top:12px;">
        <summary style="cursor:pointer;font-size:12px;font-weight:600;color:var(--c-text-2);margin-bottom:8px;user-select:none;">
          Citations (${sources.length})
        </summary>
        <div class="citations-container" style="margin-top:8px;">
          ${items}
        </div>
      </details>
    `;
  }

  const tokenHtml = tokenBadgeHtml(tokenInfo);

  const el = document.createElement('div');
  el.className = `message ${role}`;
  el.innerHTML = `
    <div class="message-avatar">${avatar}</div>
    <div class="message-body">
      <div class="message-bubble ${live ? 'streaming' : ''}">
        ${role === 'user' ? escHtml(content) : md(content)}
      </div>
      ${sourcesHtml}
      <div class="message-meta">${tokenHtml}</div>
    </div>
  `;
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
  _messages.push({ role, content });
  return el;
}

function appendTyping(id) {
  const container = document.getElementById('messages-container');
  if (!container) return;
  const el = document.createElement('div');
  el.className = 'message assistant';
  el.id = id;
  el.innerHTML = `
    <div class="message-avatar">AI</div>
    <div class="message-body">
      <div class="message-bubble">
        <div class="typing-indicator">
          <div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>
        </div>
      </div>
    </div>
  `;
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
}

function updateStreamingState(isStreaming) {
  state.streaming = isStreaming;
  const sendBtn = document.getElementById('send-btn');
  const stopBtn = document.getElementById('stop-btn');
  const input = document.getElementById('chat-input');
  if (sendBtn) { sendBtn.classList.toggle('hidden', isStreaming); sendBtn.disabled = isStreaming; }
  if (stopBtn) stopBtn.classList.toggle('hidden', !isStreaming);
  if (input) input.disabled = isStreaming;
}

export function startNewChat() {
  state.currentConversation = null;
  const main = document.getElementById('main');
  if (main) renderChat(main);
}
