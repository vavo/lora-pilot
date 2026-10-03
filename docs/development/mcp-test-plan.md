# LoRA Pilot MCP test plan

Date: 2026-10-03  
Status: proposed tests, not implemented or executed MCP coverage.  
Design: [MCP implementation plan](mcp-implementation-plan.md).

## 1. What the tests must prove

The primary oracle is observable behavior: which process launched, which bytes changed, which client received which data, and which durable record survived a crash. A response code, an SDK handshake or a matching function name is not enough.

Release-blocking invariants:

1. An unauthorized request causes no workspace effect and reveals no protected object data.
2. An accepted request ID creates at most one backend operation, including after lost replies and process restarts.
3. Original datasets, models, completed checkpoints and unrelated outputs remain unchanged by MCP execution.
4. No read-only tool initializes a worker, publishes files, downloads a model or changes queue state.
5. Revocation/expiry prevents newly authorized work and queued dispatch; it cannot silently discard completed files.
6. A changed plan, ambiguous side effect, incomplete scan or unavailable capacity cannot silently authorize a write.
7. Artifacts/logs expose only granted content. Server credentials never enter protocol output or downloadable packages.
8. Disconnects, cancellation and rollback leave an explainable, recoverable operation state.

P0 means required before enabling the affected capability. P1 means required before its supported production release. “Later” cases are still P0 for their optional capability; skipping that capability is acceptable, shipping it without the gate is not.

## 2. Fixtures and test layers

### 2.1 Shared fixtures

- `WorkspaceSentinel`: temporary source datasets, existing models/library files, completed run history and unrelated outputs, plus canary files outside the workspace. Record content digest, size, permissions, ownership where supported and link relationships. Check all protected files after success and failure. Exclude expected audit/journal writes and unavoidable directory timestamp updates from the oracle; do not exclude source-file changes.
- `CanarySecrets`: distinct fake HF, OAuth, private-client, Jupyter and Copilot tokens; cookie values; URL credentials; private captions and absolute paths. Inspect structured/text MCP output, HTTP headers, SSE events, captured logs, owner UI and archive entries. Never use actual user secrets.
- `TwoPrincipals`: A can inspect dataset A and run A, B can inspect dataset B and run B; include an administrator-only run. Use both private credentials and OAuth fixtures. Rotate credentials without changing principal identity.
- `BarrierRunner`: a small real subprocess that records launches to an append-only test file, emits bounded progress, writes a disposable checkpoint and handles TERM. It receives no network access or real dataset paths. Use it to prove launch counts and process ownership.
- `FakeComfy` / `FakeModelProvider`: local HTTP fixtures supporting slow replies, response loss after acceptance, redirects, throttling, malformed JSON, binary data and partial downloads. Use approved test-only loopback destinations through dependency injection, not a production SSRF bypass flag.
- `CrashHarness`: run Portal in a child process with deterministic barriers at journal/run-file/subprocess boundaries. Kill that child, restart on the same temporary volume and replay the same request. Synchronize with events/pipes; avoid sleep-based race tests.
- `Clock`: injected wall/monotonic clocks for plan/token expiry and quotas. Exercise clock jumps separately from ordinary expiry tests.
- `FilesystemFaults`: controlled ENOSPC/EIO/EACCES, interrupted writes, symlink/hardlink swaps and destination creation. Run race tests against actual descriptor-based file operations; mock only fault boundaries.

Default tests must never start actual trainers, change `/workspace`, call real providers, signal unrelated PIDs or use the developer's saved credentials. Reject a test root that is not a newly created disposable directory. Restore environment patches and release locks/threads/clients after every test.

### 2.2 Layers

| Layer | Exercise | Mock boundary / required evidence |
|---|---|---|
| Contract/unit | Input validation, scope/object policy, output schemas, journal transitions | Pure fixtures; table-driven boundary cases with side-effect spies |
| In-process integration | MCP SDK -> authorization -> facade -> real shared service -> temporary files | Mock GPU/provider boundary only; no test-only route bypass |
| Subprocess/protocol | Actual HTTP/stdio framing, lifecycle, deadlines, crashes, signals | Real Portal process and SDK client; fake provider/runner |
| Linux/container | UID/mode behavior, descriptor/no-follow semantics, volume locks, image dependencies | Built image, disposable local volume and actual supported network-volume type |
| Browser/client | Owner approval/CSRF/rendering plus client discovery/auth/tool use | Real browser and at least two independent supported MCP clients |
| GPU/deployment | Dataset -> training -> comparison -> export, through real proxy/auth | Small explicitly funded disposable run; capture actual output checks |

