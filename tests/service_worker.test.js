const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

function setup() {
  const timers = new Map();
  let timerId = 0;
  let messageListener, disconnectListener;
  const port = {
    onMessage: {addListener(fn) {messageListener = fn;}},
    onDisconnect: {addListener(fn) {disconnectListener = fn;}},
    postMessage() {},
  };
  const event = {addListener() {}};
  const context = vm.createContext({
    navigator: {userAgent: 'test'},
    setTimeout(fn) {timers.set(++timerId, fn); return timerId;},
    clearTimeout(id) {timers.delete(id);},
    chrome: {
      storage: {session: {async get() {return {};}}},
      webRequest: {onBeforeRequest: event, onBeforeSendHeaders: event, onHeadersReceived: event},
      tabs: {onRemoved: event},
      runtime: {connectNative() {return port;}, onMessage: event},
    },
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../extension/service_worker.js'), 'utf8'), context);
  return {
    timers, port,
    request: () => vm.runInContext("nativeRequest({command:'ping'})", context),
    pending: () => vm.runInContext('pending.size', context),
    respond: data => messageListener(data),
    disconnect: () => disconnectListener(),
  };
}

test('successful response clears pending request and timeout', async () => {
  const s = setup(), request = s.request();
  await s.respond({response_to: '1', ok: true});
  assert.equal((await request).ok, true);
  assert.equal(s.pending(), 0);
  assert.equal(s.timers.size, 0);
});

test('error response clears timeout', async () => {
  const s = setup(), request = s.request();
  const rejection = assert.rejects(request, /failed/);
  await s.respond({response_to: '1', ok: false, error: 'failed'});
  await rejection;
  assert.equal(s.pending(), 0);
  assert.equal(s.timers.size, 0);
});

test('disconnect rejects all requests and clears their timers', async () => {
  const s = setup();
  const requests = [s.request(), s.request()];
  const rejections = requests.map(p => assert.rejects(p, /desconectado/));
  s.disconnect();
  await Promise.all(rejections);
  assert.equal(s.pending(), 0);
  assert.equal(s.timers.size, 0);
});

test('postMessage failure clears request and timeout immediately', async () => {
  const s = setup();
  s.port.postMessage = () => {throw new Error('send failed');};
  await assert.rejects(s.request(), /send failed/);
  assert.equal(s.pending(), 0);
  assert.equal(s.timers.size, 0);
});

test('timeout rejects request and ignores a late response', async () => {
  const s = setup(), request = s.request();
  const rejection = assert.rejects(request, /Tiempo de espera/);
  for (const [id, fn] of s.timers) {s.timers.delete(id); fn();}
  await rejection;
  await s.respond({response_to: '1', ok: true});
  assert.equal(s.pending(), 0);
});
