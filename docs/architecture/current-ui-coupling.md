# Current UI and processing coupling

**Status:** Temporary migration inventory for the StoryToolkitAI 1.0 architecture work
**Branch reviewed:** `dev`
**Reviewed through:** `201ca62`
**Related decision:** [`engine-ui-separation.md`](./engine-ui-separation.md)

Known behavior noticed during the migration is tracked in [`known-refactor-issues.md`](./known-refactor-issues.md).

## Purpose

This document records where the current UI and processing code depend on each other.

It is a migration checklist, not a proposal for a large framework. Its purpose is to keep the remaining coupling visible while StoryToolkitAI is moved towards this dependency direction:

```text
Tkinter UI / CLI
        |
        v
StoryToolkitEngine
        |
        v
Processing, storage, models and integrations
```

Processing must not store, receive or call UI objects.

During the version 1 migration, some UI code may still reach into legacy processing objects. Those remaining cases are tracked here until they are moved behind `StoryToolkitEngine`.

## Status legend

* **Open** — the identified coupling is still present
* **In progress** — an engine-based path exists, but legacy access remains
* **Resolved** — the identified coupling no longer exists
* **Accepted temporarily** — deliberately retained for version 1 within stated limits

## Scope reviewed

The inventory covers the following areas:

```text
storytoolkitai/__main__.py
storytoolkitai/app.py
storytoolkitai/core/engine.py
storytoolkitai/core/events.py
storytoolkitai/core/storytoolkitai.py
storytoolkitai/core/toolkit_ops/toolkit_ops.py
storytoolkitai/core/toolkit_ops/processing_queue.py
storytoolkitai/core/toolkit_ops/search.py
storytoolkitai/core/toolkit_ops/assistant.py
storytoolkitai/core/toolkit_ops/projects.py
storytoolkitai/core/toolkit_ops/transcription.py
storytoolkitai/core/toolkit_ops/story.py
storytoolkitai/core/toolkit_ops/document.py
storytoolkitai/integrations/mots_resolve.py
storytoolkitai/ui/notifications.py
storytoolkitai/ui/toolkit_ui.py
storytoolkitai/ui/toolkit_cli.py
storytoolkitai/ui/menu.py
```

File and symbol names are used instead of fixed line numbers because the larger source files change frequently.

# Current dependency picture

After the completed processing-to-UI separation, queue-boundary, advanced-search, runtime-construction and CLI migration work, the central relationship looks approximately like this:

```text
__main__.py
    |
    +--> runtime_options_from_args(...)
    |       |
    |       +--> explicit RuntimeOptions
    |
    +--> build_runtime(...)
    |       |
    |       +--> StoryToolkitAI
    |       |
    |       +--> ToolkitOps
    |       |       |
    |       |       +--> ProcessingQueue
    |       |       |       |
    |       |       |       +--> explicitly supplied task handlers
    |       |       |       +--> EventEmitter
    |       |       |
    |       |       +--> SearchConfig
    |       |       +--> text and video search processors
    |       |       +--> Resolve API
    |       |       +--> model and settings state
    |       |       +--> EventEmitter
    |       |
    |       +--> StoryToolkitEngine
    |               |
    |               +--> selected ToolkitOps operations
    |               +--> copied queue snapshots
    |               +--> safe queue cancellation
    |               +--> ingest job lifecycle
    |               +--> engine-owned search sessions
    |               +--> search preparation and query execution
    |               +--> event subscriptions
    |               +--> Resolve marker, connection and render operations
    |
    +--> Tk UI
    |       |
    |       +--> receives StoryToolkitEngine
    |       +--> temporarily also receives StoryToolkitAI and ToolkitOps
    |       +--> displays engine events
    |       +--> owns dialogs, notifications, windows and presentation callbacks
    |       +--> reads job and search state through the engine
    |       +--> still accesses ToolkitOps directly for unmigrated features
    |
    +--> CLI
            |
            +--> receives StoryToolkitEngine only for processing
            +--> parses and validates command-line presentation input
            +--> uses engine Resolve connection and render operations
            +--> does not access ToolkitOps, StoryToolkitAI, NLE or resolve_api
```

The direct processing-to-Tk back-reference has been removed.

The queue no longer stores or calls the complete `ToolkitOps` object. It receives only its task-handler mapping and the shared event emitter.

Advanced-search processors no longer receive the complete `ToolkitOps` object. `StoryToolkitEngine` owns their live sessions, preparation workers and query execution, while Tk keeps only the engine-provided search ID.