## 3. Protocol and lifecycle tests (P)

| ID | Priority | Stimulus | Required oracle |
|---|---|---|---|
| P01 | P0 | Start image with MCP disabled; request `/mcp`, `/mcp/` and artifact paths | Explicit disabled/not-found behavior; no static HTML masquerading as MCP, metadata/data leak or worker creation |
| P02 | P0 | Current-revision SDK discovery/call/read and supported legacy initialization flow | Valid structured results using the chosen SDK's framing; no application dependence on legacy session identity |
| P03 | P0 | Unknown protocol revision; mismatched current-era body/header method/name/version metadata | Defined protocol error before policy/backend dispatch; no silent downgrade or effects |
| P04 | P0 | Malformed JSON, invalid UTF-8, arrays/batches, nested excess depth, duplicate security-relevant fields, unsupported content type | Deterministic rejection within configured resource limits; no partial dispatch; ambiguity never changes the authorized action |
| P05 | P0 | Extra write fields such as `path`, `toml_path`, `_template`, `url`, `command`, `env`, `confirmed`, or non-finite numeric values | Strict schema failure; none reaches a backend function |
| P06 | P0 | Request limits at N-1, N, N+1 with fixed-length and chunked bodies; compressed body | Enforced limits without unbounded buffering; oversized request produces zero effects; compression refused |
| P07 | P1 | Block a provider/hash scan while querying health and unrelated status | Portal remains responsive; executor/concurrency limits hold; slow operation does not retain the global queue lock |
| P08 | P0 | Mount/unmount/start/stop MCP alongside existing startup hooks | Exactly one telemetry/training owner; startup failure leaves MCP closed and existing Portal status explainable |
| P09 | P0 | Cancel an HTTP/SSE request during inspection, during acceptance, and after accepted submission | Inspection halts; acceptance either never occurs or returns the durable operation on retry; accepted training is not silently killed |
| P10 | P1 | Read pagination while records change; malformed/tampered cursor; another principal's cursor | Stable documented paging or explicit stale cursor; no duplicates caused by broken cursor ordering, unauthorized counts or unbounded result |
| P11 | P0 | Legacy session identifier reused with another credential; resource handle replay across clients | Authentication/grants checked independently; session/state handle grants no authority |
| P12 | P1, bridge | Stdout contamination, missing token file, symlink token file, arbitrary destination, parent env full of fake keys | Bridge fails safely; protocol stdout remains clean; only required env/credentials forwarded to fixed endpoint |

## 4. Authentication, object grants and owner approval (A)

| ID | Priority | Stimulus | Required oracle |
|---|---|---|---|
| A01 | P0 | Missing, malformed, expired, revoked, wrong-purpose bearer; valid Portal cookie or Comfy/HF token only | No MCP operation or data; generic failure; backend call count zero |
| A02 | P0 | Toggle Portal password on/off while MCP is configured; access direct backend/proxy paths | MCP never falls back to anonymous authentication; unsafe public configuration disables remote enablement or requires verified perimeter |
| A03 | P0 | Read-only credential attempts every mutation, including guessed tool names and direct artifact/admin routes | Denied by execution policy, not just tool discovery; original bytes and launch counts unchanged |
| A04 | P0 | A guesses B's dataset/run/artifact/operation IDs in lists, reads, errors, logs, completions and resource templates | No existence/count/name/size/timing detail beyond documented generic denial; no result replay across principals |
| A05 | P0 | Revoke/shrink a grant with a cached tool list and open HTTP connection | Next call denied; stale resources and existing plan IDs do not preserve access |
| A06 | P0 | Approve plan for A, execute as B; edit family/prompt/checkpoint/limits; change workspace/grant version | Denied/stale; approval remains unusable for substituted action |
| A07 | P0 | Plan expires; clock moves forward/backward; server restarts | Conservative expiry; expired approval never becomes valid after clock rollback; restart invalidates uncertain pending approvals |
| A08 | P0 | Client supplies `confirmed:true`, approval token copied from a tool result, or forged human text | None substitutes for persisted owner approval or pre-authorized policy |
| A09 | P0 | Owner mutation without CSRF token, with mismatched/`null` Origin, hostile Host, stale session or no recent reauthentication | No grant/credential expansion; clear owner-facing error; existing credentials preserved |
| A10 | P0 | Simultaneous approve/revoke/execute; revocation at queued-to-launch barrier | One linearized outcome; revocation effective before dispatch blocks launch, effective after launch follows documented running-job policy |
| A11 | P0 | Automated policy at/below/above dataset, steps, time, bytes, job-count or expiry limit | Within-limit action proceeds once; above-limit action needs approval or fails; fresh request ID cannot evade quota |
| A12 | P1 | Rotate token and replay accepted request; retry with old token | New token sees same principal/operation; old token rejected; no duplicated run |
| A13 | P0 | Unknown/malformed/missing/corrupt grant file; simulated read error | Fail closed; no recreation of permissive defaults or reset to empty auth |
| A14 | P1 | XSS/HTML/URL payloads in client labels, prompts, filenames and plan review fields; inspect grant disclosures | Owner UI renders inert text; no external navigation/fetch, credential leakage or approval triggered by content; read grants explain client disclosure and revocation limits |

