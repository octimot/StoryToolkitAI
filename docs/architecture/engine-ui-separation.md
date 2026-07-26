# Separate processing from the user interface

**Architecture status:** Implemented
**Release status:** Architecture hardening implemented; release verification pending
**Scope:** Internal Python architecture for Version 1
**Code reviewed through:** `f62b7877936902615a5cf62f46c73d48b4bdd5d1`
**Intended release candidate:** `v1.0.0-rc.1`
**Implemented boundary:** [`tk-engine-boundary.md`](./tk-engine-boundary.md)
**Closed migration inventory:** [`current-ui-coupling.md`](./current-ui-coupling.md)
**Version 1 architecture freeze:** [`version-1-architecture-freeze.md`](./version-1-architecture-freeze.md)

## Summary

StoryToolkitAI separates processing from presentation.

Processing works without importing or calling Tkinter or another user interface. The Tk interface and CLI start operations and read processing state through `StoryToolkitEngine`. Processing returns UI-independent results and publishes events for progress and presentation-relevant state changes. Each interface decides how to display them.

Version 1 keeps the application in one Python process. A local service, web UI, TUI, Tauri application and repository split remain Version 2 work.

`build_runtime(...)` constructs `StoryToolkitAI`, the private `ToolkitOps`, and
`StoryToolkitEngine`. Tk receives `StoryToolkitAI` for existing settings,
paths, application state, and lifecycle work, plus the engine for processing.
The CLI receives its parsed arguments and parser for command-line presentation,
plus the engine for processing. Neither interface receives `ToolkitOps`.

## Why this change was needed

The earlier application structure allowed processing code to know about the Tk interface and allowed UI code to reach directly into processing objects. This made it harder to:

- test processing without launching a UI;
- add another interface;
- change queue, search, assistant or Resolve internals safely;
- identify which part of the application owned a responsibility;
- prepare for a separate engine process.

The Version 1 dependency direction is:

```text
Tk / CLI / future interfaces
              |
              v
     StoryToolkitEngine
              |
              v
processing, models, storage and integrations
```

Processing must not depend on a UI.

## Version 1 goal

StoryToolkitAI Version 1 preserves the existing product while establishing a stable internal boundary.

Version 1 provides:

- the existing Tk application as the primary UI;
- the existing CLI functionality;
- compatibility with existing projects, transcriptions, stories, settings and queue data;
- one public `StoryToolkitEngine` processing entry point for first-party interfaces;
- UI-independent processing;
- simple event reporting;
- tests that protect the dependency direction;
- a stable internal boundary that prepares the codebase for a separate process in Version 2.

Version 1 does not require an HTTP API, a separate engine process or a new frontend.

## Version 2 direction

Version 2 may add:

- a local engine process;
- an HTTP API;
- a WebSocket or similar event stream;
- an expanded CLI;
- a TUI;
- a web-based UI;
- a Tauri desktop application using the shared web UI;
- independently released engine and UI repositories;
- stronger persistent-job and reconnect support.

These items must not be added to Version 1 merely to make the internal architecture look more complete.

## Rules

### 1. Processing must not import UI code

Code responsible for processing, jobs or integrations must not import modules from `storytoolkitai.ui`.

Allowed:

```text
UI -> StoryToolkitEngine -> processing
```

Not allowed:

```text
processing -> UI
```

### 2. Processing must not perform presentation work

Processing code must not:

- open Tk dialogs;
- update widgets;
- send desktop notifications directly;
- format terminal presentation output;
- require a window object;
- call methods on a UI object;
- inspect command-line flags to decide processing policy.

Processing reports what happened. The interface decides how to display it.

Process restart and executable-path operations may still use `sys.argv` when they are not interpreting command-line policy.

### 3. First-party interfaces use `StoryToolkitEngine`

Tk and CLI processing operations must go through `StoryToolkitEngine`.

First-party UI code must not receive or recover:

- `ToolkitOps`;
- `ProcessingQueue`;
- raw search processors;
- assistant implementations;
- `MotsResolve`;
- the raw Resolve API wrapper;
- the internal `NLE` state object.

`ToolkitOps` may remain a substantial internal processing coordinator. Version 1 does not require removing it or moving all of its logic into smaller classes.

### 4. Engine methods describe real operations

Engine methods should represent meaningful user operations or state queries.