Command-line arguments are now converted into explicit `RuntimeOptions` before the runtime is constructed. `StoryToolkitAI` and `ToolkitOps` receive only the decisions that affect them, rather than reading an argparse namespace or inferring mode from command-line flags.

The CLI now uses `StoryToolkitEngine` as its only processing entry point. Resolve connection waiting, timeline rendering and render-queue job execution are owned by processing and exposed through plain result dictionaries.

The main remaining direction of broad interface coupling is:

```text
Tk UI -> ToolkitOps and other unmigrated processing internals
```

# Coupling inventory

## C01 — Application construction exposes broad internals to each UI

| Field                  | Detail |
| ---------------------- | ------ |
| **Direction**          | Bootstrap -> UI and processing |
| **Location**           | `storytoolkitai/__main__.py::main`, `storytoolkitai/app.py::build_runtime`, `storytoolkitai/ui/toolkit_ui.py::run_gui`, `storytoolkitai/ui/toolkit_cli.py::run_cli` |
| **Previous state**     | Startup constructed `StoryToolkitAI`, `ToolkitOps` and `StoryToolkitEngine` directly in `__main__.py`. Both Tk and CLI received broad legacy processing objects and could bypass the engine. |
| **Current state**      | `__main__.py` converts parsed arguments into explicit runtime options and delegates object construction to `build_runtime(...)`. The CLI receives only `StoryToolkitEngine` for processing. Tk still receives `StoryToolkitAI`, `ToolkitOps` and the engine through its temporary compatibility path. |
| **Remaining coupling** | The Tk interface can still bypass the engine and call broad processing internals. The CLI part of this coupling is resolved under C16. |
| **Status**             | In progress — CLI resolved; Tk migration remains |
| **Related commits**    | `89eabcf2c6ff3248e5c045f2bd40911d175f12d0`, `9a6f1f05f1b7c0d4116e7027410a61a8a6f6467d`, `201ca62b576adecec333c061c35977f5dd5bfa96` |

## C02 — `ToolkitOps` stores the live Tk application

| Field                  | Detail                                                                                                                                       |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| **Direction**          | Former processing <-> UI cycle                                                                                                               |
| **Location**           | Formerly `ToolkitOps.__init__` and `toolkit_ui.run_gui`                                                                                      |
| **Previous state**     | `ToolkitOps` stored `toolkit_UI_obj`, and `run_gui(...)` assigned the complete Tk application back to it.                                    |
| **Current state**      | `ToolkitOps` no longer stores the Tk application. The Tk application receives `StoryToolkitEngine` directly and subscribes to engine events. |
| **Remaining coupling** | The Tk application still stores `ToolkitOps`, tracked under C01 and C19.                                                                     |
| **Status**             | Resolved                                                                                                                                     |
| **Commits**            | `9a6f1f05f1b7c0d4116e7027410a61a8a6f6467d`, `0de06f4bde23b8655bcf88cfb08fd65ccb0b1d0a`                                                       |

## C03 — Transcription processing issues OS notifications directly

| Field              | Detail                                                                                                                                                         |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Direction**      | Former processing -> UI                                                                                                                                        |
| **Location**       | Formerly `ToolkitOps.whisper_transcribe`                                                                                                                       |
| **Previous state** | The transcription workflow called `toolkit_UI_obj.notify_via_os(...)` when transcription started and finished.                                                 |
| **Current state**  | Processing emits `transcription.started` and `transcription.completed` events containing simple data. The Tk UI decides whether to display an OS notification. |
| **Behaviour note** | `transcription.completed` is emitted after the transcription output has been saved and the queue item has reached `done`.                                      |
| **Status**         | Resolved                                                                                                                                                       |
| **Commit**         | `9a6f1f05f1b7c0d4116e7027410a61a8a6f6467d`                                                                                                                     |

## C04 — Resolve operations receive and invoke a UI object

| Field                  | Detail                                                                                                                                                              |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Direction**          | Former processing -> UI                                                                                                                                             |
| **Location**           | Formerly `ToolkitOps.resolve_check_timeline` and `ToolkitOps.execute_resolve_operation`                                                                             |
| **Previous state**     | Resolve processing accepted `toolkit_UI_obj`, displayed message boxes, opened `AskDialog` and requested an output directory.                                        |
| **Current state**      | Resolve processing accepts plain values and returns plain result dictionaries. Marker selection, directory selection and error presentation are owned by the Tk UI. |
| **Remaining coupling** | Global Resolve state and direct Tk access to Resolve internals remain under C14.                                                                                     |
| **Status**             | Resolved for Tk processing-to-UI coupling                                                                                                                           |
| **Commit**             | `0de06f4bde23b8655bcf88cfb08fd65ccb0b1d0a`                                                                                                                          |

