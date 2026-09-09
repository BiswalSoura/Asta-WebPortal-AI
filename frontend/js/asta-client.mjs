export class ChatError extends Error {
  constructor(message, { status = 0, resetRequired = false } = {}) {
    super(message);
    this.name = 'ChatError';
    this.status = status;
    this.resetRequired = resetRequired;
  }
}

const isId = (value) => typeof value === 'string' &&
  /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(value);

export function validateMessage(value) {
  if (typeof value !== 'string' || !value.trim()) {
    throw new ChatError('Enter a question first.');
  }
  const message = value.trim();
  if (Array.from(message).length > 4000) {
    throw new ChatError('Please keep your question to 4,000 characters or fewer.');
  }
  return message;
}

export class AstaClient {
  constructor({ baseUrl = '/api/v1/chat', fetchImpl = globalThis.fetch.bind(globalThis),
    timeoutMs = 180000 } = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.fetchImpl = fetchImpl;
    this.timeoutMs = timeoutMs;
    this.conversationId = null;
    this.busy = false;
    this.resetRequired = false;
  }

  reset() {
    if (this.busy) throw new ChatError('Wait for the current reply before starting a new chat.');
    this.conversationId = null;
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
    let messageStarted = false;
    try {
      if (!this.conversationId) {
        const created = await this.post('/conversations');
        if (!isId(created?.conversation_id)) throw new ChatError('Asta returned an invalid conversation.');
        this.conversationId = created.conversation_id;
      }
      messageStarted = true;
      const reply = await this.post(`/conversations/${this.conversationId}/messages`, { message });
      if (reply?.conversation_id !== this.conversationId || typeof reply.answer !== 'string' ||
          !Array.isArray(reply.sources) || !reply.sources.every((source) => source &&
            (source.section_title == null || typeof source.section_title === 'string') &&
            (source.page_number == null || Number.isInteger(source.page_number)))) {
        throw new ChatError('Asta returned an unexpected response.');
      }
      return reply;
    } catch (error) {
      // POST has no idempotency key: never silently replay an uncertain message.
      if (messageStarted && ![422, 429].includes(error.status)) {
        this.resetRequired = true;
        error.resetRequired = true;
      }
      throw error;
    } finally {
      this.busy = false;
    }
  }
}
