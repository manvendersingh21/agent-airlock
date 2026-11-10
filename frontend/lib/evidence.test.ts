import assert from 'node:assert/strict';
import test from 'node:test';
import { evidenceParts, verifiedSpans } from './evidence.ts';

test('evidence uses Unicode code points after emoji, not UTF-16 offsets', () => {
  const text = '🔐 Hi Maya';
  const parts = evidenceParts(text, [{ start: 5, end: 9, value: 'Maya', type: 'person' }]);
  assert.equal(parts.map((part) => part.text).join(''), text);
  assert.equal(parts.find((part) => part.highlighted)?.text, 'Maya');
});

test('inconsistent quotes, out-of-bounds and noninteger offsets never receive highlights', () => {
  assert.deepEqual(verifiedSpans('hello world', [
    { start: 0, end: 5, quote: 'world' }, { start: -1, end: 4 },
    { start: 0, end: 99 }, { start: 1.5, end: 3 }, { quote: 'hello' },
  ]), []);
});

test('overlapping valid evidence merges without duplicating content', () => {
  const parts = evidenceParts('abcdefghi', [{ start: 1, end: 5 }, { start: 3, end: 8 }]);
  assert.equal(parts.map((part) => part.text).join(''), 'abcdefghi');
  assert.equal(parts.filter((part) => part.highlighted).length, 1);
  assert.equal(parts.find((part) => part.highlighted)?.text, 'bcdefgh');
});
