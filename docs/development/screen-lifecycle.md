# ControlPilot screen lifecycle

ControlPilot keeps one screen lifecycle for each navigation. Opening a page, including the page already on screen, creates a fresh instance. Leaving it or showing the password gate disposes the previous instance. The route loader passes this instance into the screen initializer, so the HTML request and the work started by the screen have the same owner.

The implementation lives in `apps/Portal/static/js/screen-lifecycle.js`. It deliberately stays small: an abort signal, guarded JSON and HTML requests, cleanup callbacks, timers, serial polling, and named operations that replace an earlier operation. Workspace activity, Copilot availability, and the global shutdown notice have application lifetimes and remain independent of page navigation.

## Keep the original screen with the request

Capture the lifecycle at the start of an asynchronous action. Use `screen.json()` for API calls. It attaches cancellation to the request and checks again after the response body has been read. This second check prevents a late result from being used even when a transport or test fixture does not honour cancellation.

```javascript
async function refreshStatus() {
  const screen = trainingScreen;
  if (!screen?.active) return;
  try {
    const status = await screen.json('/api/example/status');
    renderStatus(status);
  } catch (error) {
    if (!screen.active) return;
    showStatusError(error.message);
  }
}
```

The captured instance matters. Looking up the current screen after an `await` can mistake an old request for work belonging to a newer visit. Checking whether an element exists has the same problem when the user leaves a page and returns before the old request finishes.

Error handlers and `finally` blocks must also check the captured instance before changing shared state or controls. After awaiting a helper that handles its own cancellation, check `screen.active` before continuing. For asynchronous work outside the request helper, such as reading the clipboard, call `screen.check()` before applying the result.

## Let the latest selection win

Some requests compete while the user stays on one screen. Docs tabs and guided-training preflight checks use `screen.latest('document')` or another meaningful key. Starting another operation with that key disposes its predecessor. Different keys remain independent, and disposing the parent screen disposes all of them.

Use this only where a newer selection supersedes an older read. Cancelling a request does not undo a save, delete, download, or training job that the server has already accepted. Returning to a screen reloads server state. The global activity bar continues to watch backend work while its original screen is closed.

## Give background work an owner

Use `screen.poll(callback, milliseconds)` for repeated status reads. It waits for the callback to finish before scheduling another attempt, so a slow server cannot accumulate overlapping polls. The callback should render its own recoverable errors. Disposal cancels pending requests and timers, and a late callback cannot restart the loop.

Use `screen.timeout()` for delayed screen work. Register other resources with `screen.onCleanup()`, such as an upload's `XMLHttpRequest.abort()`, a WebSocket close, or removal of a window listener. Cleanup is idempotent. WebSocket handlers must still check the captured screen before rendering because already-queued events can arrive after close.

## Verify the boundary

The Node regression tests in `tests/test_screen_lifecycle.js` exercise cancellation, response-body races, competing reads, serial polling, cleanup, late authentication errors, Docs tab changes, and leaving and returning to Services. The existing ControlPilot regressions cover route races, settings preservation, and training preparation. Run them with `node --test tests/test_screen_lifecycle.js tests/test_controlpilot_regressions.js tests/test_workspace_frontend.js`.

Browser checks use delayed local API fixtures to verify that the current page and selected tab remain visible after earlier work finishes. These checks validate the frontend lifecycle; they do not establish that a Docker image was published or that GPU training succeeded.
