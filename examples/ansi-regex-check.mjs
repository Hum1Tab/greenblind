// A focused check of colon-separated ANSI color parameters, not the upstream suite.
// Run with cwd set to an ansi-regex checkout/snapshot. No third-party dependencies.
import assert from 'node:assert/strict';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';

const {default: ansiRegex} = await import(pathToFileURL(resolve('index.js')).href);
const sequence = String.fromCharCode(27) + '[38:2:11:22:33m';
assert.deepEqual(sequence.match(ansiRegex()), [sequence]);
assert.equal(('before' + sequence + 'after').replace(ansiRegex(), ''), 'beforeafter');
console.log('2 focused assertions passed');
