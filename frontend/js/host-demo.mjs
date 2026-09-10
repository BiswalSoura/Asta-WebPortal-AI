import { SESSION_KEY, isId } from './asta-client.mjs';
import { initAsta } from './asta-embed.mjs';
let context = new URL(location.href).searchParams.get('page') === 'fixture-b' ? 'fixture-b' : 'fixture-a';
const asta = initAsta({ container: document.getElementById('assistant-container'), pageContext: context });
function render() {
  let storageSummary = 'Storage unavailable';
  try {
    const stored = sessionStorage.getItem(SESSION_KEY);
    storageSummary = `Session storage: ${sessionStorage.length} key(s); Asta UUID ${stored === null ? 'absent' : isId(stored) ? 'valid' : 'invalid'}. Local storage: ${localStorage.length} key(s).`;
  } catch {}
  document.getElementById('storage-check').textContent = storageSummary;
  document.getElementById('context').textContent = asta.getPageContext() || 'Cleared';
  document.getElementById('page-title').textContent = context === 'fixture-a' ? 'Host context A' : 'Host context B';
  document.getElementById('conversation').textContent = asta.getConversationId() || 'None';
}
document.getElementById('spa').addEventListener('click', () => {
  context = context === 'fixture-a' ? 'fixture-b' : 'fixture-a';
  asta.setPageContext(context);
  history.pushState(null, '', `?page=${context}`);
  render();
});
window.addEventListener('popstate', () => {
  context = new URL(location.href).searchParams.get('page') === 'fixture-b' ? 'fixture-b' : 'fixture-a';
  asta.setPageContext(context); render();
});
document.getElementById('logout').addEventListener('click', () => { asta.resetSession(); render(); });
render();
setInterval(render, 500);

document.getElementById('expired').addEventListener('click', () => {
  asta.resetSession();
  sessionStorage.setItem(SESSION_KEY, '00000000-0000-4000-8000-000000000000');
  location.reload();
});