## C05 — `NotificationService` sends messages to live frontend objects

| Field                  | Detail                                                                                                                                         |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| **Direction**          | Former processing -> frontend objects                                                                                                          |
| **Location**           | Formerly `storytoolkitai/core/toolkit_ops/toolkit_ops.py`; now `storytoolkitai/ui/notifications.py`                                            |
| **Previous state**     | Notification classes inside the processing module stored live receiver objects and invoked `receive_notification(...)`.                        |
| **Current state**      | `NotificationService` and `NotificationMessage` are UI-owned helpers. Core processing no longer knows about notification receivers or windows. |
| **Remaining coupling** | None for the identified processing-to-UI dependency.                                                                                           |
| **Status**             | Resolved                                                                                                                                       |
| **Commit**             | `4473562f3d7a63c76109c39e3c7f74ab647e135d`                                                                                                     |

## C06 — Processing observers are live callback objects

| Field                  | Detail                                                                                                                                                                                       |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Direction**          | Former processing -> UI callback                                                                                                                                                             |
| **Location**           | Former core `Observer` class and `ToolkitOps.attach_observer`, `dettach_observer` and `notify_observers` implementation                                                                      |
| **Previous state**     | `ToolkitOps` stored live observer objects and invoked callbacks indirectly through `observer.update()`.                                                                                      |
| **Current state**      | Processing no longer stores UI callback objects. The transitional `notify_observers(action)` method emits an `action.triggered` engine event. Tk stores and schedules its callbacks locally. |
| **Remaining coupling** | Non-queue legacy workflows still use the implicit action-name event vocabulary. Queue lifecycle events no longer depend on `ToolkitOps.notify_observers(...)`.                               |
| **Status**             | Resolved for live processing-to-UI callbacks                                                                                                                                                 |
| **Commit**             | `3c9515dc094aba4a174a97d0a9aca13c7e45fe20`                                                                                                                                                   |

## C07 — Queue notifications use implicit action-name strings

| Field                  | Detail |
| ---------------------- | ------ |
| **Direction**          | Queue and legacy processing -> engine event -> UI |
| **Location**           | Queue lifecycle in `processing_queue.py`; transitional search-index completion code in `toolkit_ops.py`; engine-event handling in `toolkit_ui.py` |
| **Previous state**     | Queue addition, updates and completion used names such as `update_queue`, `update_queue_item`, `<item_type>_queue_item_done`, `<queue_id>_queue_item_done` and search-specific indexing action names. |
| **Current state**      | Queue additions and updates emit `job.changed`. Successful tasks emit `job.task_completed` containing the job ID, item type and completed task name. Advanced search now polls detached engine search state and no longer registers or consumes search-specific completion or failure action names. |
| **Remaining coupling** | `ToolkitOps.index_text`, `ToolkitOps.add_index_text_to_queue` and `ProcessingQueue._notify_on_stop_action` still contain the old search action-name compatibility path. No current Tk search workflow depends on it. Remove this unused path during the later compatibility cleanup after confirming that no external caller relies on it. Other non-queue workflows may still use `ToolkitOps.notify_observers(...)`. |
| **Status**             | Resolved for queue and advanced-search UI behavior; unused legacy compatibility code remains |
| **Related commits**    | `866d438`, `f97d0b3`, `ffef103`, `0df67f0`, `a576250`, `3ce19ad`, `e9684f2` |

## C08 — `ProcessingQueue` depends on the whole `ToolkitOps` object

| Field                  | Detail |
| ---------------------- | ------ |
| **Direction**          | Explicit construction data -> queue |
| **Location**           | `ProcessingQueue.__init__`, task dispatch and event publication in `processing_queue.py`; queue construction in `ToolkitOps.__init__` |
| **Previous state**     | The queue stored `toolkit_ops_obj`, read its `queue_tasks` mapping and called its transitional `notify_observers(...)` method. |
| **Current state**      | The queue receives only a task-handler dictionary and the shared `EventEmitter`. Task dispatch uses the supplied dictionary, and queue state changes are published directly through the emitter. |
| **Remaining coupling** | None for the complete `ToolkitOps` dependency. The unused `on_stop_action_name` compatibility field tracked under C07 does not give the queue access to `ToolkitOps`. |
| **Status**             | Resolved |
| **Commit**             | `ffef103` |

## C09 — UI reads and mutates queue implementation details

