export class ChatError extends Error {
  constructor(message, { status = 0, resetRequired = false } = {}) {
    super(message);
    this.name = 'ChatError';
    this.status = status;
    this.resetRequired = resetRequired;
  }
}

export const isId = (value) => typeof value === 'string' && value.length === 36 &&
  /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(value);

export function validateMessage(value) {
  if (typeof value !== 'string' || !value.trim()) {
    throw new ChatError('Enter a question first.');
  }
  const message = value;
  if (Array.from(message).length > 4000) {
    throw new ChatError('Please keep your question to 4,000 characters or fewer.');
  }
  return message;
}

export class AstaClient {
  constructor({ baseUrl = '/api/v1/chat', fetchImpl = globalThis.fetch.bind(globalThis),
    timeoutMs = 180000, storage = null, storageKey = SESSION_KEY, pageContext = null } = {}) {
    this.baseUrl = normalizeApiBase(baseUrl);
    this.storage = storage;
    this.storageKey = storageKey;
    this.pageContext = validatePageContext(pageContext);
    this.generation = 0;
    this.fetchImpl = fetchImpl;
    this.timeoutMs = timeoutMs;
    this.conversationId = this.restore();
    this.busy = false;
    this.resetRequired = false;
  }

  restore() {
    try {
      const id = this.storage?.getItem(this.storageKey);
      if (isId(id)) return id;
      this.storage?.removeItem(this.storageKey);
    } catch {}
    return null;
  }

  persist(id) {
    try {
      if (id) this.storage?.setItem(this.storageKey, id);
      else this.storage?.removeItem(this.storageKey);
    } catch {}
  }

  setPageContext(value) { this.pageContext = validatePageContext(value); }

  resetSession() {
    this.generation += 1;
    this.conversationId = null;
    this.persist(null);
    this.resetRequired = false;
    this.busy = false;
    this.pageContext = null;
  }

  reset() {
    if (this.busy) throw new ChatError('Wait for the current reply before starting a new chat.');
    this.conversationId = null;
    this.persist(null);
    this.resetRequired = false;
  }

  async post(path, body) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      const response = await this.fetchImpl(`${this.baseUrl}${path}`, {
        method: 'POST',
        headers: { Accept: 'application/json', ...(body ? { 'Content-Type': 'application/json' } : {}) },
        ...(body ? { body: JSON.stringify(body) } : {}),
        signal: controller.signal,
        credentials: 'omit',
        cache: 'no-store',
      });
      if (!response.ok) {
        const status = response.status;
        const message = status === 404 ? 'This conversation is unavailable. Start a new chat.' :
          status === 422 ? 'The question was rejected. Check its length and try again.' :
          status === 429 ? 'Asta is busy. Please wait before trying again.' :
          'Asta could not complete the request. Check the local server.';
        throw new ChatError(message, { status });
      }
      return await response.json();
    } catch (error) {
      if (error instanceof ChatError) throw error;
      throw new ChatError(controller.signal.aborted ?
        'The reply took too long. The server may still be processing it.' :
        'The reply could not be confirmed. Check the local server and connection.');
    } finally {
      clearTimeout(timer);
    }
  }

  async send(value) {
    const message = validateMessage(value);
    if (this.busy) throw new ChatError('A reply is already on its way.');
    if (this.resetRequired) throw new ChatError('Start a new chat before sending again.', { resetRequired: true });
    this.busy = true;
    const generation = this.generation;
    const current = () => { if (generation !== this.generation) throw new ChatError("Session reset."); };
    let messageStarted = false;
    try {
      if (!this.conversationId) {
        const created = await this.post('/conversations', this.pageContext === null ? undefined : { page_context: this.pageContext });
        current();
        if (!isId(created?.conversation_id)) throw new ChatError('Asta returned an invalid conversation.');
        this.conversationId = created.conversation_id;
        this.persist(this.conversationId);
      }
      messageStarted = true;
      const reply = await this.post(`/conversations/${this.conversationId}/messages`, { message });
      current();
      if (reply?.conversation_id !== this.conversationId || typeof reply.answer !== 'string' ||
          !Array.isArray(reply.sources) || !reply.sources.every((source) => source &&
            (source.section_title == null || typeof source.section_title === 'string') &&
            (source.page_number == null || Number.isInteger(source.page_number)))) {
        throw new ChatError('Asta returned an unexpected response.');
      }
      return reply;
    } catch (error) {
      if (generation !== this.generation) throw new ChatError("Session reset.");
      if (error.status === 404) { this.conversationId = null; this.persist(null); }
      // POST has no idempotency key: never silently replay an uncertain message.
      if (messageStarted && ![422, 429].includes(error.status)) {
        this.persist(null);
        this.resetRequired = true;
        error.resetRequired = true;
      }
      throw error;
    } finally {
      if (generation === this.generation) this.busy = false;
    }
  }
}

export const SESSION_KEY = 'aa.asta.m14.conversation-id';

export function validatePageContext(value) {
  if (value === null || value === undefined) return null;
  if (typeof value !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(value)) {
    throw new ChatError('Page context must be a non-sensitive identifier of 1–128 characters.');
  }
  return value;
}

export function normalizeApiBase(value) {
  if (typeof value !== 'string' || !value || /[\\\s?#%]/.test(value) || value.startsWith('//')) {
    throw new ChatError('Invalid API base URL.');
  }
  const relative = value.startsWith('/');
  let url;
  try { url = new URL(value, 'https://asta.invalid'); } catch { throw new ChatError('Invalid API base URL.'); }
  if ((!relative && !/^https?:\/\//.test(value)) || !['http:', 'https:'].includes(url.protocol) || url.username || url.password || /(?:^|\/)\.\.?(?:\/|$)/.test(value)) {
    throw new ChatError('Invalid API base URL.');
  }
  return (relative ? url.pathname : url.origin + url.pathname).replace(/\/+$/, '');
}
