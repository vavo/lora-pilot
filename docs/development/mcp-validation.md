# MCP implementation and validation record

Date: 2026-10-03. This records source validation, not a published image or production deployment. Setup and the current contract are in [MCP connections](../configuration/mcp.md); the broader [test catalog](mcp-test-plan.md) remains the release checklist.

## Exact scope

Source baseline: `c69b044` plus the MCP implementation working-tree changes. The implementation adds private-token Streamable HTTP, owner connection/grant/approval UI, bounded unattended policies, selected read tools, durable training/comparison/export operations and authenticated artifact downloads. MCP is disabled by default; write capabilities additionally require explicit storage/GPU/operator gates.

SHA-256 source fingerprint: `a91f54c74a404cb480691d1b687427e1709f1f98ace24f3adec8afca30d49624`.

The fingerprint hashes sorted repository-relative UTF-8 paths, a NUL byte, and each file's binary SHA-256 digest. Its 29 files are all `apps/Portal/mcp_server/*.py`, `tests/test_mcp_*.py`, plus `apps/Portal/app.py`, `apps/Portal/services/{models,training_runs}.py`, `apps/Portal/static/js/settings.js`, `apps/Portal/static/views/settings.html`, `tests/test_settings_frontend.py`, `Dockerfile`, `Makefile`, `build.env.example`, `scripts/build/{install-core-stack,write-constraints}.sh`, `tests/test_build_pins.py`, `.env.example`, `config/env.defaults`, and the standard/dev/CPU Compose files. Documentation and unrelated Services UI edits are excluded.

Implementation boundaries: one Portal owner, one existing training queue, trusted installed code/admin, untrusted MCP arguments, explicit grants to workspace objects. This is not isolation between hostile OS users.

## Executed evidence

| Check | Observed result | Boundary |
|---|---|---|
| Python regression suite | 365 tests passed | macOS, Python 3.14.7, disposable fixtures; includes the 37 MCP tests |
| Dedicated MCP suite | 37 tests passed | Linux, Python 3.11.17, disposable Docker container, runtime network disabled, no user volume mounted |
| SDK roundtrips | Discovery and tool execution passed in `2026-07-28` and `legacy` client modes | Official `mcp==2.3.0` client/server with ASGI transport; not a third-party-client certification |
| Real local Portal/browser | Enable, create, edit, policy auto-approval, owner approve/reject, token rotation and revocation passed | Chromium, loopback, temporary workspace, synthetic model/data; no training submitted |
| Browser security/layout | Injected HTML label rendered as text; no page errors; desktop 1440×1000 and fresh mobile 390×844 inspected, no horizontal overflow | No physical-device or remote-proxy claim |
| Process/ledger faults | Killed subprocesses at persisted acceptance/dispatch barriers replayed the same unknown operation without another acceptance | Local filesystem; not a power-loss or network-volume durability simulation |
| Linux process cancellation | Disposable real process used; mismatched identity not signalled, owned process terminated, output files preserved | Does not prove CUDA child-process behavior |
| Security mutation checks | Tests failed when token verification, approval enforcement or no-clobber file creation were deliberately broken | Isolated temporary source copies; production source was not mutated |
| Dependency checks | `pip check` passed in host test venv and Linux test container | Web/MCP stack only; not the complete GPU dependency environment |
| Build configuration | `make build-check` passed for cu130 and cu128 without warnings; build-pin regression tests passed | Dockerfile validation, not a full image build or GPU smoke test |
| Compose | Standard, development and CPU configurations parsed with `config --quiet` | Syntax only, no service start |

Pinned tested web stack: `mcp` 2.3.0, `mcp-types` 2.3.0, FastAPI 0.139.0, Pydantic 2.13.4, HTTPX 0.28.1, HTTPX2 2.13.1. The MCP dependency uses HTTPX2 alongside Portal's HTTPX; this change does not upgrade torch/CUDA.

Official SDK release artifacts observed from PyPI:

- Wheel SHA-256: `dd0c44c089d16453e8ae31a3877a0054d7a2314caaa81f5e0541b9b1734b2377`.
- Source archive SHA-256: `8b147a50441cf059dc88c684e0aeed3687f0aa0f39c6cde7b90330effd2b34d8`.

