# Separate processing from the user interface

**Scope:** Internal Python architecture for version 1

## Summary

StoryToolkitAI will separate processing from presentation.

Processing must work without importing or calling Tkinter or any other user interface. The current Tkinter UI and CLI will start operations and read their state through a small internal engine interface.

Processing will report progress, completion, errors, warnings, and state changes using simple events. The UI will decide how those events are presented.

Version 1 keeps the application in a single Python process.
For version 2, we are considering: a local server, a web UI, TUI, potential Tauri application, repository split, and other process-level changes are version 2 work.

## Why we are making this change

The current application contains useful separation between `core`, `toolkit_ops`, integrations, and UI modules, but the boundary is not complete.

Some processing code knows about the Tkinter UI, some UI code reads processing internals directly, and the main application passes shared implementation objects into the selected interface.

This makes it harder to:

* test processing without launching a UI;
* add a web UI, TUI, improved CLI, or Tauri desktop UI;
* run processing in a separate process;
* change queue or model-management internals safely;
* understand which code owns a particular responsibility.

The purpose of this restructuring is to establish one clear dependency direction:

```text
Tkinter / CLI / future UIs
            |
            v
     StoryToolkitEngine
            |
            v
 processing, storage, and integrations
```

The engine and processing code must not depend on a UI.

## Version 1 goal

StoryToolkitAI 1.0 will preserve the existing product while reorganizing its internals.

Version 1 should provide:

* the existing Tkinter application as the main UI;
* the existing CLI functionality;
* compatibility with existing projects, transcriptions, stories, settings, and queue data;
* a small `StoryToolkitEngine` interface used by both Tkinter and the CLI;
* UI-independent processing;
* simple event reporting;
* tests that protect current behaviour;
* a code structure ready for a process boundary in version 2.

Version 1 does not need an HTTP API or a new frontend.

## Version 2 direction

After the version 1 boundary is proven, version 2 may add:

* a local engine process;
* an HTTP API;
* a WebSocket or similar event stream;
* a full CLI;
* potential TUI;
* potential web-based UI;
* potential Tauri desktop application from web-based UI;
* independently released engine and UI repositories;
* stronger job persistence and reconnect support.

These items must not expand the version 1 restructuring unless they are required to complete the internal separation.

## Rules

### 1. Processing must not import UI code

Code responsible for processing, storage, jobs, or integrations must not import modules from `storytoolkitai.ui`.

Not allowed:

```python
from storytoolkitai.ui.toolkit_ui import ToolkitUI
```

The restriction is intentionally one-way:

```text
UI -> Engine -> processing
```

is allowed.

```text
processing -> UI
```

is not allowed.

### 2. Processing must not perform presentation work

Processing code must not:

* open Tkinter dialogs;
* update widgets;
* send desktop notifications directly;
* format terminal output;
* inspect CLI arguments;
* require a window object;
* call methods on a UI object.

Processing reports what happened. The UI decides how to display it.

For example, processing may emit:

```python
EngineEvent(
    type="job.completed",
    data={
        "job_id": job_id,
        "message": "Transcription completed",
    },
)
```

The Tkinter UI may turn that into a desktop notification. A CLI may print a line. Another UI may ignore it.

### 3. UIs use a small engine interface

The Tkinter UI and CLI must use a small public object called `StoryToolkitEngine`.

Typical methods may include:

```python
engine.start_ingest(...)
engine.start_transcription(...)
engine.get_job(...)
engine.list_jobs(...)
engine.cancel_job(...)
engine.open_project(...)
engine.save_transcription(...)
engine.search(...)
```

The exact method list will grow during the migration.

UI code must not depend on:

* queue dictionaries;
* worker threads;
* loaded model objects;
* private `ToolkitOps` state;
* internal callbacks;
* implementation-specific storage details.

### 4. Boundary data should be simple

Values passed between the UI and engine should be easy to understand and capable of being converted to JSON later.

Preferred values include:

* strings;
* numbers;
* booleans;
* lists and dictionaries;
* IDs;
* file paths;
* dataclasses;
* small Pydantic models where validation is useful.

Avoid passing:

* Tkinter windows or widgets;
* callbacks tied to a UI;
* threads;
* open file handles;
* live model instances;
* database connections;
* large mutable application objects.