| Field                  | Detail                                                                                                                                                                                                                                                                                                      |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Direction**          | UI -> `StoryToolkitEngine` -> queue                                                                                                                                                                                                                                                                         |
| **Location**           | Queue windows, startup and shutdown handling, search queue checks and ingest workflows in `storytoolkitai/ui/toolkit_ui.py`                                                                                                                                                                                 |
| **Previous state**     | Tk read queue dictionaries, generated queue IDs, changed queue-item statuses and called queue cancellation methods directly.                                                                                                                                                                                |
| **Current state**      | Tk retrieves detached snapshots through `StoryToolkitEngine.list_jobs(...)` and `get_job(...)`. Cancellation, ingest placeholder creation, Resolve timeline placeholder creation, ingest status transitions and ingest submission go through `StoryToolkitEngine`.                                          |
| **Resolved scope**     | UI modules no longer call `get_all_queue_items(...)`, `get_item(...)`, `generate_queue_id(...)`, `add_to_queue(...)`, `update_queue_item(...)`, `update_status(...)`, `set_to_canceled(...)` or `cancel_item(...)` on `ProcessingQueue`. Architecture tests protect queue reads, cancellation and mutation. |
| **Remaining coupling** | Tk still calls other unmigrated `ToolkitOps` operations. Those broader bypasses remain under C01 and C19.                                                                                                                                                                                                   |
| **Status**             | Resolved for direct queue access                                                                                                                                                                                                                                                                            |
| **Related commits**    | `a3865d6`, `059909c`, `2a15029`, `fe95896`, `7c1babe`                                                                                                                                                                                                                                                       |

## C10 — Queue UI contains timing workarounds for observer races

| Field                  | Detail |
| ---------------------- | ------ |
| **Direction**          | Engine event -> UI snapshot refresh |
| **Location**           | Queue-window and advanced-search state handling in `storytoolkitai/ui/toolkit_ui.py` |
| **Previous state**     | Tk registered payload-free queue observers and read `ProcessingQueue` directly because jobs could change or finish before a listener was attached. Advanced search also registered window-specific completion and failure action names. |
| **Current state**      | The Tk application has one engine-event subscription. A `job.changed` event schedules a Queue-window refresh on the Tk event loop. `list_jobs(...)` and `get_job(...)` remain authoritative, and the Queue window retrieves a snapshot immediately after opening. Completed queue tasks emit `job.task_completed` with structured task information. Advanced search polls `StoryToolkitEngine.get_search(...)` and treats the detached search snapshot as authoritative. |
| **Behaviour note**     | Retrieving a snapshot after subscribing or while polling is the intended race-safe pattern. Events and polling ticks signal that state may have changed; they are not treated as the complete state themselves. |
| **Remaining coupling** | None for Queue-window refresh, normal queue-task completion or advanced-search preparation completion. |
| **Status**             | Resolved |
| **Related commits**    | `059909c`, `866d438`, `f97d0b3`, `0df67f0`, `a576250`, `3ce19ad` |

## C11 — UI directly constructs search engines and owns worker threads

| Field                  | Detail |
| ---------------------- | ------ |
| **Direction**          | UI -> `StoryToolkitEngine` -> search processing |
| **Location**           | Advanced-search code in `toolkit_ui.py`; search-session methods in `core/engine.py`; search construction in `core/toolkit_ops/toolkit_ops.py` |
| **Previous state**     | Tk constructed `TextSearch` and `VideoSearch`, retained those live processors in window state and callback arguments, prepared corpora, loaded indexes and models, started processing threads and invoked search methods directly. |
| **Current state**      | `StoryToolkitEngine` owns a private search-session registry containing the live text and video processors. The engine creates sessions, owns preparation workers, coordinates queued text indexing, loads models, executes text and video queries and returns detached search information and result data. Tk stores only `search_id` and remains responsible for file selection, window state, command parsing and result presentation. |
| **Accepted limit**     | `StoryToolkitEngine.get_search_video_frame(...)` returns the existing in-process image array used by Tk. This value is UI-independent but is not suitable for a network boundary. Version 2 must replace it with encoded bytes, an artifact path or another explicitly serializable shape. |
| **Remaining coupling** | None for live search-processor ownership or search worker ownership in Tk. The unused action-name compatibility code left in processing is tracked under C07. |
| **Status**             | Resolved for Version 1 |
| **Related commits**    | `9cfc6f5`, `a576250`, `e67b05f`, `537d032`, `3ce19ad`, `e9684f2` |

## C12 — Search classes receive the entire operations object