Appropriate examples include:

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
get_processing_queue
get_resolve_api
execute_legacy_method
call_operation_by_name
```

The engine is a boundary, not a renamed reference to the implementation object.

### 5. Boundary data should be detached and simple where practical

Preferred boundary values include:

- strings;
- numbers;
- booleans;
- lists and dictionaries;
- IDs;
- file paths;
- detached snapshots that callers may mutate safely;
- dataclasses;
- small Pydantic models where validation is useful.

Do not pass UI objects, UI callbacks, worker threads, open file handles or live model implementations through the engine boundary.

Version 1 remains in-process and does not require every value to be serializable. Accepted in-process values are documented in `tk-engine-boundary.md`.

Engine events are also in-process in Version 1. Emission is synchronous in the
emitter's thread, but each listener receives its own deep copy of the event.
This prevents a listener from changing nested payload data seen by the
producer or another listener. Named payloads use simple values to ease a
future transport migration; this is not a wire protocol or a claim that the
rest of the engine boundary is transport-ready.

### 6. Long-running processing is represented as jobs

Long-running operations such as ingest, transcription, indexing and speaker detection use processing jobs.

Interfaces should be able to:

- start a job;
- receive its ID;
- read its current state;
- receive change events;
- cancel it when supported;
- inspect its error or result through engine-owned state.

The existing queue remains valid for Version 1. Its internals are hidden behind the engine.

### 7. Existing data formats remain compatible

The Version 1 restructuring should avoid unnecessary changes to:

- project files;
- transcription files;
- story files;
- settings;
- queue data;
- export behaviour.

When a format change is unavoidable, it requires a documented reason, a compatibility or migration path and fixture-based tests.

### 8. Add abstractions only when they solve a current problem

StoryToolkitAI does not require strict layered architecture or class-per-operation design.

Do not add:

- dependency-injection frameworks;
- factories without a concrete need;
- generic repository classes;
- abstract interfaces with no likely second implementation;
- wrappers that only rename a function;
- directories created only to match an architecture diagram.

Ordinary functions are preferred for stateless work. Classes are appropriate when they own meaningful state or a resource.

A proposed abstraction should answer:

> What concrete problem does this solve today?

If the answer is unclear, do not add it.

### 9. Preserve a runnable application

Architecture changes should be made in small logical commits. The application and tests should remain in a known working state as often as practical.

Temporary compatibility code is acceptable during a migration, but it must either be removed or explicitly documented before a release boundary is declared complete.

## Terminology

| Term | Meaning |
| --- | --- |
| Engine | The UI-independent processing entry point used by first-party interfaces |
| Processing | Transcription, ingest, indexing, search, assistant work, jobs, exports and related operations |
| Operation | Something StoryToolkitAI can do for a user |
| Event | A simple message saying that something happened or changed |
| Storage | Code that loads or saves projects, transcriptions, stories, settings or job data |
| Integration | Code that communicates with Resolve, FFmpeg, Whisper, LLM providers or another external system |
| UI | Tkinter, a terminal interface, a browser interface or a future Tauri interface |
| API model | A small data structure exchanged across a future process boundary |

Terms such as domain, persistence, contracts, ports, adapters and use cases are not required names for StoryToolkitAI modules.

## Version 1 completion criteria

The Version 1 restructuring is complete when:

- the Tk application and CLI still work;
- existing projects, transcriptions, stories and queue data remain compatible;
- processing imports no UI modules;
- processing opens no UI dialogs and sends no desktop notifications directly;
- Tk and CLI use `StoryToolkitEngine` for processing;
- `ToolkitOps` remains private behind the engine;
- UI code does not inspect or mutate queue internals;
- live search processors and assistant implementations remain engine-owned;
- first-party interfaces do not access Resolve implementation objects;
- command-line policy is converted into explicit runtime options before processing construction;
- progress and state changes use UI-independent events;
- boundary modules can be imported without loading Tk or UI modules;
- architecture tests and source audits protect the implemented rules;
- accepted in-process Version 1 bridges are documented;
- the implemented boundary is described in `tk-engine-boundary.md`.

The architecture completion criteria above are separate from the release
gate. Real source and packaged-application checks for startup, shutdown,
processing devices, FFmpeg, notifications, queue workflows, search,
Assistant, Resolve, and copied stable-release data remain recorded as manual
work in [`docs/testing.md`](../testing.md).

## Consequences

The decision adds a small amount of deliberate structure:

- one public engine object;
- simple event data;
- explicit runtime options;
- tests around the processing boundary;
- clearer ownership of interface and processing behaviour.

The Version 1 application still runs in one Python process. The separation is architectural rather than operational.

That is intentional. It allows the current product to prove the boundary before Version 2 adds networking, separate processes and new interfaces.
