const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function page(origin) {
  const context = vm.createContext({ URL, console, location: { origin }, document: {}, fetch() {} });
  context.window = context;
  context.window.location = context.location;
  vm.runInContext(fs.readFileSync('apps/Portal/static/js/utils.js', 'utf8'), context);
  context.serviceDefinitions = {
    comfy: { port: 5566, capabilities: {open: true} },
    copilot: { port: 7879, capabilities: {open: false} },
    controlpilot: { port: 7878, capabilities: {open: false} },
  };
  return context;
}

test('links use resolved metadata on local hosts and RunPod', () => {
  const local = page('http://localhost:7878');
  assert.equal(local.serviceUrl('comfy'), 'http://localhost:5566/');
  const pod = page('https://my-pod-7878.proxy.runpod.net');
  assert.equal(pod.serviceUrl('comfy'), 'https://my-pod-5566.proxy.runpod.net/');
  assert.equal(pod.serviceUrl('copilot'), null);
  assert.equal(pod.serviceUrl('controlpilot'), null);
  assert.equal(pod.serviceUrl('unknown'), null);
  pod.serviceDefinitions.comfy.port = null;
  assert.equal(pod.serviceUrl('comfy'), null);
});

test('protected Comfy keeps the authenticated gateway', () => {
  const pageState = page('https://my-pod-7878.proxy.runpod.net');
  pageState.controlPilotSettings = {comfy_access: {enabled:true}};
  assert.equal(pageState.serviceUrl('comfy'), 'https://my-pod-7878.proxy.runpod.net/comfy/');
});
