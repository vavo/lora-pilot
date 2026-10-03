# Connect an assistant with MCP

_Source implementation: 2026-10-03; not a published-image or live GPU certification._

LoRA Pilot provides Streamable HTTP at `/mcp`, using the official Python SDK `mcp==2.3.0`. It starts disabled. Each connection has its own expiring bearer token, permissions, and selected datasets/runs. A ControlPilot browser cookie, Comfy token or Hugging Face token cannot authenticate MCP.

This version supports private clients that can send an `Authorization: Bearer …` header. OAuth discovery/login, a stdio bridge, model installation, recovery, shell access and deletion tools are not implemented. Do not configure an OAuth-only connector against this endpoint. See [validation and remaining release gates](../development/mcp-validation.md).

## Enable read access

1. Use an image built from source containing this implementation. A mutable `latest` tag does not establish that it includes MCP.
2. Set `MCP_PUBLIC_URL` to the exact HTTPS origin used by both the client and Settings, such as `https://pilot.example.com`. Omit `/mcp`, query strings and credentials. Loopback development can use `http://127.0.0.1:7878`.
3. Apply the container environment change. Keep the execution variables below at `0` for read-only use.
4. Set a ControlPilot password, log in, then open **Settings → MCP**. Enter the current password, select **Enable MCP**, and click **Apply**.
5. Name a connection and select only the permissions and objects it needs. Enter the current password again and click **Create connection**. Copy the token immediately into the client's protected credential/header configuration. It is shown once.
6. Configure the client with transport **Streamable HTTP**, URL `https://pilot.example.com/mcp`, and that bearer header. Use its SDK for protocol initialization/version negotiation. List tools and call `workspace_status` first.

Do not put the token in a URL, prompt, committed configuration, browser local storage or shared log. The Settings page clears displayed credentials after a change or navigation. Read permission authorizes disclosure to the connected client; revocation cannot erase data it already received.

The HTTPS proxy must preserve the configured Host and Authorization header, forward the original scheme, and serve MCP without redirects. Uvicorn must trust only the actual proxy peer via `FORWARDED_ALLOW_IPS`; never use `*` on a publicly reachable backend. Pass that variable explicitly through your deployment override when needed. Requests seen as HTTP against an HTTPS configuration are refused. This implementation has not yet been tested through a real public proxy.

One configured origin is accepted. Browser `Origin: null` and foreign origins are refused; authenticated clients without Origin are supported. MCP has its own boundary and does not inherit Portal's wildcard CORS. Protect other exposed service ports separately.

## Choose permissions

| Scope | Available access |
|---|---|
| `workspace:read` | MCP/queue state and the MCP guide; GPU availability is currently unknown (`null`) |
| `datasets:inspect` | Names/opaque handles of selected datasets, bounded image/caption quality counts; no file contents |
| `models:read` | Bundled catalog identifiers, installed status and size; no downloads or filesystem paths |
| `runs:read` | Selected run summaries and checkpoint handles; no raw configuration, logs or image previews |
| `operations:read` | Operations created by this connection, including retry/unknown status |
| `training:submit` | Approved SDXL quick-test plans; requires all five read scopes above |
| `training:cancel` | Cancel selected managed runs; requires `runs:read` and `operations:read` |
| `comparison:submit` | Approved fixed baseline/LoRA comparison; requires `runs:read`, `models:read`, `operations:read` |
| `artifacts:export` | Create an approved private archive; requires `runs:read`, `operations:read` |
| `artifacts:read` | Download its own created artifacts for currently granted runs; also requires `operations:read` |

The last five scopes appear only when execution gates are enabled. Existing runs and datasets are explicitly selected; future datasets are not automatically shared. A newly created MCP training run is added to its creator's run grant. Grants are authorization to named workspace objects, not a multi-user filesystem sandbox.

**Edit grants** preserves the connection identity/token, renews its expiry, and invalidates outstanding plans and queued authorization. Unchanged dataset selections keep their handles. **Rotate token** invalidates the old token while preserving grants and operation identity. **Revoke** is permanent for that connection. Expiry is 1–30 days; an expired connection can be renewed by editing, but a revoked connection cannot.

Every Settings mutation requires the current owner password, session, same origin and CSRF token. Removing the ControlPilot password is blocked while MCP is enabled. The offline bootstrap below is the trusted administrator alternative.

## Tools and operation flow

Read tools: `workspace_status`, `datasets_list`, `dataset_review`, `models_list`, `runs_list`, `run_get`, `operation_get`. Lists support `limit` (1–100) and opaque `cursor`. Cursors become invalid after relevant grants or list contents change. Resources include `lorapilot://docs/mcp` and authorized `lorapilot://runs/{run_id}/summary` reads.

When execution is enabled:

1. Call `training_plan`, `comparison_plan` or `export_plan` with the returned dataset/run/checkpoint handles. A plan records content hashes and a ten-minute expiry.
2. In **Settings → MCP → Pending approvals**, the owner reviews the selected data, cost bounds and export disclosure, then approves or rejects with their password. Use **Refresh** to see new plans.
3. Call `training_start`, `comparison_start` or `export_create` with the approved `plan_id` and a fresh lowercase UUIDv4 `request_id`. Persist this request ID before sending.
4. Poll `operation_get` with the returned `operation_id`, no more frequently than `next_poll_after_ms`. Repeating the identical request ID/payload returns the original operation. Changing the payload with that ID is rejected.

