import test from 'node:test';
import assert from 'node:assert/strict';
import { AstaClient, SESSION_KEY, normalizeApiBase, validatePageContext } from '../js/asta-client.mjs';
import { initAsta } from '../js/asta-embed.mjs';
const id = '12345678-1234-1234-1234-123456789abc';
const ok = body => ({ ok: true, json: async () => body });
const reply = { conversation_id: id, answer: '<img src=x onerror=alert(1)>', sources: [] };
function storage() {
  const data = new Map();
  return { data, getItem: key => data.get(key) ?? null, setItem: (key, value) => data.set(key, value), removeItem: key => data.delete(key) };
}
function client(store, calls = []) {
  return new AstaClient({ storage: store, fetchImpl: async (url, options) => {
    calls.push({ url, options }); return ok(url.endsWith('/messages') ? reply : { conversation_id: id });
  } });
}
test('same-tab restore reuses UUID, writes only UUID and never content or page context', async () => {
  const store = storage(); const first = client(store);
  first.setPageContext('fixture-a'); await first.send('private question');
  assert.deepEqual([...store.data], [[SESSION_KEY, id]]);
  const calls = []; const second = client(store, calls);
  await second.send('follow-up'); assert.equal(calls.length, 1);
  assert.equal(calls[0].url, `/api/v1/chat/conversations/${id}/messages`);
  assert.deepEqual([...store.data], [[SESSION_KEY, id]]);
});
test('new chat and logout clear storage; new chat next send creates conversation', async () => {
  const store = storage(), calls = [], c = client(store, calls);
  await c.send('one'); c.reset(); assert.equal(store.data.size, 0);
  await c.send('two'); assert.equal(calls.filter(c => c.url.endsWith('/conversations')).length, 2);
  c.resetSession(); assert.equal(c.conversationId, null); assert.equal(store.data.size, 0);
});
test('corrupt stored values ignored and removed, unavailable storage tolerated', async () => {
  for (const value of ['', '{}', '<script>', 'not-a-uuid']) {
    const store = storage(); store.setItem(SESSION_KEY, value);
    assert.equal(client(store).conversationId, null); assert.equal(store.data.size, 0);
  }
  const denied = { getItem() { throw Error(); }, setItem() { throw Error(); }, removeItem() { throw Error(); } };
  await client(denied).send('hello');
});
test('restored 404 clears UUID and blocks sends until explicit new chat; no replay', async () => {
  const store = storage(); store.setItem(SESSION_KEY, id); let calls = 0;
  const c = new AstaClient({ storage: store, fetchImpl: async () => { calls++; return { ok: false, status: 404 }; } });
  await assert.rejects(c.send('hello'), /unavailable/); assert.equal(store.data.size, 0);
  await assert.rejects(c.send('again'), /new chat/); assert.equal(calls, 1);
  c.reset(); assert.equal(c.resetRequired, false);
});
test('uncertain POST is not replayed and cannot be restored on navigation', async () => {
  const store = storage(); store.setItem(SESSION_KEY, id); let calls = 0;
  const c = new AstaClient({ storage: store, fetchImpl: async () => { calls++; throw Error('secret'); } });
  await assert.rejects(c.send('hello'), /could not be confirmed/);
  assert.equal(calls, 1); assert.equal(store.data.size, 0);
});
test('logout during creation prevents late UUID persistence and message submission', async () => {
  const store = storage(); let release; let calls = 0;
  const c = new AstaClient({ storage: store, fetchImpl: () => { calls++; return new Promise(r => { release = r; }); } });
  const pending = c.send('hello'); c.resetSession(); release(ok({ conversation_id: id }));
  await assert.rejects(pending, /reset/); assert.equal(calls, 1); assert.equal(store.data.size, 0); assert.equal(c.busy, false);
});
test('page context validates and updates only creation metadata; message contract unchanged', async () => {
  const calls = []; const c = client(storage(), calls);
  c.setPageContext('fixture-a'); await c.send('one'); c.setPageContext('fixture-b'); await c.send('two');
  assert.deepEqual(JSON.parse(calls[0].options.body), { page_context: 'fixture-a' });
  assert.deepEqual(JSON.parse(calls[2].options.body), { message: 'two' });
  assert.equal(c.pageContext, 'fixture-b');
  for (const value of ['<img>', 'a/b', 'a\n', 'x'.repeat(129), { role: 'admin' }, '']) assert.throws(() => validatePageContext(value));
});
test('API base accepts exact HTTP(S) or root-relative paths and rejects unsafe forms', () => {
  assert.equal(normalizeApiBase('/api/v1/chat///'), '/api/v1/chat');
  assert.equal(normalizeApiBase('https://api.example.test/api/v1/chat/'), 'https://api.example.test/api/v1/chat');
  for (const value of ['javascript:alert(1)', '//evil.test', 'https://user:pass@example.test', '/api?token=x', '/a#b', '/a/../b', '/a%2fb', 'api/chat', '/a\\b', ' https://x']) assert.throws(() => normalizeApiBase(value));
});
// A minimal event-capable DOM double exercises the real mount and render code without dependencies.
class Element {
  constructor(doc) { this.ownerDocument = doc; this.children = []; this.attributes = new Map(); this.events = {}; this.value = ''; this.hidden = false; this.textContent = ''; }
  append(...children) { this.children.push(...children); }
  setAttribute(k,v) { this.attributes.set(k,v); }
  hasAttribute(k) { return this.attributes.has(k); }
  attachShadow() { this.shadowRoot = new Element(this.ownerDocument); return this.shadowRoot; }
  set innerHTML(value) { this.template = value; this.selectors = new Map(); }
  querySelector(key) { if (!this.selectors.has(key)) this.selectors.set(key, new Element(this.ownerDocument)); return this.selectors.get(key); }
  addEventListener(type, cb) { this.events[type] = cb; }
  replaceChildren(...children) { this.children = children; }
  focus() {}
  async trigger(type) { return this.events[type]?.({ preventDefault() {} }); }
}
function dom() {
  const doc = { createElement: () => new Element(doc), defaultView: { events: {}, addEventListener(type, cb) { this.events[type] = cb; } } }; doc.body = new Element(doc);
  globalThis.document = doc; globalThis.sessionStorage = storage(); return doc;
}
test('arbitrary host mounts once with isolated template, safe label and rejects identity config', () => {
  const doc = dom(); const container = doc.createElement();
  const api = initAsta({ container, launcherLabel: '<b>Asta</b>', pageContext: 'fixture-a' });
  assert.equal(initAsta({ container }), api); assert.equal(container.children.length, 1);
  assert.throws(() => initAsta({ container: doc.createElement() }), /already mounted/);
  const root = container.children[0].shadowRoot;
  assert.equal(root.querySelector('.asta-launcher span').textContent, '<b>Asta</b>');
  assert.throws(() => initAsta({ container, user_role: 'admin' }));
  assert.throws(() => api.setPageContext('<script>'));
  api.setPageContext('fixture-b'); assert.equal(api.getPageContext(), 'fixture-b');
});
test('host logout clears transcript, draft, errors and UUID; late answer never returns to UI', async () => {
  const doc = dom(); let release;
  globalThis.sessionStorage.setItem(SESSION_KEY, id);
  const original = globalThis.fetch; globalThis.fetch = () => new Promise(r => { release = r; });
  try {
    const api = initAsta(); const root = doc.body.children[0].shadowRoot;
    root.querySelector('textarea').value = 'private message';
    const pending = root.querySelector('form').trigger('submit');
    api.resetSession(); release(ok(reply)); await pending;
    assert.equal(api.getConversationId(), null); assert.equal(globalThis.sessionStorage.data.size, 0);
    assert.equal(root.querySelector('textarea').value, '');
    assert.equal(root.querySelector('.asta-messages').children.length, 1);
    assert.equal(root.querySelector('.asta-error').textContent, '');
    assert.equal(api.getPageContext(), null);
  } finally { globalThis.fetch = original; }
});

