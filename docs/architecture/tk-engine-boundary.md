# Tk, CLI and engine boundary

**Architecture status:** Implemented
**Release status:** Pending concurrency and release-hardening fixes
**Branch reviewed:** `dev`
**Reviewed through:** `b37334263e8620d91365dc32d333e536d06c1a58`
**Related decision:** [`engine-ui-separation.md`](./engine-ui-separation.md)
**Closed migration inventory:** [`current-ui-coupling.md`](./current-ui-coupling.md)

## Purpose

This document records the first-party interface boundary implemented during the Version 1 refactor.

It is not a proposal for a framework. It describes the dependency direction that the current Tk interface and CLI must preserve.

## Implemented dependency direction

```text
command-line arguments
          |
          v
    RuntimeOptions
          |
          v
   build_runtime(...)
          |
          +--> StoryToolkitAI
          |
          +--> ToolkitOps
          |       |
          |       +--> ProcessingQueue
          |       +--> search processors
          |       +--> assistant implementations
          |       +--> Resolve integration
          |       +--> processing models and settings
          |
          +--> StoryToolkitEngine
                  |
                  +--> public processing operations
                  +--> detached queue and search state
                  +--> engine-owned search sessions
                  +--> engine-owned assistant sessions
                  +--> Resolve commands and state snapshots
                  +--> processing events

StoryToolkitAI + StoryToolkitEngine
                  |
                  v
             Tk interface

StoryToolkitEngine
                  |
                  v
                 CLI
```

`ToolkitOps` is constructed inside `build_runtime(...)` and remains private behind `StoryToolkitEngine`.

The Tk interface receives `StoryToolkitAI` for existing application, settings and lifecycle behaviour. It receives `StoryToolkitEngine` for processing.

The CLI receives `StoryToolkitEngine` as its processing entry point.

## Public object graph

Runtime construction returns:

```python
stAI, engine = build_runtime(options)
```

The graphical interface is started with:

```python
run_gui(
    stAI=stAI,
    engine=engine,
)
```

The command-line interface is started with:

```python
run_cli(
    args=args,
    parser=parser,
    engine=engine,
)
```

First-party interfaces must not receive or recover the private `ToolkitOps` object.

## Responsibilities

### Tk interface

The Tk interface owns presentation behaviour:

- windows and widgets;
- dialogs and file selection;
- notifications;
- menus, labels and visual state;
- Tk-thread scheduling;
- form-specific input validation;
- display of engine results and errors.

### CLI

The CLI owns command-line presentation behaviour:

- parsing command-line values;
- validating command-line-only input;
- formatting terminal output;
- selecting the appropriate public engine operation.

### `StoryToolkitEngine`

The engine owns the first-party processing boundary:

- queue inspection, job creation, submission and cancellation;
- engine events;
- search-session construction and execution;
- assistant-session construction and replacement;
- Resolve connection, state snapshots and commands;
- processing capability queries such as languages and devices;
- safe delegation to private processing implementations.

### `ToolkitOps`

`ToolkitOps` remains an internal processing coordinator.

It may own processing resources, task handlers, models and integrations. It is not a first-party interface dependency, and Version 1 does not require it to be empty or removed.

## Required rules

### Processing must not depend on UI code

Modules under `storytoolkitai/core` and `storytoolkitai/integrations` must not import Tk interface modules or receive live Tk objects.

Processing reports state or returns results. It does not display dialogs, update widgets or invoke presentation objects.

### Interfaces must use the engine for processing

Modules under `storytoolkitai/ui` must not import or reference:

- `ToolkitOps`;
- `ProcessingQueue`;
- `toolkit_ops_obj`;
- the Resolve `NLE` state object;
- the raw `resolve_api` wrapper;
- `MotsResolve`;
- raw search processors;
- assistant implementation objects.

UI-independent content models may still be used directly during Version 1.

### Imports must be explicit

UI modules and processing-boundary modules must not use wildcard imports.

Explicit imports keep dependencies reviewable and prevent implementation names from entering another layer accidentally.

### Runtime policy must be explicit

Command-line values are converted into immutable `RuntimeOptions` before processing objects are constructed.

Processing modules must not branch on command-line flags or retain an argparse namespace.

Uses of `sys.argv` for process restart or executable-path discovery are process mechanics and are allowed when they do not interpret runtime policy.

### Engine methods must describe real operations

Add an engine method when a first-party interface needs a meaningful operation or state query.

