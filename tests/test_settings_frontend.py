"""Exercise Settings navigation and preference-save outcomes without a live service."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SettingsFrontendTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node.js is required')
    def test_tabs_and_preference_save_outcomes(self):
        script = r'''
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor(value = '') {
    this.value = value; this.checked = false; this.dataset = {};
    this.events = {}; this.attributes = {}; this.textContent = '';
  }
  addEventListener(name, callback) { this.events[name] = callback; }
  setAttribute(name, value) { this.attributes[name] = value; }
  getAttribute(name) { return this.attributes[name]; }
  focus() { this.focused = true; }
}
(async () => {
  for (const failure of [null, '/api/settings/ui', '/api/settings/copilot-defaults']) {
    const elements = new Map();
    const get = id => {
      if (!elements.has(id)) elements.set(id, new Element());
      return elements.get(id);
    };
    const radios = ['light', 'dark'].map(value => new Element(value));
    const tabs = ['general', 'access', 'connections', 'shutdown'].map(name => {
      const el = get('settings-tab-' + name);
      el.id = 'settings-tab-' + name;
      el.setAttribute('aria-controls', 'settings-panel-' + name);
      return el;
    });
    const requests = [], applied = [];
    const context = {
      window: {
        pendingSettingsTab: 'connections', settingsReturnSection: 'models',
        applyControlPilotUiSettings: value => applied.push(['ui', value]),
        applyCopilotDrawerDefaults: value => applied.push(['copilot', value]),
      },
      document: {
        getElementById: get,
        querySelectorAll: selector => selector.includes('settings-theme') ? radios : tabs,
      },
      AbortController, URL, location: { origin: 'http://localhost' },
      fetchJson: async (url, options) => {
        if (!options?.method) return url === '/api/settings' ? {theme: 'light', comfy_access: {}} : {set: true};
        requests.push([url, JSON.parse(options.body)]);
        if (url === failure) throw new Error('{"detail":"Service unavailable"}');
        return JSON.parse(options.body);
      },
    };
    context.window.fetchJson = context.fetchJson;
    vm.runInNewContext(fs.readFileSync('apps/Portal/static/js/screen-lifecycle.js', 'utf8'), context);
    vm.runInNewContext(fs.readFileSync('apps/Portal/static/js/settings.js', 'utf8'), context);
    await context.window.initSettings();
    assert.equal(get('settings-panel-connections').hidden, false);
    assert.equal(get('settings-panel-general').hidden, true);
    assert.equal(get('settings-back-models').hidden, false);
    assert.equal(get('settings-hf-token').value, '');
    assert.match(get('settings-hf-status').textContent, /saved/i);
    tabs[1].events.click();
    assert.equal(get('settings-panel-general').hidden, true);
    assert.equal(get('settings-panel-access').hidden, false);
    assert.equal(tabs[1].attributes['aria-selected'], 'true');
    tabs[1].events.keydown({key: 'End', preventDefault() {}});
    assert.equal(tabs[3].focused, true);
    assert.equal(tabs[3].tabIndex, 0);
    assert.equal(get('settings-panel-shutdown').hidden, false);
    tabs[3].events.keydown({key: 'ArrowRight', preventDefault() {}});
    assert.equal(tabs[0].tabIndex, 0);
    radios[0].checked = false; radios[1].checked = true;
    get('settings-sidebar-compact').checked = true;
    get('settings-copilot-allow-urls').checked = true;
    get('settings-panel-general').events.change();
    assert.equal(get('settings-ui-status').textContent, 'Unsaved changes.');
    await get('settings-ui-save').events.click();
    assert.deepEqual(requests[0], ['/api/settings/ui', {theme:'dark', sidebar_compact:true}]);
    assert.equal(get('settings-ui-save').disabled, false);
    const status = get('settings-ui-status').textContent;
    if (failure === '/api/settings/ui') {
      assert.equal(requests.length, 1);
      assert.equal(applied.length, 0);
      assert.match(status, /Could not save preferences: Service unavailable/);
    } else {
      assert.deepEqual(requests[1], ['/api/settings/copilot-defaults', {allow_all_urls:true}]);
      assert.equal(applied[0][0], 'ui');
      if (failure) {
        assert.equal(applied.length, 1);
        assert.match(status, /Appearance saved. Copilot preferences were not saved: Service unavailable/);
      } else {
        assert.equal(applied[1][0], 'copilot');
        assert.equal(status, 'Preferences saved.');
      }
    }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
'''
        subprocess.run(['node', '-e', script], cwd=ROOT, check=True)
