const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = module.constructor;
const ts = require('typescript');

function compileModule(rel, overrides = {}) {
  const filepath = path.join(__dirname, '..', rel);
  const source = fs.readFileSync(filepath, 'utf8')
    .replace('import.meta.env.VITE_API_BASE_URL', '"https://api.example.test"');
  const built = ts.transpileModule(source, {
    fileName: filepath, reportDiagnostics: true,
    compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022},
  });
  assert.ok(!built.diagnostics?.length, JSON.stringify(built.diagnostics));
  const compiled = new Module(filepath, module);
  compiled.filename = filepath;
  compiled.paths = module.paths;
  const oldRequire = compiled.require.bind(compiled);
  compiled.require = name => Object.hasOwn(overrides, name) ? overrides[name] : oldRequire(name);
  compiled._compile(built.outputText, filepath);
  return compiled.exports;
}

global.window = {location:{origin:'http://localhost:3000'}};
const dateTime = compileModule('src/utils/dateTime.ts');
const api = compileModule('src/utils/api.ts', {'./dateTime':dateTime});
const lobbyId = '1d01939b-2aa8-497b-b04d-f83e3302d298';
const stubLobby = {id:lobbyId, title:'Lab', subject:'ITE', language:'python', max_students:35,
 status:'ACTIVE', created_at:'2026-11-16T00:00:00Z', expires_at:'2026-11-16T02:00:00Z'};
const stubSubmission = {id:9, lobby_id:lobbyId, student_id:'221', file_name:'answer.py', language:'python',
 status:'pending', ai_probability:null, risk_level:null, created_at:'2026-11-16T01:00:00Z'};
const responses = [];
function response(status, data) {
  return {status, ok:status<400, headers:{get:()=> 'application/json'},json:async()=>data};
}
async function test() {
  global.fetch = async (url, options) => {
    responses.push({url, options});
    if (String(url).endsWith('/instructor/dashboard')) return response(200, {lobbies:[stubLobby],submissions:[stubSubmission]});
    if (String(url).endsWith('/lobbies/'+lobbyId+'/lock')) return response(200, {...stubLobby, status:'LOCKED'});
    throw Error('Unexpected request: '+url);
  };
  const data = await api.loadInstructorData('test-token');
  assert.equal(responses.length, 1, 'One request for dashboard, not N+1');
  assert.match(responses[0].url, /\/instructor\/dashboard$/);
  assert.equal(data.lobbies.length, 1);
  assert.equal(data.submissions.length, 1);
  assert.equal(data.submissions[0].sourceCode, '', 'Dashboard must not include code');
  assert.equal(new Headers(responses[0].options.headers).get('Authorization'),'Bearer test-token');
  assert.ok(responses[0].options.signal instanceof AbortSignal, 'Requests must be cancellable');
  const locked = await api.setLobbyLocked('test-token', lobbyId, true);
  assert.equal(locked.status, 'LOCKED');
  assert.equal(responses.length, 2);
  // WebSocket is a conservative polling accelerator, not the only data source.
  const statuses = [];
  const sockets = [];
  class FakeSocket {
    static OPEN = 1;
    constructor(url, protocols) {this.url=url;this.protocols=protocols;this.readyState=1;sockets.push(this);}
    send(){}
    close(){this.readyState=3;this.onclose?.({code:1000});}
  }
  global.WebSocket=FakeSocket;
  const unsubscribe = api.subscribeToLobbyUpdates('test-token', [lobbyId], ()=>{}, connected=>statuses.push(connected));
  assert.equal(sockets.length,1);
  assert.equal(new URL(sockets[0].url).search, "", "JWT must not be in request URL");
  assert.deepEqual(sockets[0].protocols, ["codeauthentic", "auth.test-token"]);
  sockets[0].onopen();
  assert.deepEqual(statuses,[true]);
  sockets[0].close();
  assert.deepEqual(statuses,[true,false]);
  unsubscribe();
  console.log('Performance frontend integration: one dashboard request, lock response, abort signal, socket connection lifecycle PASS');
}
test().catch(err=>{console.error(err);process.exitCode=1;});
