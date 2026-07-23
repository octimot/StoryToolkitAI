# Tk and engine boundary

**Status:** Implemented for the StoryToolkitAI Version 1 architecture  
**Branch reviewed:** `dev`  
**Reviewed through:** `13836ca23215f605054d3498c852b1a708e5b314`  
**Related decision:** [`engine-ui-separation.md`](./engine-ui-separation.md)  
**Migration inventory:** [`current-ui-coupling.md`](./current-ui-coupling.md)

## Purpose

This document records the first-party interface boundary implemented during the Version 1 refactor.

It is not a proposal for a new framework. It describes the dependency direction that the current Tk interface and CLI must preserve.

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

The Tk interface receives `StoryToolkitAI` for existing application and settings behaviour and receives `StoryToolkitEngine` for processing.

The CLI receives only `StoryToolkitEngine` for processing.

## Public object graph

The public runtime construction result is:

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

## Interface responsibilities

The Tk interface owns presentation behaviour:

- windows and widgets;
- dialogs and file selection;
- notifications;
- menu state and labels;
- presentation callbacks;
- Tk-thread scheduling;
- user-input validation that is specific to a form;
- display of engine results and errors.

The CLI owns command-line presentation behaviour:

- parsing command-line values;
- validating command-line-only input;
- formatting log output;
- selecting the appropriate public engine operation.

`StoryToolkitEngine` owns the first-party processing boundary:

- queue inspection, creation, submission and cancellation;
- engine events;
- search-session construction and execution;
- assistant-session construction and replacement;
- Resolve connection, state snapshots and commands;
- processing capability queries such as languages and devices;
- safe delegation to the private processing implementation.

`ToolkitOps` remains an internal processing coordinator. It may own processing resources and call integrations, but it is not a first-party interface dependency.

## Required rules

### Processing must not depend on UI code

Modules under `storytoolkitai/core` and `storytoolkitai/integrations` must not import Tk interface modules or receive live Tk objects.

Processing reports state or returns results. It does not display dialogs, update widgets or invoke presentation objects.

### Interfaces must use the engine for processing

Modules under `storytoolkitai/ui` must not import or reference:

- `ToolkitOps`;
- `ProcessingQueue`;
- `toolkit_ops_obj`;
- the Resolve `NLE` global;
- the raw `resolve_api` wrapper;
- `MotsResolve`;
- another processing implementation that bypasses `StoryToolkitEngine`.

UI-independent content models may still be imported directly during Version 1. That accepted limit is described below.

### Imports must be explicit

UI modules must not use wildcard imports.

This rule applies to processing modules and UI libraries alike. Explicit imports keep the actual dependency list reviewable and prevent processing names from entering the UI namespace accidentally.

### Engine methods must describe real operations

Add an engine method when a first-party interface needs a meaningful operation or query.

Good examples include:

```text
start_ingest
cancel_job
create_search
replace_assistant
get_resolve_state
import_resolve_media
```

Do not add generic bypasses such as:

```text
get_toolkit_ops
execute_legacy_method
call_operation_by_name
get_processing_queue
get_resolve_api
```

The engine is a boundary, not a renamed reference to the implementation object.

### Returned state must be detached where practical

Queue state, search state, assistant metadata, Resolve state and other mutable collections returned to an interface should be copied before crossing the boundary.

Live processing objects must remain private unless they are explicitly documented as an accepted in-process Version 1 bridge.

### Events do not replace authoritative state

Engine events indicate that something happened or that state may have changed.

For queue and search workflows, the interface retrieves a current engine snapshot after receiving an event or polling tick. It must not treat an event payload as the only authoritative state when the engine provides a state query.

### Tk updates stay on the Tk thread

Engine listeners may be called from worker threads.

A Tk listener must schedule widget changes onto the Tk event loop instead of changing widgets directly from the processing thread.

## Implemented feature boundaries

### Queue and ingest

Tk does not read or mutate `ProcessingQueue` directly.

Queue IDs, placeholder jobs, status changes, submission and cancellation are owned by processing and exposed through engine methods. Queue queries return detached dictionaries that exclude runtime-only fields such as task callables.

### Search

The engine owns live text and video search processors, preparation workers and search-session state.

Tk stores a search ID and uses engine methods to prepare, inspect, query and close a search session.

### Assistant

