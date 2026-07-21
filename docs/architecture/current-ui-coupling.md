# Current UI and processing coupling

**Status:** Temporary migration inventory for the StoryToolkitAI 1.0 architecture work
**Branch reviewed:** `dev`
**Reviewed:** 2026-07-21
**Related decision:** [`engine-ui-separation.md`](./engine-ui-separation.md)

Known behavior noticed during the migration is tracked in
[`known-refactor-issues.md`](./known-refactor-issues.md).

## Purpose

This document records where the current UI and processing code depend on each
other. It is a migration checklist, not a proposal for a large framework.

Its purpose is to keep the remaining coupling visible while StoryToolkitAI is
moved towards this dependency direction:

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

During the version 1 migration, some UI code may still reach into legacy
processing objects. Those remaining cases are tracked here until they are moved
behind `StoryToolkitEngine`.

## Status legend

* **Open** — the identified coupling is still present
* **In progress** — an engine-based path exists, but legacy access remains
* **Resolved** — the identified coupling no longer exists
* **Accepted temporarily** — deliberately retained for version 1 within stated
  limits

## Scope reviewed

The inventory covers the following areas:

```text
storytoolkitai/__main__.py
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

File and symbol names are used instead of fixed line numbers because the larger
source files change frequently.

# Current dependency picture

After the completed processing-to-UI separation work, the central relationship
looks approximately like this:

```text
__main__.py
    |
    +--> StoryToolkitAI
    |
    +--> ToolkitOps
    |       |
    |       +--> ProcessingQueue
    |       +--> ToolkitSearch
    |       +--> Resolve API
    |       +--> model and settings state
    |       |
    |       +--> EventEmitter
    |
    +--> StoryToolkitEngine
            |
            +--> selected ToolkitOps operations
            +--> copied queue snapshots
            +--> safe queue cancellation
            +--> event subscriptions
            +--> Resolve marker operations
                    |
                    v
                  Tk UI
                    |
                    +--> displays engine events
                    +--> owns dialogs and notifications
                    +--> owns window callbacks
                    +--> reads job state through the engine
                    +--> still accesses ToolkitOps directly for
                         unmigrated features