## 5. Remote OAuth and network boundary (O)

| ID | Priority | Stimulus | Required oracle |
|---|---|---|---|
| O01 | P0, remote | Real selected issuer/client discovery, login, consent, PKCE, resource/audience and tool call | Protected-resource metadata and challenges work through public URL; exact tested client/provider versions recorded |
| O02 | P0, remote | Wrong issuer/audience/algorithm, bad signature, missing expiry, future `nbf`, expired token, ID token instead of access token | Rejected before backend/object lookup; no algorithm fallback or acceptance as private token |
| O03 | P0, remote | Valid issuer token for unmapped subject/client or missing scope | No implicit local grant; denial and correct scope challenge where applicable |
| O04 | P0, remote | Key rotation, stale cache, unavailable JWKS, unknown key flood | Bounded refresh; valid cached keys only within policy; new unverifiable tokens denied; no fetch storm |
| O05 | P0, remote | Token header/discovery metadata tries arbitrary `jku`/issuer/JWKS URL or redirects to private/link-local host | No unconfigured outbound access; fake metadata service records zero requests |
| O06 | P0 | Token in URL, query, Referer, RPC argument, error message or redirected outbound request | Not accepted as authentication and not emitted to logs/upstreams; redirect cannot carry Authorization to another origin |
| O07 | P0 | Host poisoning, mixed case/port lookalikes, suffix-matched Origin, `Origin:null`, DNS rebinding | Exact configured boundary enforced; permitted proxy Host works; hostile value rejected |
| O08 | P0 | Spoofed forwarded IP/scheme from direct client versus trusted reverse proxy | Only configured proxy metadata affects canonical handling/rate limits; metadata URLs do not derive from untrusted headers |
| O09 | P1 | Broad Portal CORS preflight applied to `/mcp` and `/mcp-artifacts`; originless native client | MCP-specific CORS survives mount/middleware order; originless authenticated request works; unapproved browser Origin fails |
| O10 | P0, remote | Revoke local grant while OAuth token remains cryptographically valid; provider-side revoke without introspection | Local revocation immediate; provider revocation behavior matches documented maximum access-token lifetime, not an invented instant guarantee |

## 6. Writes, idempotency and crash recovery (W)

Run W01–W09 for training, comparison, export and later installation, using each backend's real acceptance adapter.