The engine owns live assistant implementations and their `ToolkitOps` dependency.

Tk keeps an `AssistantSession` handle. Model replacement preserves the stable engine session while the private implementation is replaced inside the engine.

The handle is an in-process Version 1 API and is not a network contract.

### Resolve

Tk and CLI do not access `NLE`, `MotsResolve` or `resolve_api`.

Resolve presentation state is obtained from detached engine snapshots. Connection, rendering, marker operations, media import, playhead movement and polling control are invoked through explicit engine methods.

The internal `NLE` global may remain inside processing during Version 1. Its existence is not permission for a first-party interface to read it.

### Runtime construction

Command-line arguments are converted into immutable `RuntimeOptions` before processing objects are constructed.

`StoryToolkitAI` and `ToolkitOps` receive explicit runtime decisions instead of an argparse namespace or implicit mode checks.

`ToolkitOps` is constructed privately and wrapped by `StoryToolkitEngine`.

## Accepted Version 1 in-process bridges

Version 1 remains a single Python process. The following values may cross the current in-process boundary even though they are not suitable for a future HTTP or WebSocket API:

- `StoryToolkitAI` passed to Tk for existing settings, paths and application lifecycle behaviour;
- UI-independent `Project`, `Transcription`, `Story`, `Document` and related model objects;
- `IngestSettings` passed to `start_ingest(...)`;
- `AssistantSession`, which is a lightweight handle to an engine-owned assistant;
- the existing Resolve render monitor returned by the monitored-render workflow;
- existing `Timecode` values used by Resolve-related Tk behaviour;
- image arrays returned for video-search frame presentation;
- transitional `action.triggered` events used by remaining compatibility workflows.

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
```

The central checks require that:

- processing does not import the UI;
- UI modules do not use wildcard imports;
- UI modules do not import processing coordinators, queue implementation or Resolve internals;
- forbidden processing names and attributes do not appear in the UI object graph;
- `run_gui(...)` accepts only `stAI` and `engine`;
- `build_runtime(...)` returns only `stAI` and `engine`;
- first-party search ownership remains behind the engine.

Run the focused boundary suite with:

```bash
python -m pytest   tests/architecture/test_ui_import_boundary.py   tests/architecture/test_ui_engine_boundary.py   tests/architecture/test_ui_resolve_boundary.py   tests/architecture/test_runtime_object_graph.py   tests/architecture/test_search_boundary.py   -q
```

Then run the complete suite:

```bash
python -m pytest -q
```

## Repeatable source audit

From the repository root:

```bash
rg -n --glob '*.py'   'toolkit_ops_obj|ToolkitOps|\.processing_queue|\.resolve_api|\bNLE\b|MotsResolve'   storytoolkitai/ui
```

Expected result: no matches.

```bash
rg -n --glob '*.py'   '(^|[[:space:]])(from|import)[[:space:]].*\*'   storytoolkitai/ui
```

Expected result: no matches.

```bash
rg -n --glob '*.py'   'toolkit_ops_obj|ToolkitOps'   storytoolkitai/__main__.py   storytoolkitai/ui
```

Expected result: no matches.

Matches inside `storytoolkitai/app.py` are expected because runtime construction privately creates `ToolkitOps`.

## Migration commits

The final Tk boundary was completed in these commits:

- `3518c45b9c56a60b5e76ab65994bd12223d94e50` — route remaining Tk queue helpers through the engine;
- `7f19e1aeb9295d6ca017389c2c317f693b97fdc9` — route Tk Resolve workflows through the engine;
- `dec9242c6e9064f46de0be4b806fbd4fe139e48e` — move assistant sessions behind the engine;
- `99a82f8afcda1b284416f6c9cdbf33b7d05b3793` — keep `ToolkitOps` private in runtime construction;
- `13836ca23215f605054d3498c852b1a708e5b314` — replace UI wildcard imports and enforce the engine boundary.

Earlier queue, event, search, CLI and runtime-option commits established the prerequisites recorded in [`current-ui-coupling.md`](./current-ui-coupling.md).

## Completion statement

For StoryToolkitAI Version 1, the Tk and CLI processing boundary is complete when the architecture tests above pass and the source audits produce the documented results.

Further cleanup may simplify `ToolkitOps`, `StoryToolkitAI`, compatibility events or return values, but that cleanup must not weaken the implemented dependency direction.
