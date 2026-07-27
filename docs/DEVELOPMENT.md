# Development

This records the current architecture and repeatable checks maintainers must
preserve. Migration records belong in Git history, issues, and pull requests.

## Runtime structure

```text
command-line arguments -> RuntimeOptions -> build_runtime(...)
                                             |-> StoryToolkitAI
                                             `-> StoryToolkitEngine
                                                    `-> private processing

StoryToolkitAI + StoryToolkitEngine -> Tk
StoryToolkitEngine                  -> CLI
```

Tk and CLI perform processing through `StoryToolkitEngine`.

`StoryToolkitEngine` owns the first-party processing boundary and keeps
`ToolkitOps`, `ProcessingQueue`, search, assistant, and Resolve implementations
private. Tk also receives `StoryToolkitAI` for state and lifecycle work.

Version 1 remains in-process. Live values explicitly documented as in-process
bridges do not yet constitute a network API.

## Rules maintainers must preserve

- Processing-owned code must not import `storytoolkitai.ui` or call UI code.
- Processing must not open dialogs, update widgets, format terminal output, or
  send desktop notifications directly.
- Tk and CLI must use `StoryToolkitEngine` for processing operations.
- UI code must not recover or inspect private queue, search, assistant, or
  Resolve implementation objects.
- Engine methods must represent real operations or detached state queries, not
  generic access to private objects.
- Exposed mutable processing state must be detached where practical; live
  models, callbacks, threads, and callables remain private.
- Runtime policy must be converted to `RuntimeOptions` before processing is
  constructed instead of being inferred from ambient command-line state.
- Preserve existing data and export formats unless a documented bug requires
  a migration.
- Keep shared-state lock sections short. Do not run expensive processing or
  invoke listeners while holding queue or search registry locks.
- Prefer the smallest concrete implementation; do not add framework layers or
  abstractions without a current need.

## Events and threads

Processing reports changes through `EngineEvent`. Event payloads intended for
first-party interfaces should contain `None`, booleans, numbers, strings, and
lists or dictionaries containing those values.

Event emission is synchronous in the emitter's thread. `EventEmitter` snapshots
and releases its listener lock, then gives each listener a deep copy. Listener
mutation is isolated, and a failing listener must not block later listeners.

Tk's listener only accepts or rejects an event and places accepted events in a
thread-safe inbox. A bounded poll owned by the Tk thread drains that inbox.
Workers must never call Tk methods or wait for Tk event handling. Events sent
before `mainloop()` are retained; shutdown stops polling and rejects later
events. Queue-window refreshes may be coalesced, and delayed UI work must
revalidate its window and shutdown state.

## Queue and search state

Events indicate that state may have changed; they do not replace authoritative
state queries. UI code reads detached queue and search state through engine
methods and must not inspect processing implementation state directly.

`ProcessingQueue` protects shared queue, history, thread, and variable state
with its state lock. It creates deep snapshots under that lock, excludes
runtime-only values such as task callables and temporary output, and emits
deferred `job.changed` events only after the outer synchronized operation has
released the lock.

The engine owns search processors, workers, and session state. The search
registry lock protects only short lookups, identity checks, state updates, and
snapshot creation. Model loading, indexing, searching, and frame retrieval run
outside it. Closing a session prevents new work; already accepted third-party
work may finish, but late results from closed or replaced sessions are dropped.

## Standard test commands

Use the Python 3.11 test environment from the repository root:

```bash
.venv-test/bin/python -m pytest tests/architecture -q
.venv-test/bin/python -m pytest --ignore=tests/architecture -q
.venv-test/bin/python -m pytest -q
.venv-test/bin/python -m compileall -q -f storytoolkitai tests
git diff --check
```

The split commands match CI. All five checks are required for a release.
Automated or mocked results do not prove hardware or packaged-app behavior.

## Source-release checklist

- Run all standard checks on the exact release commit.
- Smoke-test source startup, shutdown, FFmpeg discovery, transcription, queue
  cancellation/recovery, search, Assistant, exports, and stable-release data.
- Test supported Resolve discovery, connection, marker operations, and
  reconnect from the source checkout when Resolve is available.
- Set the stable version and finalize the changelog in the final preparation
  change, then merge the tested tree to `main`.
- Tag and publish the source release without standalone assets, then update the
  source version endpoint when the release should become discoverable.

## Standalone-release checklist

- Select a stable patch version after source rollout and build every artifact
  from that exact commit using the maintainer-approved release procedure.
- Record each artifact's filename, target, checksum, source commit, and signing
  or notarization status; verify the same artifact before publication.
- For every published platform/device variant, test clean install or copy,
  upgrade/uninstall where applicable, first and subsequent launch, shutdown,
  bundled dependencies, and paths containing spaces and Unicode.
- Verify FFmpeg discovery and safe invalid-path failure. Exercise every
  advertised CPU, Metal/MPS, or CUDA path and record evidence against silent
  fallback.
- Run representative transcription, queue cancellation/dependencies/recovery,
  text and video search, Assistant success/failure, exports, and copied
  stable-release data in the packaged application.
- Test Resolve discovery, connection, marker read/write, reconnect and
  packaged-app operation on each supported platform.
- Record manual results and logs per artifact; do not substitute source or
  mocked results. Publish only verified artifacts on the matching GitHub
  release.

## Deferred to Version 2

- A separate engine process and local daemon.
- HTTP/WebSocket transports, wire formats, versioned API contracts, replay,
  remote subscriptions, SDKs, and serialization of current in-process bridges.
- Web, TUI, or Tauri interfaces and independently released UI/engine repos.
- Remote or multi-user processing, stronger persistent-job/reconnect support,
  and a replacement queue database.
- Broad rewrites of `ToolkitOps`, package renames, or a general plugin or
  dependency-injection architecture without a concrete Version 2 need.

## Documentation policy

Documentation merged to `main` should describe the current architecture, a
public feature, or a repeatable maintenance process. Migration plans,
investigation logs, inventories, freeze notices, and temporary checklists may
live in feature branches or pull requests, but should be removed before merge
once their lasting conclusions are incorporated here.

Current truth belongs in `main`; its history belongs in branches, commits, issues, and pull requests.
