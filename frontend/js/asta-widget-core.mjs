import { AstaClient, validateMessage } from './asta-client.mjs';

const mounts = new WeakMap();

// Only paired **bold** is interpreted. Every other character remains literal text.
export function formatAnswer(body, text) {
  const parts = text.split(/(\*\*[^*\n]+\*\*)/g);
  if (parts.length === 1) { body.textContent = text; return; }
  body.replaceChildren();
  for (const part of parts) {
    if (!part) continue;
    const bold = part.startsWith('**') && part.endsWith('**');
    const node = body.ownerDocument.createElement(bold ? 'strong' : 'span');
    node.textContent = bold ? part.slice(2, -2) : part;
    body.append(node);
  }
}

export function mountWidget(host, options = {}) {
  if (!host || typeof host.attachShadow !== 'function') throw new TypeError('A host element is required.');
  if (mounts.has(host)) return mounts.get(host);
  if (host.shadowRoot) throw new TypeError('Host already has a shadow root.');
  const client = new AstaClient(options);
  let generation = 0;
  const root = host.attachShadow({ mode: 'open' });
  // Only this fixed template uses HTML. User messages, answers and sources use textContent.
  root.innerHTML = `
    <link rel="stylesheet" href="${new URL('../css/asta-widget.css', import.meta.url).href}">
    <button class="asta-launcher" type="button" aria-expanded="false" aria-controls="asta-panel">✦ <span>Ask Asta</span></button>
    <section class="asta-panel" id="asta-panel" role="dialog" aria-labelledby="asta-title" hidden>
      <header class="asta-header">
        <div class="asta-avatar" aria-hidden="true">A</div>
        <div class="asta-heading"><h2 id="asta-title">Asta</h2><p>Your WebPortal assistant</p></div>
        <button class="asta-close" type="button" aria-label="Close chat">×</button>
      </header>
      <div class="asta-toolbar"><span>Local conversation</span><button class="asta-new" type="button">New chat</button></div>
      <div class="asta-messages" role="log" aria-label="Conversation" aria-live="polite" aria-relevant="additions text"></div>
      <p class="asta-status" role="status"></p>
      <p class="asta-error" role="alert" hidden></p>
      <form class="asta-form">
        <label for="asta-question">Ask about WebPortal</label>
        <textarea id="asta-question" rows="2" placeholder="Type your question…" aria-describedby="asta-help"></textarea>
        <div class="asta-compose-bottom"><span id="asta-help">Enter to send · Shift+Enter for a new line</span><button class="asta-send" type="submit" disabled>Send ↑</button></div>
      </form>
    </section>`;
  const get = (selector) => root.querySelector(selector);
  const panel = get('.asta-panel');
  const launcher = get('.asta-launcher');
  const input = get('textarea');
  const send = get('.asta-send');
  const newChat = get('.asta-new');
  const messages = get('.asta-messages');
  const status = get('.asta-status');
  const errorBox = get('.asta-error');
  get('.asta-launcher span').textContent = options.launcherLabel || 'Ask Asta';

  function sync() {
    input.disabled = client.busy;
    newChat.disabled = client.busy;
    send.disabled = client.busy || client.resetRequired || !input.value.trim();
    panel.setAttribute('aria-busy', String(client.busy));
  }
  function showError(message) {
    errorBox.textContent = message;
    errorBox.hidden = !message;
  }
  function append(role, text, sources = []) {
    const article = document.createElement('article');
    article.className = `asta-message asta-${role}`;
    const name = document.createElement('strong');
    name.textContent = role === 'user' ? 'You' : 'Asta';
    const body = document.createElement('p');
    if (role === 'assistant') formatAnswer(body, text);
    else body.textContent = text;
    article.append(name, body);
    if (sources.length) {
      const details = document.createElement('details');
      const summary = document.createElement('summary');
      summary.textContent = `Sources (${sources.length})`;
      const list = document.createElement('ul');
      for (const source of sources) {
        const item = document.createElement('li');
        item.textContent = `${source.section_title || 'Approved WebPortal documentation'}${source.page_number == null ? '' : ` · Page ${source.page_number}`}`;
        list.append(item);
      }
      details.append(summary, list);
      article.append(details);
    }
    messages.append(article);
    messages.scrollTop = messages.scrollHeight;
    return article;
  }
  function welcome() {
    append('assistant', "Hi, I'm Asta. What would you like to know about WebPortal?");
  }
  function setOpen(open) {
    panel.hidden = !open;
    launcher.setAttribute('aria-expanded', String(open));
    if (open) (input.disabled ? get('.asta-close') : input).focus();
    else launcher.focus();
  }
  launcher.addEventListener('click', () => setOpen(panel.hidden));
  get('.asta-close').addEventListener('click', () => setOpen(false));
  root.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !panel.hidden) { event.preventDefault(); setOpen(false); }
  });
  input.addEventListener('input', sync);
  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      if (!send.disabled) get('form').requestSubmit();
    }
  });
  newChat.addEventListener('click', () => {
    if (client.busy) return;
    const keepDraft = client.resetRequired;
    client.reset();
    messages.replaceChildren();
    if (!keepDraft) input.value = '';
    status.textContent = '';
    showError('');
    welcome();
    sync();
    input.focus();
  });
  get('form').addEventListener('submit', async (event) => {
    event.preventDefault();
    if (client.busy || client.resetRequired) return;
    let question;
    try { question = validateMessage(input.value); }
    catch (error) { showError(error.message); return; }
    showError('');
    const bubble = append('user', question);
    input.value = '';
    status.textContent = 'Asta is thinking… The first knowledge answer may take a little longer.';
    const requestGeneration = generation;
    const pending = client.send(question);
    sync();
    try {
      const reply = await pending;
      if (requestGeneration !== generation) return;
      append('assistant', reply.answer, reply.sources);
    } catch (error) {
      if (requestGeneration !== generation) return;
      const note = document.createElement('small');
      note.textContent = 'Reply not received';
      bubble.append(note);
      input.value = question;
      showError(`${error.message}${error.resetRequired && error.status !== 404 ? ' Start a new chat before sending again; your question is preserved.' : ''}`);
    } finally {
      if (requestGeneration !== generation) return;
      status.textContent = '';
      sync();
      if (!panel.hidden) (client.resetRequired ? newChat : input).focus();
    }
  });
  welcome();
  const api = Object.freeze({
    setPageContext: (value) => client.setPageContext(value),
    getPageContext: () => client.pageContext,
    getConversationId: () => client.conversationId,
    resetSession() {
      generation += 1;
      client.resetSession();
      messages.replaceChildren();
      input.value = '';
      status.textContent = '';
      showError('');
      welcome();
      sync();
      setOpen(false);
    },
    open: () => setOpen(true),
    close: () => setOpen(false),
  });
  // Back/forward cache may revive an old document after another page reset the session.
  if (options.storage) host.ownerDocument.defaultView?.addEventListener('pageshow', (event) => {
    if (!event.persisted) return;
    const restored = client.restore();
    const context = client.pageContext;
    api.resetSession();
    client.conversationId = restored;
    client.persist(restored);
    client.setPageContext(context);
  });
  mounts.set(host, api);
  return api;
}