Do not expose generic access to private implementation objects.

### Returned state must be detached where practical

Queue state, search state, assistant metadata, Resolve state and mutable collections returned to an interface should be copied before crossing the boundary.

Live processing objects remain private unless explicitly documented as an accepted Version 1 bridge.

### Events do not replace authoritative state

Engine events indicate that something happened or state may have changed.

For queue and search workflows, an interface retrieves a copied engine snapshot after receiving an event or polling tick. Snapshot synchronization remains a release-hardening requirement. Event payloads are not the only source of authoritative state when the engine provides a query method.

### Tk updates stay on the Tk thread

Engine listeners may be called from worker threads.

The Tk listener only places events into a thread-safe Python queue. A bounded callback scheduled by the Tk-owning thread polls that queue and performs event handling. Processing threads therefore do not call Tk methods or wait for Tk to process an event.

Shutdown stops the Tk poller, and listener calls that observe the shutdown state return without enqueueing. Rejection is intentionally best-effort rather than atomic with queue insertion: an event already entering concurrently may reach the abandoned queue after polling stops. It is discarded safely when the UI object is released and cannot update Tk.

## Implemented feature boundaries

### Queue and ingest

Tk does not read or mutate `ProcessingQueue` directly.

Queue IDs, placeholder jobs, status changes, submission and cancellation are owned by processing and exposed through engine methods. Queue queries return copied queue data, excluding runtime-only fields such as task callables. Queue snapshot synchronization remains a release-hardening requirement.

### Search

The engine owns live text and video search processors, preparation workers and search-session state.

Tk stores a search ID and uses engine methods to prepare, inspect, query and close a search session.

### Assistant

The engine owns live assistant implementations and their `ToolkitOps` dependency.

Tk keeps an `AssistantSession` handle. Replacing a model preserves the stable engine session while the private implementation is replaced inside the engine.

### Resolve

Tk and CLI do not access `NLE`, `MotsResolve` or the raw `resolve_api`.

Resolve presentation state is obtained from engine snapshots. Connection, rendering, marker operations, media import, playhead movement and polling control are invoked through explicit engine methods.

The internal `NLE` state object may remain inside processing during Version 1.

### Runtime construction

Command-line arguments are converted into `RuntimeOptions` before processing construction.

`StoryToolkitAI` and `ToolkitOps` receive explicit runtime decisions. `ToolkitOps` is constructed privately and wrapped by `StoryToolkitEngine`.

### Events

Named event factories produce detached, transport-safe payload data. The architecture test requires a representative simple-data sample for every public factory. It also inventories direct `EngineEvent` construction: direct producers use literal event names, and the only reviewed direct payload is the fixed simple `job.changed` queue summary. Add a named factory and sample before introducing another payload shape.

Queue events expose stable job summaries rather than callables, threads or temporary processing objects.

## Accepted Version 1 in-process bridges

Version 1 remains a single Python process.

The following values may cross the current in-process boundary even though they are not yet suitable for an HTTP or WebSocket API:

- `StoryToolkitAI` passed to Tk for settings, paths and application lifecycle behaviour;
- UI-independent `Project`, `Transcription`, `Story`, `Document` and related model objects;
- `IngestSettings` passed to `start_ingest(...)`;
- `AssistantSession`, a lightweight handle to an engine-owned assistant;
- the existing Resolve render monitor used by monitored rendering;
- existing `Timecode` values used by Resolve-related Tk behaviour;
- image arrays returned for video-search frame presentation;
- operation-specific return shapes used by existing in-process workflows.

These are accepted Version 1 limits, not Version 2 API designs.

Before a separate engine process is introduced, each required cross-process value must be replaced with documented serializable data, an ID, an artifact path or a dedicated event.

## Architecture checks

The following tests protect this boundary:

```text
tests/architecture/test_ui_import_boundary.py
tests/architecture/test_ui_engine_boundary.py
tests/architecture/test_ui_resolve_boundary.py
tests/architecture/test_runtime_object_graph.py
tests/architecture/test_search_boundary.py
tests/architecture/test_legacy_event_boundary.py
tests/architecture/test_processing_boundary.py
tests/architecture/test_event_data_boundary.py
tests/architecture/test_headless_engine_import.py
```

The checks require that:

