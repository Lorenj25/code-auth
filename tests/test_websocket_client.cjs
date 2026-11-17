// Offline TypeScript-level integration tests: live socket + code-view API + timestamps.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const Module = module.constructor;

function compileModule(rel, overrides = {}) {
  const file = path.join(__dirname, '..', rel);
  const source = fs.readFileSync(file, 'utf8')
    .replace('import.meta.env.VITE_API_BASE_URL', '"https://api.example.test"');
  const compiled = ts.transpileModule(source, {
    fileName: file,
    reportDiagnostics: true,
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  });
  assert.ok(!compiled.diagnostics?.length, rel + ': ' + JSON.stringify(compiled.diagnostics));
  const instance = new Module(file, module);
  instance.filename = file;
  instance.paths = module.paths;
  const originalRequire = instance.require.bind(instance);
  instance.require = request => Object.prototype.hasOwnProperty.call(overrides, request)
    ? overrides[request] : originalRequire(request);
  instance._compile(compiled.outputText, file);
  return instance.exports;
}

const time = compileModule('src/utils/dateTime.ts');
assert.equal(time.utcTimestamp('2026-11-16T04:30:00'), '2026-11-16T04:30:00Z');
assert.equal(time.utcTimestamp('2026-11-16T04:30:00Z'), '2026-11-16T04:30:00Z');
assert.match(time.formatPhilippineTime('2026-11-16T04:30:00Z'), /12:30\s?PM/i);
assert.match(time.formatPhilippineDateTime('2026-11-16T04:30:00'), /12:30\s?PM/i);

global.window = { location: { origin: 'https://frontend.example.test' } };
const sockets = [];
class FakeSocket {
  static OPEN = 1;
  constructor(url, protocols) { this.url = url; this.protocols = protocols; this.readyState = FakeSocket.OPEN; sockets.push(this); }
  send(message) { this.lastMessage = message; }
  close() { this.readyState = 3; if (this.onclose) this.onclose({ code: 1000 }); }
}
global.WebSocket = FakeSocket;
const api = compileModule('src/utils/api.ts', {'./dateTime': time});
let count = 0;
const unsubscribe = api.subscribeToLobbyUpdates('fake-test-token', ['lobby-one', 'lobby-two'], () => count++);
assert.equal(sockets.length, 2);
assert.equal(new URL(sockets[0].url).protocol, 'wss:');
assert.equal(new URL(sockets[0].url).pathname, '/ws/lobbies/lobby-one');
assert.equal(new URL(sockets[0].url).searchParams.get('token'), null, 'Do not leak JWT in WebSocket URLs');
assert.deepEqual(sockets[0].protocols, ['codeauthentic', 'auth.fake-test-token']);
sockets[0].onopen();
assert.equal(count, 0, 'Opening the initial socket must not issue a redundant dashboard request');
sockets[0].onmessage({ data: JSON.stringify({ type: 'submission_created' }) });
sockets[1].onmessage({ data: JSON.stringify({ type: 'submission_updated' }) });
assert.equal(count, 2);
sockets[0].onmessage({ data: 'pong' });
assert.equal(count, 2);
unsubscribe();
assert.ok(sockets.every(socket => socket.readyState === 3));

function fakeJsonResponse(status, body) {
  return {
    status, ok: status < 400, headers: { get: () => 'application/json' },
    json: async () => body,
  };
}
async function testApi() {
  let lastRequest;
  global.fetch = async (url, options) => {
    lastRequest = { url, options };
    return fakeJsonResponse(200, { id: 14, lobby_id: 'abcd-xyz', source_code: 'print(1)', token_count: 42 });
  };
  const code = await api.getSubmissionCode('instructor-token', 'abcd-xyz', '14');
  assert.deepEqual(code, { sourceCode: 'print(1)', tokenCount: 42 });
  assert.match(lastRequest.url, /\/lobbies\/abcd-xyz\/submissions\/14\/code$/);
  assert.equal(new Headers(lastRequest.options.headers).get('Authorization'), 'Bearer instructor-token');
  assert.equal(lastRequest.options.cache, 'no-store');
  global.fetch = async () => fakeJsonResponse(404, { detail: 'Not Found' });
  await assert.rejects(api.getSubmissionCode('token', 'abcd-xyz', '14'), /backend is outdated/i);
  global.fetch = async () => fakeJsonResponse(404, { detail: 'Submission not found in your lobby.' });
  await assert.rejects(api.getSubmissionCode('token', 'abcd-xyz', '14'), /not found in your instructor lobby/i);
  const mod = compileModule('src/utils/api.ts', {'./dateTime': time});
  assert.equal(typeof mod.subscribeToLobbyUpdates, 'function');
}
testApi().then(() => console.log('Frontend integration tests passed: date/time, live sockets, cleanup, source-code API/auth/errors.'))
.catch(error => { console.error(error); process.exitCode = 1; });
