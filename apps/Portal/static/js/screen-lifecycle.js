// One instance per mounted screen. Never look up a newer instance after an await.
window.createScreenLifecycle = function () {
  const controller = new AbortController();
  const cleanups = new Set(), latest = new Map();
  const scope = {
    signal: controller.signal,
    get active() { return !controller.signal.aborted; },
    check() { controller.signal.throwIfAborted(); },
    onCleanup(cleanup) {
      if (!scope.active) { cleanup(); return () => {}; }
      cleanups.add(cleanup);
      return () => cleanups.delete(cleanup);
    },
    dispose() {
      if (!scope.active) return;
      controller.abort();
      for (const cleanup of cleanups) {
        try { cleanup(); } catch (error) { console.error('Screen cleanup failed', error); }
      }
      cleanups.clear();
      latest.clear();
    },
    // Independent operations share the screen; competing reads share a key.
    latest(key) {
      latest.get(key)?.dispose();
      const child = window.createScreenLifecycle();
      latest.set(key, child);
      const unlink = scope.onCleanup(() => child.dispose());
      child.onCleanup(unlink);
      return child;
    },
    async json(url, options = {}) {
      scope.check();
      const request = new AbortController();
      const abort = () => request.abort();
      const unlink = scope.onCleanup(abort);
      const external = options.signal;
      external?.addEventListener('abort', abort, {once: true});
      if (external?.aborted) abort();
      try {
        request.signal.throwIfAborted();
        const result = await window.fetchJson(url, {...options, signal: request.signal});
        request.signal.throwIfAborted();
        scope.check();
        return result;
      } finally {
        unlink();
        external?.removeEventListener('abort', abort);
      }
    },
    async text(url) {
      scope.check();
      const response = await fetch(url, {signal: scope.signal});
      if (!response.ok) throw new Error('View unavailable');
      const text = await response.text();
      scope.check();
      return text;
    },
    timeout(callback, delay) {
      if (!scope.active) return null;
      const timer = setTimeout(() => {
        unlink();
        if (scope.active) callback();
      }, delay);
      const unlink = scope.onCleanup(() => clearTimeout(timer));
      return timer;
    },
    poll(callback, delay) {
      const tick = async () => {
        if (!scope.active) return;
        try { await callback(); }
        catch (error) { if (scope.active) console.error('Screen poll failed', error); }
        finally { scope.timeout(tick, delay); }
      };
      void tick();
    },
  };
  return scope;
};