| Field                  | Detail |
| ---------------------- | ------ |
| **Direction**          | Explicit search configuration -> search processing |
| **Location**           | `SearchConfig`, `ToolkitSearch`, `SearchItem`, `TextSearch` and `VideoSearch` in `core/toolkit_ops/search.py`; configuration construction in `ToolkitOps.__init__` |
| **Previous state**     | Search objects received `toolkit_ops_obj` and derived settings, model state, the Torch device and application configuration from the complete operations object. |
| **Current state**      | Search processors receive a narrow, immutable `SearchConfig` containing the current Torch-device callback, semantic-model default, application-setting reader and configuration writer. Search code no longer stores `ToolkitOps` or `StoryToolkitAI`. |
| **Design note**        | The callbacks preserve current runtime settings without introducing a settings-provider interface, dependency-injection container or search factory framework. |
| **Remaining coupling** | None for the complete `ToolkitOps` dependency. Search still uses explicit settings callbacks owned by processing, which is appropriate for the in-process Version 1 architecture. |
| **Status**             | Resolved for Version 1 |
| **Related commits**    | `9f7e644`, `e9684f2` |

## C13 — Assistant inherits a hidden UI back-reference

| Field                  | Detail                                                                                                    |
| ---------------------- | --------------------------------------------------------------------------------------------------------- |
| **Direction**          | Former assistant processing -> UI                                                                         |
| **Location**           | `ToolkitAssistant.__init__`                                                                               |
| **Previous state**     | The assistant copied `toolkit_ops_obj.toolkit_UI_obj` into its own `toolkit_UI_obj` field.                |
| **Current state**      | The unused UI field has been removed.                                                                     |
| **Remaining coupling** | The assistant still receives the broad `ToolkitOps` object, but it no longer receives or stores UI state. |
| **Status**             | Resolved for the UI back-reference                                                                        |
| **Commit**             | `fdc93adc07f1c2177857da6300651b56fbb8eecb`                                                                |

## C14 — Resolve state is stored globally on `NLE`

| Field                  | Detail |
| ---------------------- | ------ |
| **Direction**          | Shared mutable state between processing and Tk UI |
| **Location**           | `NLE` in `toolkit_ops.py`; Resolve-related code in `toolkit_ui.py` and `menu.py` |
| **Current state**      | Class attributes hold the current Resolve project, timeline, markers, timecode, bin, connection and polling state. |
| **Improvement made**   | Resolve marker, connection, timeline-render and render-job operations are available through `StoryToolkitEngine`. The CLI no longer reads `NLE`, controls Resolve lifecycle or accesses `resolve_api` directly. |
| **Remaining coupling** | Tk code can still read global `NLE` or Resolve integration state directly. |
| **Status**             | Open |
| **Related commit**     | `201ca62b576adecec333c061c35977f5dd5bfa96` |

## C15 — Menu commands pass the UI object into processing

| Field                  | Detail                                                                                                                                            |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Direction**          | Former UI -> processing -> UI cycle                                                                                                               |
| **Location**           | Resolve handlers in `storytoolkitai/ui/menu.py` and related Tk controls                                                                           |
| **Previous state**     | UI handlers passed `toolkit_UI_obj` into a generic Resolve processing method.                                                                     |
| **Current state**      | UI handlers gather user input and call explicit engine methods with plain values. Resolve errors are converted into message boxes on the UI side. |
| **Remaining coupling** | None for the identified UI-object argument.                                                                                                       |
| **Status**             | Resolved                                                                                                                                          |
| **Commit**             | `0de06f4bde23b8655bcf88cfb08fd65ccb0b1d0a`                                                                                                        |

## C16 — CLI calls Resolve implementation details

| Field                  | Detail |
| ---------------------- | ------ |
| **Direction**          | Former CLI -> processing and integration internals |
| **Location**           | Resolve command handling in `storytoolkitai/ui/toolkit_cli.py`; public operations in `storytoolkitai/core/engine.py` |
| **Previous state**     | CLI code received `ToolkitOps` and `StoryToolkitAI`, enabled Resolve directly, polled `resolve_api` and invoked raw Resolve render methods. |
| **Current state**      | The CLI receives only `StoryToolkitEngine` for processing. It validates command-line input, asks the engine to establish a Resolve connection and invokes engine timeline-render or render-job operations. Processing owns connection waiting and raw Resolve calls. Results cross the boundary as plain dictionaries containing `ok` with optional `code`, `message` and `data`. |
| **Remaining coupling** | None for the CLI-to-Resolve implementation dependency. Global Resolve state still used by Tk is tracked separately under C14. |
| **Status**             | Resolved |
| **Commit**             | `201ca62b576adecec333c061c35977f5dd5bfa96` |

