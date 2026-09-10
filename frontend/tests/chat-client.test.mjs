import test from 'node:test';
import assert from 'node:assert/strict';
import { AstaClient, validateMessage } from '../js/asta-client.mjs';

const id = '12345678-1234-1234-1234-123456789abc';
const otherId = 'abcdef12-1234-1234-1234-123456789abc';
const ok = (body) => ({ ok: true, status: 200, json: async () => body });
const answer = { conversation_id: id, answer: 'APN / Parcel Number', sources: [{ section_title: 'Location', page_number: 2 }] };

test('creates once and reuses the ID for follow-ups; sends only the message field', async () => {
  const calls = [];
  const client = new AstaClient({ fetchImpl: async (url, options) => {
    calls.push({ url, options });
    return ok(url.endsWith('/messages') ? answer : { conversation_id: id, status: 'active' });
  } });
  assert.deepEqual(await client.send('  Where?  '), answer);
  await client.send('Can you explain that option?');
  assert.equal(calls.length, 3);
  assert.equal(calls[0].url, '/api/v1/chat/conversations');
  assert.equal(calls[0].options.body, undefined);
  assert.equal(calls[1].url, `/api/v1/chat/conversations/${id}/messages`);
  assert.equal(calls[2].url, calls[1].url);
  assert.deepEqual(JSON.parse(calls[1].options.body), { message: '  Where?  ' });
  assert.equal(calls[1].options.credentials, 'omit');
});

test('rejects blank and overlong input before making requests', async () => {
  const client = new AstaClient({ fetchImpl: () => assert.fail('Unexpected network request') });
  await assert.rejects(client.send(' \n '));
  await assert.rejects(client.send('a'.repeat(4001)));
  assert.equal(validateMessage('😀'.repeat(4000)).length, 8000);
});

test('blocks simultaneous sends and reset while waiting', async () => {
  let release;
  const client = new AstaClient({ fetchImpl: () => new Promise((resolve) => { release = resolve; }) });
  client.conversationId = id;
  const pending = client.send('Hello');
  await assert.rejects(client.send('Second'), /already/);
  assert.throws(() => client.reset(), /Wait/);
  release(ok(answer));
  await pending;
  assert.equal(client.busy, false);
});

test('new chat creates a new conversation on the next send', async () => {
  let creations = 0;
  const client = new AstaClient({ fetchImpl: async (url) => {
    if (!url.endsWith('/messages')) return ok({ conversation_id: ++creations === 1 ? id : otherId });
    return ok({ ...answer, conversation_id: creations === 1 ? id : otherId });
  } });
  await client.send('Hello');
  client.reset();
  await client.send('Hello again');
  assert.equal(creations, 2);
  assert.equal(client.conversationId, otherId);
});

test('404 asks for an explicit new chat and never automatically replays', async () => {
  let calls = 0;
  const client = new AstaClient({ fetchImpl: async () => { calls++; return { ok: false, status: 404 }; } });
  client.conversationId = id;
  await assert.rejects(client.send('Hello'), (error) => error.status === 404 && error.resetRequired);
  await assert.rejects(client.send('Hello'));
  assert.equal(calls, 1);
  client.reset();
  assert.equal(client.resetRequired, false);
});

test('422 and 429 preserve conversation and allow an explicit retry', async () => {
  for (const status of [422, 429]) {
    let calls = 0;
    const client = new AstaClient({ fetchImpl: async () => ++calls === 1 ? { ok: false, status } : ok(answer) });
    client.conversationId = id;
    await assert.rejects(client.send('Hello'), (error) => error.status === status && !error.resetRequired);
    assert.equal((await client.send('Edited question')).conversation_id, id);
  }
});

test('network failure and server errors do not expose internal responses or replay a message', async () => {
  for (const failure of ['network', 400, 500]) {
    let calls = 0;
    const client = new AstaClient({ fetchImpl: async () => {
      calls++;
      if (failure === 'network') throw new Error('private connection details');
      return { ok: false, status: failure, json: async () => ({ error: 'private server details' }) };
    } });
    client.conversationId = id;
    await assert.rejects(client.send('Hello'), (error) => error.resetRequired && !error.message.includes('private'));
    assert.equal(calls, 1);
    assert.equal(client.busy, false);
  }
});

test('timeout unlocks controls but requires a new chat after an uncertain POST', async () => {
  const client = new AstaClient({ timeoutMs: 5, fetchImpl: (_url, { signal }) => new Promise((_resolve, reject) => {
    signal.addEventListener('abort', () => reject(new Error('aborted')), { once: true });
  }) });
  client.conversationId = id;
  await assert.rejects(client.send('Hello'), (error) => error.resetRequired && /too long/.test(error.message));
  assert.equal(client.busy, false);
});

test('rejects malformed and mismatched response contracts', async () => {
  for (const payload of [{ ...answer, conversation_id: otherId }, { ...answer, sources: null }, { ...answer, sources: [null] }]) {
    const client = new AstaClient({ fetchImpl: async () => ok(payload) });
    client.conversationId = id;
    await assert.rejects(client.send('Hello'), (error) => error.resetRequired);
  }
});

test('failed creation never sends a message; user can explicitly try again', async () => {
  let calls = 0;
  const client = new AstaClient({ fetchImpl: async () => { calls++; return ok({ conversation_id: 'invalid' }); } });
  await assert.rejects(client.send('Hello'), /invalid conversation/);
  assert.equal(calls, 1);
  assert.equal(client.conversationId, null);
  assert.equal(client.busy, false);
  assert.equal(client.resetRequired, false);
});