- processing does not import UI modules;
- UI and processing-boundary modules do not use wildcard imports;
- UI modules do not import processing coordinators, queue implementation or Resolve internals;
- forbidden processing names and attributes do not appear in the UI object graph;
- `run_gui(...)` accepts only `stAI` and `engine`;
- `build_runtime(...)` returns only `stAI` and `engine`;
- first-party search ownership remains behind the engine;
- removed callback and action-event compatibility paths do not return;
- processing does not read command-line policy from `sys.argv` or retained `cli_args`;
- named event factories and reviewed direct event producers use simple payload data;
- importing and constructing the runtime boundary does not load or start Tkinter, CustomTkinter or `storytoolkitai.ui`;
- `receive_engine_event(...)`, the listener registered with the engine, only accepts or rejects an event and writes accepted events to the thread-safe inbox.

These architecture tests enforce the reviewed first-party coding patterns rather than attempting to prove every possible runtime behaviour. They detect normal imports, supported literal dynamic imports, known private attribute access, runtime object wiring and reviewed event payload construction. New reflection, computed imports, plugin-loading patterns or direct event-construction styles must be accompanied by an appropriate extension to the architecture tests.

Run the focused architecture suite with:

```bash
python -m pytest tests/architecture -q
```

Run the remaining tests with:

```bash
python -m pytest --ignore=tests/architecture -q
```

Run the complete suite before a release candidate:

```bash
python -m pytest -q
```

## Repeatable source audit

Run these commands from the repository root.

### Processing references to UI concepts

Expected result: no matches under core or integrations.

```bash
rg -n --glob '*.py'   'toolkit_UI_obj|notify_via_os|notify_via_messagebox|AskDialog|ask_for_target_dir|receive_notification|NotificationService|NotificationMessage'   storytoolkitai/core   storytoolkitai/integrations
```

### Direct processing imports of UI modules

Expected result: no matches.

```bash
rg -n --glob '*.py'   '(^|[[:space:]])(from|import)[[:space:]]+storytoolkitai\.ui|from[[:space:]]+\.\.?ui'   storytoolkitai/core   storytoolkitai/integrations
```

### First-party UI processing bypasses

Expected result: no matches.

```bash
rg -n --glob '*.py'   'toolkit_ops_obj|ToolkitOps|\.processing_queue|\.resolve_api|\bNLE\b|MotsResolve'   storytoolkitai/ui
```

### UI wildcard imports

Expected result: no matches.

```bash
rg -n --glob '*.py'   '(^|[[:space:]])from[[:space:]].*[[:space:]]import[[:space:]]+\*'   storytoolkitai/ui
```

### Processing-boundary wildcard imports

Expected result: no matches.

```bash
rg -n --glob '*.py'   '(^|[[:space:]])from[[:space:]].*[[:space:]]import[[:space:]]+\*'   storytoolkitai/core/toolkit_ops   storytoolkitai/integrations   storytoolkitai/app.py   storytoolkitai/core/engine.py   storytoolkitai/core/events.py   storytoolkitai/core/search_sessions.py
```

### Runtime-policy boundary

The architecture test distinguishes prohibited command-line policy reads from legitimate process restart and executable-path operations.

```bash
python -m pytest   tests/architecture/test_processing_boundary.py::test_processing_does_not_read_ambient_runtime_state   -q
```

Expected result: the test passes.

### Removed legacy event paths

Expected result: no matches under core or integrations.

```bash
rg -n --glob '*.py'   'notify_observers|action\.triggered|create_action_triggered_event|_emit_legacy_action|on_stop_action_name'   storytoolkitai/core   storytoolkitai/integrations
```

## Version 1 release gate

The Version 1 architecture boundary is ready for release when:

- the architecture test suite passes;
- the remaining automated test suite passes;
- the complete test suite passes;
- the documented source audits produce no unexpected matches;
- Tk and CLI use `StoryToolkitEngine` for processing;
- accepted in-process bridges remain explicitly documented;
- the macOS release smoke test completes successfully;
- known runtime issues have a current classification.

## Migration closure

The first-party Tk and CLI processing boundary is complete through:

- the queue, event, search, CLI and runtime-option migrations;
- the final Tk engine-boundary commits;
- `b37334263e8620d91365dc32d333e536d06c1a58`, which closes the remaining Version 1 architecture guard gaps.

Further cleanup may simplify `ToolkitOps`, `StoryToolkitAI` or operation-specific return values, but it must not weaken the implemented dependency direction.

A separate Version 2 plan will define process, transport and frontend boundaries.