## C17 — Processing infers runtime mode from `sys.argv` and `cli_args`

| Field                  | Detail |
| ---------------------- | ------ |
| **Direction**          | Former startup mode -> implicit processing behaviour |
| **Location**           | `storytoolkitai/app.py`, `storytoolkitai/__main__.py`, `StoryToolkitAI.__init__` and `ToolkitOps.__init__` |
| **Previous state**     | `StoryToolkitAI` stored the complete argparse namespace. Processing inspected `cli_args`, `sys.argv` and `--noresolve` to decide update checks, API-key checks, Resolve initialization and queue restoration. |
| **Current state**      | `runtime_options_from_args(...)` converts parser values into an immutable `RuntimeOptions` object. `build_runtime(...)` passes explicit startup decisions into `StoryToolkitAI` and `ToolkitOps`. Neither object stores the argparse namespace or infers runtime mode from command-line flags. |
| **Boundary note**      | Uses of `sys.argv` that reproduce the current process command, locate packaged resources or construct an existing subprocess command are process mechanics, not runtime-mode inference, and are outside this coupling item. |
| **Remaining coupling** | None for ambient runtime-mode or `--noresolve` policy reads in processing construction. |
| **Status**             | Resolved |
| **Commit**             | `201ca62b576adecec333c061c35977f5dd5bfa96` |

## C18 — UI uses a wildcard import from the large operations module

| Field                  | Detail                                                                         |
| ---------------------- | ------------------------------------------------------------------------------ |
| **Direction**          | UI -> all exported processing names                                            |
| **Location**           | Import section of `storytoolkitai/ui/toolkit_ui.py`                            |
| **Current state**      | The UI still uses `from storytoolkitai.core.toolkit_ops.toolkit_ops import *`. |
| **Remaining coupling** | Processing dependencies are implicit and difficult to audit.                   |
| **Status**             | Open                                                                           |

## C19 — UI holds the application object, operations object and model objects broadly

| Field                  | Detail |
| ---------------------- | ------ |
| **Direction**          | UI -> broad internal object graph |
| **Location**           | Constructors and helpers throughout `toolkit_ui.py` |
| **Current state**      | The top-level Tk application stores `StoryToolkitEngine`, `ToolkitOps` and `StoryToolkitAI`. Many helpers also keep broad UI and processing object references. |
| **Improvement made**   | Transcription events, Resolve operations, queue inspection and cancellation, ingest lifecycle operations, advanced-search construction, search preparation, model loading and query execution now use the engine. Tk no longer stores live text or video search processors. |
| **Remaining coupling** | Most other legacy UI workflows can still bypass the engine through `ToolkitOps`. Direct queue access is resolved under C09, and advanced-search ownership is resolved under C11 and C12. |
| **Status**             | In progress |
| **Related commits**    | `9a6f1f05`, `0de06f4b`, `059909c`, `2a15029`, `7c1babe`, `3ce19ad`, `e9684f2` |

## C20 — UI directly creates, mutates and saves live project and content models

| Field                  | Detail                                                                                                 |
| ---------------------- | ------------------------------------------------------------------------------------------------------ |
| **Direction**          | UI -> model and storage behaviour                                                                      |
| **Location**           | Project, transcription, story and document workflows throughout `toolkit_ui.py`                        |
| **Current state**      | UI code constructs model objects and invokes methods that mutate, link, unlink and save them.          |
| **Accepted limit**     | UI-independent model objects may remain shared inside the same Python process during version 1.        |
| **Remaining coupling** | Creation, loading, saving and multi-object operations are not consistently exposed through the engine. |
| **Status**             | Accepted temporarily                                                                                   |

## C21 — `StoryToolkitAI` combines engine settings with launcher and UI state

| Field                  | Detail |
| ---------------------- | ------ |
| **Direction**          | Shared application object across startup, processing and Tk UI |
| **Location**           | `storytoolkitai/core/storytoolkitai.py::StoryToolkitAI`; construction in `storytoolkitai/app.py` |
| **Previous state**     | The object stored settings and application paths together with the complete command-line namespace, update lifecycle and values related to UI navigation. |
| **Current state**      | Command-line state has been removed. Startup now passes explicit booleans for debug mode, API-key checks and update checks. The object still combines settings, application paths, update lifecycle and values related to UI navigation. |
| **Improvement made**   | Runtime policy is explicit and testable without constructing or retaining argparse state. |
| **Remaining coupling** | Passing the complete object into `ToolkitOps` and Tk still hides which settings and lifecycle values each consumer actually needs. Decompose only where the remaining Tk migration or a concrete Version 2 requirement benefits from it. |
| **Status**             | In progress |
| **Related commit**     | `201ca62b576adecec333c061c35977f5dd5bfa96` |