| ID | Priority | Stimulus | Required oracle |
|---|---|---|---|
| W01 | P0 | Same request ID/payload sent sequentially and from 20 synchronized clients | One operation/backend ID and at most one actual launch; all authorized retries observe that operation |
| W02 | P0 | Same request ID with altered payload, defaults, ordering or tool name | Semantically identical canonical payload replays; changed effect produces conflict; no silent field coercion |
| W03 | P0 | Lose client reply after acceptance or upstream reply after provider accepts | Retry recovers accepted operation or unknown outcome; no fresh provider request |
| W04 | P0 | Kill before/after acceptance journal fsync, approval reservation, backend ID reservation, run record, dispatch marker, subprocess launch, result persistence | Each crash yields zero or one effect, existing original data, valid linkage or explicit quarantine/unknown; never inferred safe replay |
| W05 | P0 | Crash with temporary record, truncated JSON, dangling backend ID or run record without accepted journal | No dispatch of partial record; owner-visible reconciliation state; no deletion/replacement of unrelated directories |
| W06 | P0 | Restart then replay before worker recovery completes; two Portal owners race | One owner; replay waits/fails retryably; neither owner dispatches the same operation twice |
| W07 | P0 | One-time approval used with two different request IDs concurrently | At most one accepted action; reservation survives crash and cannot be double-consumed |
| W08 | P0 | Another request ID targets resource with unresolved unknown comparison/install | Conflict/owner review; request ID changes cannot bypass uncertainty |
| W09 | P0 | Idempotency journal at capacity; old completed request replayed after log/archive retention | New mutations rejected without evicting tombstones; old replay never becomes a new write |
| W10 | P0 | Fault writing audit/operation acceptance or returning permission check result | No side effect without persisted acceptance; failure response reveals no secret; read status remains available where safe |
| W11 | P1 | Queue/GPU/operation/download locks contended in UI, MCP, worker and revoke threads | No deadlock under bounded deterministic stress; documented lock order exercised |
| W12 | P0 | Disable MCP immediately before/after acceptance and dispatch | No new MCP work after disable point; accepted/running behavior matches policy; existing UI work remains intact |

## 7. Filesystem integrity, snapshots and capacity (F)

| ID | Priority | Stimulus | Required oracle |
|---|---|---|---|
| F01 | P0 | Absolute/traversal paths, URL/double encoding, Windows separators/drives, NUL, Unicode lookalikes in handles/filenames | Invalid handle/input denied; no resolution outside authorized objects and no external reads/writes |
| F02 | P0 | Symlink in each parent component, final symlink, hardlinked snapshot source/destination, FIFO/socket/device, deleted source | File access refuses unsafe type/path; process does not block on FIFO; external sentinel unchanged |
| F03 | P0 | Swap parent directory/final file between validation and open/copy/promote using a barrier | Descriptor/no-follow logic protects outside data; operation fails/conflicts; no clobber |
| F04 | P0 | Change dataset caption/image after review, preserving size and mtime; add/remove a member | Content/tree digest changes; plan invalidated; trainer launch count zero |
| F05 | P0 | Rewrite source during snapshot copy, including modification of a file already copied | Final snapshot matches approved manifest or operation aborts; never train a mixed unapproved snapshot |
| F06 | P0 | Fixture trainer writes caches/captions or modifies its input image | Only private snapshot changes; original dataset digest, mode and link identity remain intact |
| F07 | P0 | Destination file created or replaced during checkpoint publish/download promotion | Existing destination survives byte-for-byte; conflict or verified reuse; no overwrite flag |
| F08 | P0 | ENOSPC/EIO/EACCES at staging write, fsync, rename, archive finish and journal update | Protected sources remain unchanged; terminal/unknown state correct; cleanup affects only owned temp files |
| F09 | P0 | Unknown quota, misleading host disk total, concurrent UI/external consumption, reservation race | Allocation blocked or constrained conservatively; reserve counted once; runtime guard reports failure without deleting source data |
| F10 | P1 | Excess files, deeply nested directories, oversized image/decompression bomb and huge captions | Work bounded; explicit incomplete/too-large result; no clean review/approval from a partial scan |
| F11 | P0 | Existing symlink at journal/cache root; permissions too broad; newer unsupported schema | MCP writes disabled; no following link, chmod of unrelated paths or reset/reinitialization |
| F12 | P1 | Fresh and existing workspace bootstrap twice, then image upgrade/downgrade | Existing datasets, settings, credentials and journals preserved; no bundled example credential seeded |
| F13 | P0, deployment | Lock/rename/fsync/crash tests on supported persistent/network volume | Demonstrated single-owner/durable behavior; unsupported volume keeps mutations disabled |

## 8. Training, queue and recovery (Q/U)