```

The direct processing-to-Tk back-reference has been removed.

The main remaining direction of coupling is:

```text
Tk UI / CLI -> ToolkitOps and processing internals
```

# Coupling inventory

## C01 — Application construction exposes broad internals to each UI

| Field                  | Detail                                                                                                                                                                                                                          |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Direction**          | Bootstrap -> UI and processing                                                                                                                                                                                                  |
| **Location**           | `storytoolkitai/__main__.py::main`, `storytoolkitai/ui/toolkit_ui.py::run_gui`, `storytoolkitai/ui/toolkit_cli.py::run_cli`                                                                                                     |
| **Current state**      | Startup constructs `StoryToolkitAI`, `ToolkitOps` and `StoryToolkitEngine`. The Tk application receives the engine but still also receives the application and operations objects. The CLI continues to use the legacy objects. |
| **Remaining coupling** | Both UIs can bypass the engine and call broad processing internals.                                                                                                                                                             |
| **Status**             | In progress                                                                                                                                                                                                                     |
| **Related commits**    | `89eabcf2c6ff3248e5c045f2bd40911d175f12d0`, `9a6f1f05f1b7c0d4116e7027410a61a8a6f6467d`                                                                                                                                          |

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
| **Remaining coupling** | Global Resolve state and direct UI access to Resolve internals remain under C14 and C16.                                                                            |
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
| **Remaining coupling** | The implicit action-name event vocabulary remains under C07.                                                                                                                                 |
| **Status**             | Resolved for live processing-to-UI callbacks                                                                                                                                                 |
| **Commit**             | `3c9515dc094aba4a174a97d0a9aca13c7e45fe20`                                                                                                                                                   |

## C07 — Queue notifications use implicit action-name strings

| Field                  | Detail                                                                                                                                                                                                |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Direction**          | Queue -> engine event -> UI                                                                                                                                                                           |
| **Location**           | Queue addition, update and completion paths in `processing_queue.py`; `ToolkitOps.notify_observers`; engine-event handling in `toolkit_ui.py`                                                         |
| **Previous state**     | Queue-window refresh depended on action names such as `update_queue` and `update_queue_item`, without event data identifying the changed job.                                                         |
| **Current state**      | Queue additions and updates emit a neutral `job.changed` event containing stable summary fields. The Queue window listens for that event and retrieves a fresh snapshot through `StoryToolkitEngine`. |
| **Remaining coupling** | Queue code still publishes transitional action names for other legacy workflows, including queue-item completion names and arbitrary `on_stop_action_name` values.                                    |
| **Status**             | In progress                                                                                                                                                                                           |
| **Related commits**    | `866d438`, `f97d0b3`, `3c9515dc094aba4a174a97d0a9aca13c7e45fe20`                                                                                                                                      |

## C08 — `ProcessingQueue` depends on the whole `ToolkitOps` object

| Field                  | Detail                                                                                                                         |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **Direction**          | Queue -> operations object                                                                                                     |
| **Location**           | `ProcessingQueue.__init__`, task dispatch and event publication in `processing_queue.py`                                       |
| **Current state**      | The queue stores `toolkit_ops_obj`, reads its `queue_tasks` mapping and calls its transitional `notify_observers(...)` method. |
| **Remaining coupling** | The queue depends on much more state than its task mapping and event publisher require.                                        |
| **Status**             | Open                                                                                                                           |

## C09 — UI reads and mutates queue implementation details

| Field                  | Detail                                                                                                                                                                                                                                                                                                                                  |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Direction**          | UI -> engine, with remaining UI -> queue writes                                                                                                                                                                                                                                                                                         |
| **Location**           | Queue windows, application startup, shutdown handling, search queue checks and queue-submission workflows in `storytoolkitai/ui/toolkit_ui.py`                                                                                                                                                                                          |
| **Previous state**     | Tk read raw queue dictionaries through `ProcessingQueue`, called queue cancellation methods directly and used queue implementation methods for startup, shutdown and search checks.                                                                                                                                                     |
| **Current state**      | Tk retrieves detached job snapshots through `StoryToolkitEngine.list_jobs(...)` and `get_job(...)`. Cancellation uses `StoryToolkitEngine.cancel_job(...)`, preserving safe cancellation for queued and running jobs. Queue-window rendering, startup checks, shutdown checks and search queue reads no longer inspect queue internals. |
| **Resolved scope**     | Direct calls to `get_all_queue_items(...)`, `get_item(...)`, `set_to_canceled(...)` and `cancel_item(...)` have been removed from the UI. An architecture test protects this boundary.                                                                                                                                                  |
| **Remaining coupling** | Five direct queue write/submission calls remain: three `update_queue_item(...)` calls and two `generate_queue_id(...)` calls. They belong to user-interaction and ingest/transcription workflows and will be migrated with the operations that own those workflows.                                                                     |
| **Status**             | In progress                                                                                                                                                                                                                                                                                                                             |
| **Related commits**    | `a3865d6`, `059909c`, `153eebc`, `2a15029`, `fe9589618d668cc34de792e017e1c9244485f2f7`                                                                                                                                                                                                                                                  |

## C10 — Queue UI contains timing workarounds for observer races

| Field                  | Detail                                                                                                                                                                                                                                                            |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Direction**          | Engine event -> UI snapshot refresh                                                                                                                                                                                                                               |
| **Location**           | Queue-window event handling and search completion checks in `storytoolkitai/ui/toolkit_ui.py`                                                                                                                                                                     |
| **Previous state**     | Tk registered payload-free queue observers and read `ProcessingQueue` directly because jobs could change or finish before a listener was attached.                                                                                                                |
| **Current state**      | The Tk application has one engine-event subscription. A `job.changed` event schedules a Queue-window refresh on the Tk event loop. `list_jobs(...)` and `get_job(...)` remain authoritative, and the Queue window retrieves a snapshot immediately after opening. |
| **Behaviour note**     | Retrieving a snapshot after subscribing is the intended race-safe pattern. Events signal that state changed; they are not treated as the state itself.                                                                                                            |
| **Remaining coupling** | The advanced-search workflow still uses its existing window-specific completion action. The search workflow itself remains tracked under C11 and C12.                                                                                                             |
| **Status**             | Resolved for Queue-window refresh and direct queue rechecks                                                                                                                                                                                                       |
| **Related commits**    | `059909c`, `866d438`, `f97d0b3`                                                                                                                                                                                                                                   |

## C11 — UI directly constructs search engines and owns worker threads

| Field                  | Detail                                                                                                              |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------- |
| **Direction**          | UI -> processing implementation                                                                                     |
| **Location**           | Advanced search code in `toolkit_ui.py`; search classes in `core/toolkit_ops/search.py`                             |
| **Current state**      | UI code constructs text and video search objects, calls loading and indexing methods and starts processing threads. |
| **Remaining coupling** | Model ownership, worker execution and presentation are mixed inside Tk workflows.                                   |
| **Status**             | Open                                                                                                                |

## C12 — Search classes receive the entire operations object

| Field                  | Detail                                                                                                            |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **Direction**          | Search processing -> broad application state                                                                      |
| **Location**           | Search constructors and helpers in `core/toolkit_ops/search.py`                                                   |
| **Current state**      | Search objects receive `toolkit_ops_obj` and derive settings, model state, devices and application state from it. |
| **Remaining coupling** | The actual requirements of the search implementation are hidden behind the broad operations object.               |
| **Status**             | Open                                                                                                              |

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

| Field                  | Detail                                                                                                             |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **Direction**          | Shared mutable state between processing and UI                                                                     |
| **Location**           | `NLE` in `toolkit_ops.py`; Resolve-related code in `toolkit_ui.py`, `menu.py` and `toolkit_cli.py`                 |
| **Current state**      | Class attributes hold the current Resolve project, timeline, markers, timecode, bin, connection and polling state. |
| **Improvement made**   | Resolve marker operations are available through `StoryToolkitEngine`.                                              |
| **Remaining coupling** | UI and CLI code can still read global `NLE` or Resolve integration state directly.                                 |
| **Status**             | Open                                                                                                               |

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

| Field                  | Detail                                                                                                     |
| ---------------------- | ---------------------------------------------------------------------------------------------------------- |
| **Direction**          | CLI -> processing and integration internals                                                                |
| **Location**           | Resolve command handling in `storytoolkitai/ui/toolkit_cli.py`                                             |
| **Current state**      | CLI code still receives `ToolkitOps`, controls Resolve lifecycle and calls `resolve_api` methods directly. |
| **Improvement made**   | Engine methods now exist for marker copy and render operations.                                            |
| **Remaining coupling** | The CLI has not been migrated to those methods and still knows integration lifecycle details.              |
| **Status**             | Open                                                                                                       |

## C17 — Processing infers runtime mode from `sys.argv` and `cli_args`

| Field                  | Detail                                                                                                                       |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **Direction**          | Startup mode -> processing behaviour                                                                                         |
| **Location**           | `ToolkitOps.__init__`, `StoryToolkitAI` state and Resolve helper launch paths                                                |
| **Current state**      | Processing checks command-line state to decide Resolve initialization, queue resume behaviour and some subprocess workflows. |
| **Remaining coupling** | The engine cannot be constructed with explicit runtime options independently of the host process arguments.                  |
| **Status**             | Open                                                                                                                         |

## C18 — UI uses a wildcard import from the large operations module

| Field                  | Detail                                                                         |
| ---------------------- | ------------------------------------------------------------------------------ |
| **Direction**          | UI -> all exported processing names                                            |
| **Location**           | Import section of `storytoolkitai/ui/toolkit_ui.py`                            |
| **Current state**      | The UI still uses `from storytoolkitai.core.toolkit_ops.toolkit_ops import *`. |
| **Remaining coupling** | Processing dependencies are implicit and difficult to audit.                   |
| **Status**             | Open                                                                           |

## C19 — UI holds the application object, operations object and model objects broadly

| Field                  | Detail                                                                                                                                                         |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Direction**          | UI -> broad internal object graph                                                                                                                              |
| **Location**           | Constructors and helpers throughout `toolkit_ui.py`                                                                                                            |
| **Current state**      | The top-level Tk application stores `StoryToolkitEngine`, `ToolkitOps` and `StoryToolkitAI`. Many helpers also keep broad UI and processing object references. |
| **Improvement made**   | Transcription events, Resolve operations and queue inspection/cancellation use the engine.                                                                     |
| **Remaining coupling** | Most legacy UI workflows can still bypass the engine. Direct queue submission and state-update calls remain until their owning operations are migrated.        |
| **Status**             | In progress                                                                                                                                                    |
| **Related commits**    | `9a6f1f05f1b7c0d4116e7027410a61a8a6f6467d`, `0de06f4bde23b8655bcf88cfb08fd65ccb0b1d0a`, `059909c`, `153eebc`, `2a15029`                                        |

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

| Field                  | Detail                                                                                                                                   |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| **Direction**          | Shared application object across startup, processing and UI                                                                              |
| **Location**           | `storytoolkitai/core/storytoolkitai.py::StoryToolkitAI`                                                                                  |
| **Current state**      | The object stores settings and application paths together with command-line state, update lifecycle and values related to UI navigation. |
| **Remaining coupling** | Passing the complete object into processing hides which configuration values are actually required.                                      |
| **Status**             | Open                                                                                                                                     |

## C22 — Operation dispatch and result values are inconsistent

| Field                  | Detail                                                                                                                                                        |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Direction**          | Processing API ambiguity exposed to UI and queue                                                                                                              |
| **Location**           | `ToolkitOps`, `ProcessingQueue.execute_item_tasks` and engine-facing operations                                                                               |
| **Current state**      | Processing operations return a mixture of dictionaries, booleans, paths and `None`.                                                                           |
| **Improvement made**   | Engine queue methods return detached dictionaries, and Resolve operations use result dictionaries containing `ok` with optional `code`, `message` and `data`. |
| **Remaining coupling** | Most legacy operations still have undocumented and inconsistent result shapes.                                                                                |
| **Status**             | In progress                                                                                                                                                   |
| **Related commits**    | `89eabcf2c6ff3248e5c045f2bd40911d175f12d0`, `0de06f4bde23b8655bcf88cfb08fd65ccb0b1d0a`                                                                        |

# Status summary

| ID  | Coupling                                      | Status                                       |
| --- | --------------------------------------------- | -------------------------------------------- |
| C01 | Broad objects passed to UIs                   | In progress                                  |
| C02 | `ToolkitOps` stores Tk application            | Resolved                                     |
| C03 | Transcription sends OS notifications          | Resolved                                     |
| C04 | Resolve processing receives UI object         | Resolved for Tk coupling                     |
| C05 | Core notification service stores UI receivers | Resolved                                     |
| C06 | Core stores live callback observers           | Resolved                                     |
| C07 | Queue uses implicit action strings            | In progress                                  |
| C08 | Queue depends on complete `ToolkitOps`        | Open                                         |
| C09 | UI accesses queue internals                   | In progress; reads and cancellation resolved |
| C10 | Queue event timing workarounds                | Resolved for Queue-window refresh            |
| C11 | UI owns search objects and threads            | Open                                         |
| C12 | Search receives complete `ToolkitOps`         | Open                                         |
| C13 | Assistant stores UI reference                 | Resolved                                     |
| C14 | Resolve state stored globally on `NLE`        | Open                                         |
| C15 | Resolve menu passes UI into processing        | Resolved                                     |
| C16 | CLI calls Resolve implementation details      | Open                                         |
| C17 | Processing reads runtime arguments            | Open                                         |
| C18 | UI wildcard-imports processing module         | Open                                         |
| C19 | UI stores broad internal object graph         | In progress                                  |
| C20 | UI mutates live content models                | Accepted temporarily                         |
| C21 | `StoryToolkitAI` mixes responsibilities       | Open                                         |
| C22 | Inconsistent operation result values          | In progress                                  |

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

Matches are expected until C07 and C08 are resolved.

```bash
rg -n --glob '*.py' \
  'notify_observers|action\.triggered|on_stop_action_name|add_observer_to_window|_notify_window_observers' \
  storytoolkitai