## C22 — Operation dispatch and result values are inconsistent

| Field                  | Detail |
| ---------------------- | ------ |
| **Direction**          | Processing API ambiguity exposed to UI and queue |
| **Location**           | `ToolkitOps`, `ProcessingQueue.execute_item_tasks` and engine-facing operations |
| **Current state**      | Processing operations return a mixture of dictionaries, booleans, paths, lists, tuples and `None`. |
| **Improvement made**   | Engine queue methods return detached dictionaries. Resolve marker, connection, timeline-render and render-job operations use result dictionaries containing `ok` with optional `code`, `message` and `data`. Ingest lifecycle operations have explicit engine methods. Advanced-search session methods return detached dictionaries, text search returns a detached `(results, max_results)` tuple, and video search returns detached result dictionaries. |
| **Accepted limit**     | The in-process video-frame helper returns an image array for Tk rendering, as documented under C11. |
| **Remaining coupling** | Most legacy operations still have undocumented and inconsistent result shapes. Public engine results should be standardized only as each operation is migrated. |
| **Status**             | In progress |
| **Related commits**    | `89eabcf2`, `0de06f4b`, `7c1babe`, `9cfc6f5`, `e67b05f`, `537d032`, `201ca62` |

# Status summary

| ID  | Coupling                                      | Status |
| --- | --------------------------------------------- | ------ |
| C01 | Broad objects passed to UIs                   | In progress — CLI resolved; Tk remains |
| C02 | `ToolkitOps` stores Tk application            | Resolved |
| C03 | Transcription sends OS notifications          | Resolved |
| C04 | Resolve processing receives UI object         | Resolved for Tk coupling |
| C05 | Core notification service stores UI receivers | Resolved |
| C06 | Core stores live callback observers           | Resolved |
| C07 | Queue uses implicit action strings            | UI dependency resolved; unused compatibility code remains |
| C08 | Queue depends on complete `ToolkitOps`        | Resolved |
| C09 | UI accesses queue internals                   | Resolved for direct queue access |
| C10 | Queue and search timing workarounds           | Resolved |
| C11 | UI owns search objects and threads            | Resolved for Version 1 |
| C12 | Search receives complete `ToolkitOps`         | Resolved for Version 1 |
| C13 | Assistant stores UI reference                 | Resolved |
| C14 | Resolve state stored globally on `NLE`        | Open |
| C15 | Resolve menu passes UI into processing        | Resolved |
| C16 | CLI calls Resolve implementation details      | Resolved |
| C17 | Processing reads runtime arguments            | Resolved |
| C18 | UI wildcard-imports processing module         | Open |
| C19 | UI stores broad internal object graph         | In progress |
| C20 | UI mutates live content models                | Accepted temporarily |
| C21 | `StoryToolkitAI` mixes responsibilities       | In progress |
| C22 | Inconsistent operation result values          | In progress |

# Repeatable local audit

Run the following commands from the repository root.

Install `ripgrep` on macOS when needed:

```bash
brew install ripgrep
```

## Processing references to UI concepts

Expected result: no intentional matches under core or integrations.

```bash
rg -n --glob '*.py' \
  'toolkit_UI_obj|notify_via_os|notify_via_messagebox|AskDialog|ask_for_target_dir|receive_notification|NotificationService|NotificationMessage' \
  storytoolkitai/core \
  storytoolkitai/integrations
```

## Direct UI imports from processing

Expected result: no matches.

```bash
rg -n --glob '*.py' \
  '(^|[[:space:]])(from|import)[[:space:]]+storytoolkitai\.ui|from[[:space:]]+\.\.?ui' \
  storytoolkitai/core \
  storytoolkitai/integrations
```

## Removed live observer implementation

Expected result: no matches under core.

```bash
rg -n --glob '*.py' \
  'class Observer|attach_observer|dettach_observer|self\._observers' \
  storytoolkitai/core
```

## Transitional action-event bridge

Matches remain for non-queue legacy workflows and the now-unused search-index compatibility path.

Normal queue lifecycle, queue task completion and advanced-search UI behavior must not depend on this bridge.

```bash
rg -n --glob '*.py' \
  'notify_observers|action\.triggered|on_stop_action_name|add_observer_to_window|_notify_window_observers' \
  storytoolkitai
```