| ID | Priority | Stimulus | Required oracle |
|---|---|---|---|
| Q01 | P0 | List/discover/read on cold workspace and on paused queue with queued run | No worker initialized, queue unpaused, snapshot created or subprocess launched |
| Q02 | P0 | Submit approved run while GPU busy, another UI run queued, legacy training active or queue full | Existing conflict/order policy preserved; precise accepted-but-waiting versus rejected state; no parallel trainer |
| Q03 | P0 | Dataset/model/template changes after plan or while queued | Dispatch-time verification rejects stale authorization; no trainer starts with altered inputs |
| Q04 | P0 | User-edited TOML includes external output paths, custom imports/optimizer, resume file or hooks | Unapproved recipe rejected even if the REST UI can use it; no arbitrary config forwarded |
| Q05 | P0 | Cancel queued/running/finished run, cancel twice, cancel foreign run, cancel after PID reuse | Only owned/granted managed run affected; no arbitrary signals; terminal cancellation idempotent; all outputs retained |
| Q06 | P0 | Revoke/expire grant while queued, while hashing, and while trainer running | Queued/new work blocked; running behavior explicit; no silent loss of checkpoint; owner can still inspect/cancel |
| Q07 | P0 | Run exceeds step/wall-time bound; watchdog fails to signal or process group changes | Stop only verified owned group; report inability/unknown; never signal replacement PID; preserve partial outputs |
| Q08 | P0 | Restart with active trainer/orphan plus pending MCP/UI runs | Interrupted status and paused dispatch retained; no global unpause by MCP; no duplicate launch |
| Q09 | P1 | Invalid/missing GPU telemetry and intermittent provider probes | No invented capacity; conservative conflict state; no automatic service stop to “make room” |
| U01 | P0, later | Resume with changed dataset, wrong-family/foreign run, incomplete checkpoint or active continuation | Rejected with no new run, or documented conflict; ownership/grants enforced |
| U02 | P0, later | Saved state contains symlink or replaced optimizer pickle; imported run record claims trusted origin | Provenance/content verification rejects it; no untrusted deserialization |
| U03 | P0, later | Resume valid managed safetensors versus trusted full state | New linked run; original run/state unchanged; weights-only schedule reset explicitly represented; same request replay does not create another continuation |

## 9. Comparison and export (C/E)

| ID | Priority | Stimulus | Required oracle |
|---|---|---|---|
| C01 | P0 | Comparison plan on valid checkpoint, then abort | No library copy, workflow file, provider queue entry or output mutation |
| C02 | P0 | Inject arbitrary node class, graph, URL, path, huge dimensions/steps or excess checkpoints | Input/recipe validation rejects before Comfy receives a prompt |
| C03 | P0 | Existing library copy differs from selected checkpoint | Existing bytes preserved; conflict surfaced; no move/delete/replacement |
| C04 | P0 | FakeComfy accepts prompt then drops reply; later queue/history missing or inconsistent | Persist unknown/unavailable; no automatic retry/reset; clear owner reconciliation action |
| C05 | P0 | Parallel UI/MCP training and comparison launches | Shared GPU guard serializes decisions; no conflicting managed workload starts |
| C06 | P1 | Prompt injection in image metadata/history or provider error | Returned as sanitized data only; no extra tool call, follow-up URL fetch or credential leak |
| E01 | P0 | Export default package with fake secrets/paths/captions in every available source; inspect checkpoint approval | ZIP contains only approved checkpoint, safe metadata and selected images; no dataset, logs, keys or optimizer files; approval discloses trained-model privacy limits without claiming anonymization |
| E02 | P0 | Replace checkpoint/image after preview with same-size/same-mtime contents; switch image to another run | Digest/object binding rejects before archive publication; no unintended bytes returned |
| E03 | P0 | Invalid image indices, duplicates, negative indices, altered manifest/approval, raw config injection | Deterministic validation; no substituted artifact; selected image order stable |
| E04 | P0 | Image has EXIF/text chunks/private metadata; image decompression bomb | Allowed pixels only, metadata absent; oversized image rejected within memory bound |
| E05 | P0 | Foreign/expired artifact ID; revoked grant during stream; malformed/multiple Range headers | No unauthorized bytes; ongoing stream observes bounded revocation policy; range cannot amplify resource use |
| E06 | P0 | Client cannot authenticate resource-link download | Documented human Portal link/failure; no public URL fallback or token in query |
| E07 | P0 | Export quota reached, construction interrupted or archive cache cleanup races active download | Source checkpoint survives; no partial archive exposed; active stream retained or cancelled cleanly under policy |
| E08 | P1 | Inspect generated download headers and proxy/CDN behavior | No-store, attachment, nosniff and authorization survive forwarding; no cross-principal cache replay |