```

## UI queue inspection and cancellation

Expected result after Step 7: no matches.

```bash
rg -n --glob '*.py' \
  'processing_queue\.(get_all_queue_items|get_item|set_to_canceled|cancel_item)' \
  storytoolkitai/ui
```

## Remaining direct UI queue writes

Expected result at the current migration stage: five matches in
`storytoolkitai/ui/toolkit_ui.py`.

These writes will be migrated with their owning user-interaction,
ingest/transcription and search workflows rather than as part of Queue-window
presentation.

```bash
rg -n --glob '*.py' \
  'processing_queue\.(generate_queue_id|add_to_queue|update_queue_item)' \
  storytoolkitai/ui
```

Current expected calls:

```text
update_queue_item(...)
update_queue_item(...)
generate_queue_id(...)
generate_queue_id(...)
update_queue_item(...)
```

## Resolve globals and integration internals

Matches identify C14 and C16 work.

```bash
rg -n --glob '*.py' \
  '\bNLE\.|resolve_api|resolve_enable|resolve_disable|poll_resolve|resolve_check_timeline' \
  storytoolkitai/ui \
  storytoolkitai/core
```

The removed generic Resolve operation should not appear:

```bash
rg -n --glob '*.py' \
  'execute_resolve_operation' \
  storytoolkitai
```

## UI-owned search objects and worker threads

Matches identify C11 and C12 work.

```bash
rg -n --glob '*.py' \
  'TextSearch\(|VideoSearch\(|ToolkitSearch\(|Thread\(|index_text|index_video' \
  storytoolkitai/ui \
  storytoolkitai/core/toolkit_ops/search.py
```

## Ambient runtime-mode reads

Matches identify C17 work.

```bash
rg -n --glob '*.py' \
  'sys\.argv|cli_args|--noresolve|--mode.?cli|subprocess\.(Popen|run)' \
  storytoolkitai/core \
  storytoolkitai/integrations
```

## Wildcard processing import

Matches identify C18 work.

```bash
rg -n --glob '*.py' \
  'from storytoolkitai\.core\.toolkit_ops\.toolkit_ops import \*' \
  storytoolkitai/ui
```

## Broad engine bypasses in the UI

Matches identify C01, C09, C14, C16 and C19 work.

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