Version 1 does not require every value to be serialized. It should simply avoid values that make a future process boundary unnecessarily difficult.

### 5. Long-running work is represented as jobs

Operations such as ingest, transcription, indexing, and model work should be represented as jobs.

The UI should be able to:

* start a job;
* receive its ID;
* read its current state;
* receive progress events;
* cancel it when supported;
* inspect its result or error.

The existing processing queue may remain in version 1. The immediate goal is to hide its internals behind engine methods, not to replace it.

### 6. Existing data formats should remain compatible

The version 1 restructuring should avoid unnecessary changes to:

* project files;
* transcription files;
* story files;
* settings;
* queue data;
* export behaviour.

When a format change is unavoidable, it must include:

* a documented reason;
* a compatibility or migration path;
* tests using existing fixture files.

### 7. Add abstractions only when they solve a current problem

This project will not adopt a strict layered architecture or a class-per-operation style.

Do not add:

* dependency-injection frameworks;
* factories without a concrete need;
* generic repository classes;
* abstract interfaces with no likely second implementation;
* wrapper classes that only rename a function;
* directories created only to match an architecture diagram.

Ordinary functions are preferred when an operation is stateless.

Classes are appropriate when they own meaningful state or a resource, such as:

* the engine lifecycle;
* the processing queue;
* loaded models;
* a Resolve connection;
* a project or transcription;
* an API client.

A proposed abstraction should answer this question:

> What concrete problem does this solve today?

If the answer is unclear, do not add it.

### 8. Preserve a runnable application during the migration

The restructuring will be performed incrementally on the `dev` branch.

Changes should be made in small logical commits. The application and tests should remain in a known working state as often as practical.

The migration should use temporary compatibility wrappers when they allow one feature to move at a time. Temporary code must be clearly marked and removed before the version 1 release.

## Terminology

The project will prefer plain names in code and documentation.

| Term        | Meaning                                                                                                 |
| ----------- | ------------------------------------------------------------------------------------------------------- |
| Engine      | The UI-independent entry point used by Tkinter, the CLI, and future clients                             |
| Processing  | Transcription, ingest, indexing, search, stories, exports, assistant work, jobs, and related operations |
| Operation   | Something StoryToolkitAI can do for a user                                                              |
| Event       | A simple message saying that something happened or changed                                              |
| Storage     | Code that loads or saves projects, transcriptions, stories, settings, or job data                       |
| Integration | Code that communicates with Resolve, FFmpeg, Whisper, LLM providers, or other external systems          |
| UI          | Tkinter, a terminal interface, a browser interface, or the future Tauri interface                       |
| API model   | A small data structure exchanged between a UI and the engine                                            |

Terms such as domain, persistence, contracts, ports, adapters, and use cases may appear in external architecture discussions, but they are not required names for StoryToolkitAI modules.

## Initial code direction

The existing structure should be changed gradually. A possible version 1 direction is:

```text
storytoolkitai/
├── __main__.py
├── app.py
├── core/
│   ├── engine.py
│   ├── events.py
│   ├── jobs.py
│   └── operations/
├── storage/
├── integrations/
└── ui/
```

This is not a mandatory final tree.

Files should be moved only when the move makes ownership clearer or removes coupling. A tidy directory structure is not more important than understandable code and preserved behaviour.

## Version 1 completion criteria

The restructuring is complete when:

* the current Tkinter application still works;
* existing projects and transcriptions still load;
* processing imports no UI modules;
* processing opens no dialogs;
* processing sends no desktop notifications directly;
* Tkinter uses `StoryToolkitEngine`;
* the CLI uses `StoryToolkitEngine`;
* UI code does not inspect queue internals;
* progress and state changes use simple events;
* important existing behaviour has characterization tests;
* the engine can be created in a headless test;
* `ToolkitOps` is removed or contains no unique processing logic;
* the code structure and public engine interface are documented.

## Consequences

This decision adds a small amount of structure:

* a public engine object;
* simple event data;
* tests around the processing boundary;
* clearer ownership of UI, processing, storage, and integration code.

It should reduce long-term complexity by removing UI callbacks and shared implementation objects from processing.

The version 1 application will still run in one Python process. This means the separation is architectural rather than operational. That is intentional: it lets the existing application prove the boundary before version 2 adds networking, separate processes, and new interfaces.