## 10. Optional model installation (M)

| ID | Priority | Stimulus | Required oracle |
|---|---|---|---|
| M01 | P0, later | Unknown catalog ID, workspace manifest override, arbitrary repo/URL/revision/destination | No provider request or filesystem mutation without owner-approved catalog identity |
| M02 | P0, later | Provider redirects to another origin/private IP/metadata host or changes DNS mid-flow | No credential forwarding or prohibited fetch; fixture records exact permitted requests |
| M03 | P0, later | Interrupted/partial download, wrong size/digest, gated model/license denied, 429 or unavailable provider | Existing models preserved; bounded retries where proven safe; no false installed state |
| M04 | P0, later | Two clients plus UI request the same destination; destination appears during download | One coordinated writer or conflict; operation ownership correct; no replacement of newly created file |
| M05 | P0, later | Portal restarts while download process survives; job metadata disappears | Unknown/reconciliation state; no second downloader or trusting incomplete file |
| M06 | P0, later | Enough space at plan but not staging/promotion; reserve contested by another operation | Respect reservations and fail without deletion; temporary files retained/cleaned only by verified ownership |

## 11. Redaction, abuse and operational recovery (R/D)

| ID | Priority | Stimulus | Required oracle |
|---|---|---|---|
| R01 | P0 | Provider exception/logs contain each secret canary, auth header, URL password and absolute config path | Sensitive values absent across JSON/text/SSE/stdio/server logs and UI; structured safe error remains useful |
| R02 | P0 | Filename/caption/log says “ignore previous instructions,” requests secret files or includes a forged tool call | Fixed tool policy unchanged; owner approval UI inert; no parser treats content as authority |
| R03 | P0 | `runs:read` without `runs:logs`/`artifacts:read`; artifact preview without grant | No raw log/config/image bytes; discovery and direct reads agree |
| R04 | P1 | Read flood, auth-failure flood with many IPs/IDs, repeated costly scans and oversized responses | Bounded memory/maps/workers; explicit throttling/truncation; Portal still answers health/status |
| R05 | P0 | Full/corrupt audit journal and clock discontinuity | New mutations fail closed; no secret-bearing fallback logs; status/owner repair path remains usable |
| D01 | P0 | New SDK dependency installed under both CUDA build profiles | Constraints resolve, image import/start succeeds, `pip check` and existing build-pin tests pass; no hidden training-stack upgrade |
| D02 | P0, remote | Real HTTPS proxy with path routing, timeout, buffering, redirect and Origin handling | SDK roundtrip and status polling work; no credential downgrade/redirect or loss of security headers |
| D03 | P0 | Two real clients: discover, grant, plan, approve, execute, reconnect, revoke | Expected workflow completes once; incompatible features documented by client/version, not labelled generically supported |
| D04 | P0, GPU | Synthetic SDXL quick test -> checkpoint comparison -> export | Actual valid checkpoint and baseline/trained images; archive manifest/contents verified; original dataset hashes unchanged |
| D05 | P0, GPU | Cancel actual short run; disconnect client; restart Portal during disposable run | Documented checkpoints/recovery/queue pause; no unrelated process stopped; no automatic duplicate run |
| D06 | P0 | Disable feature and roll back image with queued/running/unknown/export states | REST UI remains usable; artifacts preserved; unsupported journal disables writes; no replay after rollback |
| D07 | P1 | Restore an older backup containing previously valid credentials/grants | Restore disables MCP dispatch and rotates/revokes credentials; old tokens cannot regain access; lost-journal effects require owner reconciliation, not automatic replay |
| D08 | P0, deployment | Attempt direct access to Portal, sidecar, Comfy and other exposed ports outside approved perimeter | Record actual exposure; remote release blocked if an unauthenticated control path bypasses the intended protection |

## 12. Crash matrix and state oracles