## Direct UI queue access

Expected result after Step 8: no matches.

```bash
rg -n --glob '*.py' \
  'processing_queue\.(get_all_queue_items|get_item|generate_queue_id|add_to_queue|update_queue_item|update_status|set_to_canceled|cancel_item)' \
  storytoolkitai/ui
```

## `ProcessingQueue` dependency on `ToolkitOps`

Expected result after Step 8: no matches.

```bash
rg -n --glob '*.py' \
  'toolkit_ops_obj|notify_observers' \
  storytoolkitai/core/toolkit_ops/processing_queue.py
```

## Queue task-completion callback names

Expected result in `processing_queue.py`: no matches.

Tk may still construct local callback names after receiving a structured `job.task_completed` event.

```bash
rg -n --glob '*.py' \
  '_queue_item_done' \
  storytoolkitai/core/toolkit_ops/processing_queue.py
```

## Explicit queue events

Expected matches in queue, event and Tk event-handling code.

```bash
rg -n --glob '*.py' \
  'job\.changed|job\.task_completed|create_job_task_completed_event' \
  storytoolkitai
```

## Legacy search action compatibility path

Expected result: matches may remain only in processing compatibility code. There must be no matching registration or handling in `storytoolkitai/ui`.

```bash
rg -n --glob '*.py' \
  'on_stop_action_name|update_(done|fail)_indexing_search_file_path' \
  storytoolkitai/core/toolkit_ops

rg -n --glob '*.py' \
  'on_stop_action_name|update_(done|fail)_indexing_search_file_path' \
  storytoolkitai/ui
```

The second command must return no matches. Remove the remaining processing-side compatibility path during the later legacy cleanup after confirming that no external caller uses it.

## Resolve globals and integration internals

Matches in Tk or core identify the remaining C14 global-state work. The CLI must not be among those callers.

```bash
rg -n --glob '*.py' \
  '\bNLE\.|resolve_api|resolve_enable|resolve_disable|poll_resolve|resolve_check_timeline' \
  storytoolkitai/ui/toolkit_ui.py \
  storytoolkitai/ui/menu.py \
  storytoolkitai/core
```

Expected result for the migrated CLI: no matches.

```bash
rg -n --glob '*.py' \
  'toolkit_ops_obj|stAI|\bNLE\.|resolve_api|resolve_enable|resolve_disable|poll_resolve' \
  storytoolkitai/ui/toolkit_cli.py
```

The removed generic Resolve operation should not appear:

```bash
rg -n --glob '*.py' \
  'execute_resolve_operation' \
  storytoolkitai
```

## Engine-owned advanced search

Expected result: no matches in Tk for live search processors or processing preparation calls.

```bash
rg -n --glob '*.py' \
  'text_search_item|video_search_item|TextSearch\(|VideoSearch\(|prepare_search_corpus|load_index_paths' \
  storytoolkitai/ui
```

Expected matches: engine search-session methods and narrow `SearchConfig` construction in processing code.

```bash
rg -n --glob '*.py' \
  'SearchConfig|create_search\(|prepare_search\(|search_text\(|search_video\(|get_search_video_frame' \
  storytoolkitai/core
```

The architecture checks for this boundary are in `tests/architecture/test_search_boundary.py`.

## Explicit runtime construction

Runtime-mode policy is now protected by an architecture test:

```bash
python -m pytest tests/architecture/test_runtime_boundary.py
```

Expected result for argparse-state storage: no matches.

```bash
rg -n --glob '*.py' \
  'cli_args' \
  storytoolkitai
```

Broad `sys.argv` searches may still find process-restart, packaged-resource or subprocess command construction. Those mechanics are not C17 regressions unless processing uses them to decide application mode, queue restoration, update checks, API-key checks or Resolve enablement.

## Wildcard processing import

Matches identify C18 work.

```bash
rg -n --glob '*.py' \
  'from storytoolkitai\.core\.toolkit_ops\.toolkit_ops import \*' \
  storytoolkitai/ui
```

## Broad engine bypasses in the UI

Matches identify C01, C14 and C19 work. The CLI has been removed from this bypass path.

Direct queue access should no longer be among the results.

```bash
rg -n --glob '*.py' \
  'toolkit_ops_obj\.|\.processing_queue|\.resolve_api|\bNLE\.' \
  storytoolkitai/ui
```

# Update rule

When a coupling is changed:

1. Update only the affected entry.
2. Record the commit that changed or resolved it.
3. Keep unresolved related coupling under its own existing entry.
4. Add a new entry only when the issue is materially different from C01–C22.

