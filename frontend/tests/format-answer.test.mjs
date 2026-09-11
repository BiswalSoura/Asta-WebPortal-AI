import test from 'node:test';
import assert from 'node:assert/strict';
import { formatAnswer } from '../js/asta-widget-core.mjs';
import { validateMessage } from '../js/asta-client.mjs';

test('validation preserves the raw message including whitespace and typos', () => {
  const raw = '  Where can I craete a prject?  ';
  assert.equal(validateMessage(raw), raw);
  assert.throws(() => validateMessage(' '.repeat(4000) + 'x'));
});

function element(tag = 'p') {
  return { tag, children: [], textContent: '',
    ownerDocument: { createElement: element },
    replaceChildren() { this.children = []; },
    append(node) { this.children.push(node); },
    set innerHTML(_) { throw Error('Dynamic HTML is forbidden'); },
  };
}
test('paired bold and line breaks retain text without exposing markdown markers', () => {
  const body = element(); formatAnswer(body, 'Use **Create New Project**\nThen **APN / Parcel Number**.');
  assert.deepEqual(body.children.map(n => n.tag), ['span', 'strong', 'span', 'strong', 'span']);
  assert.equal(body.children.map(n => n.textContent).join(''), 'Use Create New Project\nThen APN / Parcel Number.');
});
for (const text of ['<script>alert(1)</script>', '<img src=x onerror=alert(1)>',
  '[click](javascript:alert(1))', '**<img src=x onerror=alert(1)>**',
  '**<script>alert(1)</script>**', '**[click](javascript:alert(1))**', '**unclosed']) {
  test(`hostile or unmatched text stays inert: ${text}`, () => {
    const body = element(); formatAnswer(body, text);
    assert.ok(body.children.every(n => ['span', 'strong'].includes(n.tag)));
    assert.ok(body.children.every(n => Object.keys(n).every(k => !['src', 'href', 'onclick', 'onerror'].includes(k))));
    assert.equal(body.children.length ? body.children.map(n => n.textContent).join('') : body.textContent,
      text.startsWith('**') && text.endsWith('**') ? text.slice(2, -2) : text);
  });
}