For W04, record these boundaries for each backend in the implementation PR. A test must terminate the real process at the boundary, not merely raise an exception caught by the handler.

| Boundary | Expected restart outcome |
|---|---|
| Before acceptance is durable | No accepted operation/effect; original request may be accepted once after retry |
| Acceptance durable, approval reservation incomplete | Recover reservation for that operation or block unknown; no competing consumption |
| Backend ID reserved, no backend object yet | Reconcile the same ID; create once only if absence is provable and no external dispatch occurred |
| Private directories created, run record incomplete | Quarantine/block; no worker sees it as executable and no broad cleanup |
| Linked run record durable, client never receives it | Replay returns the same run; no new queue record |
| Dispatch marker durable, launch uncertain | Unknown/interrupted; inspect verified process identity; no automatic relaunch |
| Provider accepted, response lost | Unknown until trustworthy reconciliation; no blind second submission |
| Backend terminal, journal update missing | Reconcile terminal evidence to same operation; no repeat work |
| Export verified but response lost | Return same archive identity if retained; expiry returns explicit unavailable, never unrelated bytes |

For a genuinely unsent external request, only the same recorded dispatch attempt may proceed under a documented proof of absence. Timeouts and lack of a response are not that proof. Training's reserved run ID allows stronger local reconciliation than an upstream provider without idempotency support.

## 13. Test implementation and execution

Suggested suites: `test_mcp_protocol.py`, `test_mcp_auth.py`, `test_mcp_policy.py`, `test_mcp_operations.py`, `test_mcp_files.py`, `test_mcp_training.py`, `test_mcp_results.py`, `test_mcp_oauth.py`, and later `test_mcp_installs.py` / `test_mcp_bridge.py`. Split only when a suite becomes hard to navigate; IDs above should appear in test names/comments or the release evidence table.

Reuse existing training/storage/export fixtures and run relevant existing suites after shared-service changes: `test_portal_api_contracts.py`, `test_training_runs.py`, `test_guided_training.py`, `test_training_comparison_api.py`, `test_experiment_export.py`, `test_storage.py`, `test_models_api.py`, `test_model_install.py`, `test_tagpilot_dataset_api.py`, `test_comfy_access.py` and `test_bootstrap_contracts.py`.

Proposed commands once the tests and SDK dependency exist:

```bash
# Use the project's test environment, with runtime roots redirected to fixtures.
python3 -m unittest discover -s tests -p 'test_mcp_*.py'
python3 -m unittest discover -s tests
make build-check
```

Subprocess/crash, container, client and GPU checks need separate opt-in harnesses. They must accept an explicitly created disposable workspace and print the effective target before running. Production paths, real tokens and a default unrestricted network are prohibited in the harness.

Use generated cases for identifier parsing, scope/object combinations and plan canonicalization. Seed and persist a minimal failing example; a fuzz run with no oracle is not meaningful coverage. Use barriers to reproduce races. Repeat stress tests only for new concurrency changes or an unresolved race, not to inflate a passing test count.

Verify test strength with selected mutation checks: remove a scope check, remove the accepted-record write, use a fresh backend ID on retry, replace no-clobber with overwrite, bypass digest verification, or serialize a raw provider exception. The corresponding test must fail on a prohibited effect/disclosure. Do this in disposable test copies; never leave mutation changes in the implementation.

## 14. Release acceptance record

The implementation release report must contain:

- Exact code/image revision, SDK/protocol versions, supported clients and auth provider configuration class (no secrets).
- Test IDs executed, pass/fail/skip reason, and a mapping from each advertised capability to its P0 gate. Skipped required tests block that capability.
- Protected-file sentinel results; crash-boundary launch counts and reconciled operation IDs; cross-client data isolation results.
- Built-container/volume type evidence separately from local macOS/Python tests. A local `O_NOFOLLOW` test does not certify the target network volume.
- Real reverse-proxy/OAuth evidence separately from mocked discovery/JWKS checks.
- Real GPU run/checkpoint/comparison/export evidence separately from the barrier-runner tests.
- Rollback/revocation drill results, remaining limitations, any deferred tool, and the operator steps for unknown outcomes.

This planning task validates the design against source and protocol documentation only. It does not certify future MCP code, provider authentication, container deployment or GPU execution. Complete the applicable gates before enabling writes for users.