A plan consumes its approval once. On a timeout, retry the same request; never invent a new ID to bypass an uncertain outcome. States are `accepted`, `dispatching`, `running`, `succeeded`, `failed`, `cancelled`, and `unknown`. A successful tool response can describe queued or failed work: inspect `state` and `error`. Errors expose safe codes, not provider responses or stack traces.

An owner can enable **Unattended operations** for a connection's selected write scopes and objects. Each plan is auto-approved only within its step, wall-time and byte limits; larger plans return to explicit approval. This policy permits repeated operations within the total deployment storage budget. It is not a monetary or daily spending cap. Cancellation is controlled by its separate scope and can lose progress since the last checkpoint.

The training recipe is SDXL `quick_test`, rank 16, AdamW, up to 600 steps and 3,600 seconds, using the owner-installed `models/checkpoints/sd_xl_base_1.0.safetensors`. It uses private verified dataset copies and fixed trainer configuration. Source dataset, snapshots, configuration and model changes before launch block execution. No arbitrary TOML, imports, commands, URLs or environment overrides are accepted.

Comparison supports MCP recipe-v1 SDXL runs with a valid terminal checkpoint. It generates two images at 20 steps with a fixed graph; publication uses a unique no-clobber LoRA directory. It never starts ComfyUI or downloads missing models. An accepted provider request with a lost response becomes `unknown`, never an automatic second submission.

Exports contain the selected checkpoint tensor data, minimal `experiment.json`, a README, and up to two explicitly selected comparison images. Trainer checkpoint metadata and image metadata are stripped from copies. Original datasets, captions, logs, optimizer state and credentials are excluded. Trained weights themselves can retain training information; export is not anonymization.

The result's `artifact_id` identifies `GET /mcp-artifacts/{artifact_id}` on the same origin. Download using the same connection's bearer header and `artifacts:read` grant. The archive expires after 24 hours; URLs contain no credentials, range requests are refused, and revocation/expiry is checked during streaming. The original checkpoint is not modified.

## Execution release gates and limits

| Variable | Default | Meaning |
|---|---|---|
| `MCP_PUBLIC_URL` | empty | Exact public HTTPS origin, or loopback HTTP; empty means unavailable |
| `MCP_EXECUTION_ENABLED` | `0` | Operator opts into write tools |
| `MCP_STORAGE_VERIFIED` | `0` | Operator has verified locks, atomic replace, file/directory fsync and permissions on the actual volume |
| `MCP_GPU_VERIFIED` | `0` | Operator has completed the disposable target-image training/comparison/cancellation checks |
| `MCP_WRITE_BUDGET_BYTES` | `0` | Explicit total budget for MCP allocations; zero refuses allocations |

All three enablement flags must equal `1`. They are operator attestations, not automatic verification. Do not change them merely to reveal buttons. Live GPU, complete CUDA images and the target network volume remain unverified for this source change; keep writes disabled for normal users until the release gates pass.

The process reserves estimated bytes before acceptance, also checks reported filesystem space, and leaves a 1 GiB reserve. Reservations include private copies and persist even after failed/finished operations. They cannot guarantee provider quota or account for unrelated writers. A running training watchdog checks elapsed time, output growth and free space, and signals only a verified process group. A Portal crash or storage failure can prevent that watchdog from stopping work. The fixed comparison has bounded images/steps but no guaranteed wall-time cancellation.

Other bounds: 64 KiB request, 256 KiB tool response, 60 authenticated requests/minute per connection, 120/minute per peer, 30 mutation calls/minute, 32 concurrent RPCs, four blocking workers, one preparation worker, two artifact streams. Dataset inspection accepts at most 5,000 entries, depth 16, 256 MiB total, 32 MiB per file and 40 million pixels per image, with a 30-second scan deadline. Oversized data is rejected, not silently skipped.

The private ledger is `/workspace/config/mcp/state.json` (0600, private 0700 directory). It is bounded to 8 MiB, 100 connections, 256 live plans, 2,048 operation tombstones and 1,000 recent audit entries. Expired plans are pruned when a new plan is created. There is no automatic artifact/cache cleanup or reservation release yet. Hitting a bound refuses new work; it does not delete user data or forget replay identities.

## Disable, recover and bootstrap

Disable MCP in Settings to reject new access and invalidate pending/queued authorization. Running training/comparison work continues; cancel it through the existing owner interface after inspecting status. Revocation and grant edits also leave running work intact. Restart invalidates unused plans and marks interrupted acceptance/dispatch records `unknown`. Known training-run linkage can reconcile terminal results; unknown provider outcomes need manual owner investigation. There is no MCP reset/retry/reconciliation tool.

Preserve the ledger and operation records when investigating. Do not delete `config/mcp` to clear a conflict or reclaim capacity: that discards revocation and replay history. Do not restore an older ledger over current state. Stop Portal, retain a consistent private backup, inspect the linked run/provider queue and partial files, and keep uncertain work disabled. A versioned maintenance/reconciliation workflow is still a release follow-up.

For headless read-only bootstrap, stop Portal first and run from the repository/image root with its core Python:

```bash
python -m apps.Portal.mcp_server.cli --workspace /workspace create-read-client \
  --label 'My private client' --dataset '1_my-dataset' --days 7
```

The command verifies selected objects, acquires exclusive ownership, creates a read-only connection and enables MCP. It prints the credential once; protect that terminal output. Repeat `--dataset` or `--run` to grant other existing objects. It refuses a live Portal owner and never enables write tools. Restart Portal afterward. For emergency offline disable:

```bash
python -m apps.Portal.mcp_server.cli --workspace /workspace disable
```

Use a single Portal process per workspace. A second owner fails closed. No path here changes the container's other services or promises isolation from a trusted workspace administrator/root process.