The build pins the version; these recorded hashes are provenance, not an assertion that all transitive packages use hash-enforced installation. Sources: [PyPI release metadata](https://pypi.org/pypi/mcp/2.3.0/json), [official SDK](https://github.com/modelcontextprotocol/python-sdk).

## What the focused tests establish

Test names include catalog IDs, sometimes covering only part of a catalog row. The 37 methods do not constitute completion of all 106 design scenarios.

- **Access/protocol:** private tokens, expiry/renewal, revocation/rotation, no cookie/provider-token fallback, cross-client dataset/cursor isolation, owner password/CSRF checks, safe validation errors, corrupt policy/state fail-closed behavior, HTTP origin/host/body/JSON limits, current/legacy SDK paths and offline-owner-lock refusal.
- **Read/data boundary:** source hash/mode sentinels survive reads and operations; model inspection does not seed directories; reads never start the queue; paths, parent symlinks, hardlinks and FIFOs are refused; state permissions are enforced.
- **Approval/retries:** unapproved/foreign plans cannot create runs; policy limits are tested individually; grant changes invalidate pending and queued work; 20 concurrent identical training requests create one linked run; request/payload conflicts and consumed approvals are rejected; restart invalidates unused plans and clock regression fails closed.
- **Dispatch/files:** same-size/same-mtime source changes are detected; private copies never hardlink source; queued source/config/snapshot/record changes prevent launch; capacity and journal failures precede effects; destination collision preserves its old bytes; busy GPU checks leave work queued; cancel replay preserves files.
- **Comparison/export:** the real fixed graph builder drives a synthetic provider producing two images; a lost accepted reply records one POST and an unknown outcome; archive allowlists exclude private captions/paths; tensor bytes survive removal of trainer metadata; selected images lose metadata; stale checkpoints cannot export; foreign/range downloads are refused and revocation interrupts streaming.

Provider HTTP, actual model validity, real training quality and native kernels are not established by synthetic graph/checkpoint fixtures. The Linux process test proves signalling behavior for a disposable Python process only.

## Gates still open

1. Build both complete target CUDA images and resolve/check their full environments. Run GPU smoke tests, then a small explicitly funded synthetic SDXL training → comparison → export workflow, including cancellation/restart/revocation and dataset hash sentinels. Keep `MCP_GPU_VERIFIED=0` until this passes for the deployment.
2. Verify exclusive locks, atomic replacement, file/directory fsync, inode behavior, ownership and failure handling on the actual persistent volume, particularly RunPod network storage. Measure capacity independently of shared-filesystem totals. Keep `MCP_STORAGE_VERIFIED=0` until verified.
3. Validate current/legacy protocol errors and supported independent client versions through the real HTTPS reverse proxy. Check trusted forwarding, body limits, disconnects and long artifact streams. The local raw current-era request also exercised the SDK-required `params._meta` version/capabilities envelope; clients should use the SDK rather than hand-build envelopes.
4. Select a maintained OAuth authorization server and implement/test the planned issuer/audience/PKCE/resource metadata integration. No provider was selected during this implementation; OAuth capabilities are absent, not silently replaced with a universal bearer claim.
5. Add a reviewed owner maintenance/reconciliation workflow before relaxing conservative operation/journal/storage caps. Unknown outcomes currently require manual investigation and never automatically retry. Archive expiry blocks access but does not remove files; reservations and replay tombstones persist.
6. Model installs, training recovery, extra families, stdio, log/preview resources and additional remote-client integrations remain later scope. Their tools are absent.

No live workspace data, real cloud tokens or production GPU jobs were used. Existing Services UI changes in the working tree were preserved. Git publication is separate from these checks.

## Reproduce

Use a disposable workspace and an environment with the pinned Portal/MCP dependencies:

```bash
python -m unittest discover -s tests -p 'test_mcp_*.py' -v
python -m unittest discover -s tests
make build-check
make build-check CUDA_PROFILE=cu128
```

Tests construct temporary roots internally. Do not point a test harness at an existing user workspace. Existing suite warnings about Pydantic v1 validators and FastAPI lifecycle decorators are unrelated to MCP behavior; both focused and full runs completed successfully.

## Security follow-up: 2026-10-05

The follow-up to `0b87564` patches three availability findings in the shared ledger, artifact transport and run resource handler. The earlier fingerprint and Linux evidence above describe the original implementation, not this patch.

- Owner controls and recovery transactions have a 64 KiB reserve above the existing 8 MiB work limit. Audit pressure can remove the oldest entries while retaining the newest; operation tombstones remain intact. Already-full ledgers can initialize, reconcile and disable, and unchanged retries do not require another write.
- Artifact downloads allow two streams globally and one per connection identity, including across token rotation. Blocked header, body and completion sends time out after 30 seconds. Timeouts, disconnects and cancellation release capacity and close the open archive; error responses release capacity before sending. Ordinary downloads and revocation checks remain available.
- Run resource reads use the same four-worker limiter and cancellation wrapper as tools, with a 256 KiB response cap. A blocked filesystem read leaves Portal HTTP handling responsive. Unauthorized, malformed and oversized resources retain safe errors.

Changed runtime files: `apps/Portal/mcp_server/{store,server,operations}.py`. Added `tests/test_mcp_security_regressions.py`; updated the connection guide's limits. The shared boundaries preserve authorization, one-time approvals, replay identities and user files.

Validation ran on macOS with Python 3.12.11 and `mcp==2.3.0`, using temporary workspaces, synthetic exports and in-process ASGI clients. The full suite's Comfy tests additionally used disposable loopback servers.

| Gate | Command/check | Result |
|---|---|---|
| Syntax/imports | AST parse of MCP modules and new tests; import `store`, `server`, `operations`; `git diff --check` | Passed |
| Focused security cases | `python -m unittest discover -s tests -p 'test_mcp_security_regressions.py' -v` | 9 passed; reduced ledger caps and short send deadlines exercise the production boundaries without exhausting storage or using live services |
| Existing behavior | `python -m unittest discover -s tests` | 374 passed, including all 46 MCP tests; zero skips |
| Dependency consistency | `uv --no-cache pip check --python <test-venv>/bin/python` | Passed, 49 installed packages compatible |
| Independent patch review | Read-only caller/lifecycle review and a bounded stalled-error-response check | No remaining findings after releasing download capacity before error responses |
| Optional build configuration | `make build-check` | Unavailable: local Docker daemon stopped; no image/build configuration changed |

Initial full-suite attempts identified missing disposable-environment dependencies and sandbox restrictions on loopback sockets. After installing the required dependencies and allowing the local test sockets, the complete suite passed. The security tests establish recovery at the work cap, intact replay records, released download slots/descriptors, fair access for another connection and responsive resource dispatch. They do not establish target-volume durability, deployed proxy behavior, GPU execution or external-client compatibility; the release gates above remain open.


## Setup follow-up: 2026-10-06

The setup changes in `1e91754` and `d0b2352`, plus the plaintext-setup guard, replace the manual public-URL prerequisite with trusted RunPod discovery or an owner-confirmed saved HTTPS origin. The UI provides inline password setup, atomic connection creation/enablement, private copy instructions and four read-only examples. The earlier fingerprint describes the original implementation, not this follow-up.

Validation used disposable local workspaces and synthetic credentials; it did not create a connection to user data or enable GPU writes:

- All 408 Python tests passed, including 53 MCP tests. Seven new setup cases cover owner/password/CSRF checks, missing-password disclosure limits, invalid configuration, forged origins and forwarding headers, URL persistence and permissions, RunPod proxy handling, and an official SDK client connecting after setup without a server restart.
- All 61 JavaScript tests passed. Six new MCP UI tests exercise explicit data selection, default read scopes, password confirmation, atomic enablement, safe preview versus credential copying, retry after rejection, duplicate submission, late responses, tab cleanup, clipboard fallback and refusal to request passwords over public plaintext HTTP. Existing Settings fixture selectors were updated to include the MCP controls.
- The rendered Settings view and real MCP backend were exercised in a local browser with synthetic owner authentication: create a scoped connection, rotate its token, copy the credential-bearing instructions, and inspect the masked preview. Mobile inspection at 390 × 844 showed no horizontal overflow; no browser console warnings/errors were reported. The inline password path is covered by UI regression tests, not a change to a live owner's password.

The custom-proxy, independent-client, persistent-volume and GPU release gates above remain separate from these checks. Normal setup leaves execution flags off.