test('back-forward cache resumes from current storage and clears obsolete UI', () => {
  const doc = dom(); globalThis.sessionStorage.setItem(SESSION_KEY, id);
  const api = initAsta(); const root = doc.body.children[0].shadowRoot;
  root.querySelector('textarea').value = 'old account draft';
  globalThis.sessionStorage.removeItem(SESSION_KEY);
  doc.defaultView.events.pageshow({ persisted: true });
  assert.equal(api.getConversationId(), null);
  assert.equal(root.querySelector('textarea').value, '');
  globalThis.sessionStorage.setItem(SESSION_KEY, id);
  doc.defaultView.events.pageshow({ persisted: true });
  assert.equal(api.getConversationId(), id);
});
test('real widget renders hostile answer as text and New chat clears UI plus stored UUID', async () => {
  const doc = dom(); const original = globalThis.fetch;
  globalThis.fetch = async url => ok(url.endsWith('/messages') ? reply : { conversation_id: id });
  try {
    const api = initAsta(); const root = doc.body.children[0].shadowRoot;
    root.querySelector('textarea').value = 'question';
    await root.querySelector('form').trigger('submit');
    const bubbles = root.querySelector('.asta-messages').children;
    assert.equal(bubbles[2].children[1].textContent, reply.answer);
    assert.equal(bubbles[2].children[1].children.length, 0);
    assert.deepEqual([...globalThis.sessionStorage.data], [[SESSION_KEY, id]]);
    await root.querySelector('.asta-new').trigger('click');
    assert.equal(root.querySelector('.asta-messages').children.length, 1);
    assert.equal(api.getConversationId(), null);
    assert.equal(globalThis.sessionStorage.data.size, 0);
  } finally { globalThis.fetch = original; }
});
