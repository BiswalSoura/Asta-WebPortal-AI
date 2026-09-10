import { mountWidget } from './asta-widget-core.mjs';
import { normalizeApiBase, validatePageContext } from './asta-client.mjs';

const documents = new WeakMap();

export function initAsta({ container = document.body, apiBase = '/api/v1/chat',
  launcherLabel = 'Ask Asta', pageContext = null, ...unknown } = {}) {
  if (Object.keys(unknown).length) throw new TypeError('Unsupported Asta configuration field.');
  if (!container || typeof container.append !== 'function') throw new TypeError('A container element is required.');
  if (typeof launcherLabel !== 'string' || !launcherLabel.trim() || launcherLabel.length > 80) throw new TypeError('Invalid launcher label.');
  const baseUrl = normalizeApiBase(apiBase);
  validatePageContext(pageContext);
  const mounted = documents.get(container.ownerDocument);
  if (mounted && mounted.container !== container) throw new TypeError('Asta is already mounted in this document.');
  let storage = null;
  try { storage = globalThis.sessionStorage; } catch {}
  let host = Array.from(container.children).find(child => child.hasAttribute('data-asta-embed'));
  if (!host) {
    host = container.ownerDocument.createElement('div');
    host.setAttribute('data-asta-embed', '');
    container.append(host);
  }
  const api = mountWidget(host, { baseUrl, launcherLabel, pageContext, storage });
  documents.set(container.ownerDocument, { container, api });
  return api;
}
