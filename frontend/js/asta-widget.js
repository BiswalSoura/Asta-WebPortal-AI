import { mountWidget } from './asta-widget-core.mjs';
const host = document.getElementById('asta-widget');
if (host && !host.shadowRoot) mountWidget(host, { baseUrl: host.dataset.apiBase || '/api/v1/chat' });
