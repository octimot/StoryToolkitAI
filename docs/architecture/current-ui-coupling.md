# Current UI and processing coupling

**Status:** Temporary migration inventory for the StoryToolkitAI 1.0 architecture work  
**Branch reviewed:** `dev`  
**Reviewed:** 2026-07-20  
**Related decision:** [`engine-ui-separation.md`](./engine-ui-separation.md)

## Purpose

This document records where the current UI and processing code depend on each
other.

It is a migration checklist, not a proposal for a large framework. Its purpose
is to help us remove the dependencies that prevent StoryToolkitAI from running
its processing code without Tkinter, while preserving current behaviour and
file formats for version 1.

The intended version 1 direction is:

```text
Tkinter UI / CLI
        |
        v
StoryToolkitEngine
        |
        v
Processing, storage, models and integrations
```

The important rule is one-way dependency:

```text
UI -> Engine -> processing
```

Processing must not call back into a UI object.

## How to use this document

Each inventory entry has an ID such as `C01`. When a coupling point is removed:

1. Add or confirm the required characterization test.
2. Make the smallest change that removes the coupling.
3. Update the entry's status and note the commit.
4. Keep the public behaviour unchanged unless a deliberate change is recorded.

The source positions below use file and symbol names rather than fixed line
numbers. The current large source files change line numbers frequently, while
symbols provide more stable anchors. The audit commands near the end of this
document print exact line numbers for the current checkout.

## Scope reviewed

The review covered the following areas on the `dev` branch:

```text
storytoolkitai/__main__.py
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
storytoolkitai/ui/toolkit_ui.py
storytoolkitai/ui/toolkit_cli.py
storytoolkitai/ui/menu.py
```

This is a source-level assessment. Dynamic Python behaviour can hide
relationships from a static review, so the local audit script and import guard
should be run in the real checkout before Step 3 is marked complete.

## Classification

### Must remove for version 1

These prevent a real UI-independent engine even while everything still runs in
one process:

- processing storing or receiving live UI objects;
- processing opening dialogs or issuing desktop notifications;
- processing invoking Tk callbacks;
- UI reading or mutating private queue and integration state;
- startup mode being inferred inside processing from `sys.argv`;
- wildcard imports that make the public boundary impossible to see.

### Must contain for version 1; full process-safe design may wait for version 2

These are acceptable temporarily if they remain UI-independent and are exposed
through a clear engine method:

- passing live `Project`, `Transcription`, `Story` and `Document` objects inside
  the same Python process;
- existing model instance caches;
- existing file-based queue persistence;
- existing processing functions and stateful classes;
- returning simple dictionaries where replacing them immediately would create
  unnecessary churn.

These choices should not become the network API for version 2, but they do not
all need to be redesigned before the version 1 internal boundary is complete.

### Correctly owned by the UI

The following are not problems when they stay entirely on the UI side:

- `messagebox` and other Tk dialogs;
- native file and folder selection;
- desktop notifications;
- `window.after(...)` and Tk thread hand-off;
- window state, layout and themes;
- deciding how an engine warning or event is presented.

The problem is not that these features exist. The problem is processing code
calling them or requiring their objects.

# Current dependency picture

The central relationship currently looks approximately like this:

```text
__main__.py
   |
   +--> StoryToolkitAI ------------------------+
   |                                           |
   +--> ToolkitOps ----------------------+      |
   |       |                            |      |
   |       +--> ProcessingQueue         |      |
   |       +--> ToolkitSearch           |      |
   |       +--> Resolve API             |      |
   |       +--> model/settings state    |      |
   |       +--> observers               |      |
   |       +--> toolkit_UI_obj <--------+------+--- Tk UI
   |                                                   |
   +---------------------------------------------------+
                  Tk UI also reaches into queue,
                  search, Resolve and model internals
```

The coupling is mostly through live objects and callbacks rather than obvious
`core -> ui` imports. That makes it easy to overlook during normal maintenance.

# Coupling inventory

## C01 — Application construction exposes all internals to each UI

| Field | Detail |
|---|---|
| **Direction** | Bootstrap -> UI and processing |
| **Location** | `storytoolkitai/__main__.py::main` |
| **Current behaviour** | Startup constructs `StoryToolkitAI` and `ToolkitOps`, then passes both objects directly to `run_gui(...)` or `run_cli(...)`. |
| **Why it matters** | Each UI receives the application object and the large operations object, so there is no small public processing boundary. |
| **Version 1 treatment** | Add `StoryToolkitEngine` and pass the engine to each UI. Construction of legacy objects may remain inside an engine factory during migration. |
| **Tests needed first** | Headless construction smoke test; current argument parsing/startup characterization. |
| **Priority** | High; foundation for Step 4. |
| **Status** | Open. |

## C02 — `ToolkitOps` stores the live Tk application

| Field | Detail |
|---|---|
| **Direction** | Processing <-> UI cycle |
| **Location** | `storytoolkitai/core/toolkit_ops/toolkit_ops.py::ToolkitOps.__init__`; `storytoolkitai/ui/toolkit_ui.py::run_gui` |
| **Current behaviour** | `ToolkitOps` declares `self.toolkit_UI_obj = None`; `run_gui(...)` assigns the created Tk application back to that field. |
| **Why it matters** | The UI owns `ToolkitOps`, and `ToolkitOps` owns the UI. Processing therefore cannot exist independently and can call arbitrary UI behaviour. |
| **Version 1 treatment** | Remove the back-reference. Pass only an event emitter and explicit settings/resources required by processing. |
| **Tests needed first** | Tk startup smoke test; transcription start/finish notification characterization. |
| **Priority** | Critical. |
| **Status** | Open. |

## C03 — Transcription processing issues OS notifications directly

| Field | Detail |
|---|---|
| **Direction** | Processing -> UI |
| **Location** | `storytoolkitai/core/toolkit_ops/toolkit_ops.py::ToolkitOps.whisper_transcribe` |
| **Current behaviour** | The transcription workflow calls `self.toolkit_UI_obj.notify_via_os(...)` when transcription starts and finishes. |
| **Why it matters** | A headless engine should report a state change, not decide that it becomes a desktop notification. |
| **Version 1 treatment** | Emit simple `job.started` and `job.completed` events. The Tk UI subscribes and optionally displays an OS notification. Logging remains in processing. |
| **Tests needed first** | Mocked transcription success, failure and cancellation tests; assert queue statuses and emitted events. |
| **Priority** | Critical; good first vertical refactor. |
| **Status** | Open. |

## C04 — Resolve operations receive and invoke a UI object

| Field | Detail |
|---|---|
| **Direction** | Processing -> UI |
| **Location** | `ToolkitOps.resolve_check_timeline`; `ToolkitOps.execute_resolve_operation` in `storytoolkitai/core/toolkit_ops/toolkit_ops.py` |
| **Current behaviour** | Resolve methods accept `toolkit_UI_obj`, display message boxes, instantiate `AskDialog`, access the Tk root and call `ask_for_target_dir()`. |
| **Why it matters** | Validation, user choices, presentation and Resolve API work are combined in one workflow. This is the strongest direct UI dependency in processing. |
| **Version 1 treatment** | Split each interaction into two stages: (1) UI gathers choices; (2) engine receives plain arguments and performs the operation. Return or raise plain errors such as `timeline_unavailable`, `bin_unavailable` and `marker_filter_invalid`. |
| **Tests needed first** | Characterize timeline unavailable, no bin clips, no markers, invalid marker color, cancelled target selection and successful render/copy operations using a fake Resolve API. |
| **Priority** | Critical but risky; address after the event and engine foundations. |
| **Status** | Open. |

## C05 — `NotificationService` sends messages to live frontend objects

| Field | Detail |
|---|---|
| **Direction** | Processing -> arbitrary receiver objects |
| **Location** | `NotificationService` in `storytoolkitai/core/toolkit_ops/toolkit_ops.py` |
| **Current behaviour** | A receiver type named `window` stores an object expected to implement `receive_notification(...)`; `_process_message(...)` invokes that method directly. |
| **Why it matters** | The notification cannot be serialized, replayed or sent to a CLI/web/Tauri client. It also embeds the concept of a UI window in core processing. |
| **Version 1 treatment** | Keep logging separate. Replace live receivers with a small event emitter that publishes plain `EngineEvent` values. UI code converts notification events into message boxes or status messages. |
| **Tests needed first** | Existing notification logging behaviour; UI handling of warning/error messages. |
| **Priority** | High. |
| **Status** | Open. |

## C06 — Processing observers are live callback objects

| Field | Detail |
|---|---|
| **Direction** | Processing -> UI callback |
| **Location** | `ToolkitOps.attach_observer`, `ToolkitOps.dettach_observer`, `ToolkitOps.notify_observers`; `toolkit_UI.add_observer_to_window` |
| **Current behaviour** | `ToolkitOps` stores observer objects and calls `observer.update()`. The UI replaces `update` with a callback wrapper that schedules work through `window.after(...)`. |
| **Why it matters** | The observer is a live Tk-aware object. Action strings are implicit, payload-free and difficult to document. The mechanism cannot cross a process boundary. |
| **Version 1 treatment** | Introduce one small event emitter. Publish `EngineEvent(type, data)` values. Keep Tk thread hand-off inside the UI listener. Preserve a temporary observer adapter if needed during migration. |
| **Tests needed first** | Queue update, queue-item completion and on-stop observer behaviour. |
| **Priority** | Critical; event foundation. |
| **Status** | Open. |

## C07 — Queue notifications use implicit action-name strings

| Field | Detail |
|---|---|
| **Direction** | Queue -> `ToolkitOps` observers -> UI |
| **Location** | `ProcessingQueue.execute_item_tasks`, `_notify_on_stop_observer`, queue update methods in `processing_queue.py` |
| **Current behaviour** | The queue calls `toolkit_ops_obj.notify_observers(...)` with values including `update_queue`, `<item_type>_queue_item_done`, `<queue_id>_queue_item_done` and arbitrary `on_stop_action_name`. |
| **Why it matters** | Event meaning is encoded in string construction, and listeners often need to re-read mutable queue state to discover what changed. |
| **Version 1 treatment** | Define a small initial event vocabulary with payloads: `job.added`, `job.updated`, `job.completed`, `job.failed`, `job.cancelled`, and any named workflow completion still required. Include at least `job_id`, `status` and `item_type`. |
| **Tests needed first** | Queue lifecycle tests covering addition, progress/status update, completion, failure and cancellation. |
| **Priority** | Critical. |
| **Status** | Open. |

## C08 — `ProcessingQueue` depends on the whole `ToolkitOps` object

| Field | Detail |
|---|---|
| **Direction** | Queue -> operations object |
| **Location** | `ProcessingQueue.__init__`, task dispatch and notification calls in `processing_queue.py`; `ToolkitOps.queue_tasks` |
| **Current behaviour** | The queue stores `toolkit_ops_obj`, reads its `queue_tasks` dictionary of bound methods and calls its observer methods. |
| **Why it matters** | The queue cannot be constructed or tested independently, and its dependency includes far more state than it needs. |
| **Version 1 treatment** | Do not create a complex scheduler abstraction. Pass two explicit dependencies: a task mapping and an event-emitting callable/object. A temporary compatibility constructor may accept `ToolkitOps` while callers are migrated. |
| **Tests needed first** | Queue task dispatch; missing task; task success/failure; dependency propagation; resume from file. |
| **Priority** | High. |
| **Status** | Open. |

## C09 — UI reads and mutates queue implementation details

| Field | Detail |
|---|---|
| **Direction** | UI -> processing internals |
| **Location** | Queue and shutdown code in `storytoolkitai/ui/toolkit_ui.py` |
| **Current behaviour** | UI code calls methods directly on `toolkit_ops_obj.processing_queue`, retrieves raw queue dictionaries and uses/mutates fields such as status, name and progress. It also calls cancellation methods on the queue implementation. |
| **Why it matters** | Queue storage and representation cannot change without editing UI code. Mutable dictionaries allow accidental state changes outside the queue. |
| **Version 1 treatment** | Add engine methods `list_jobs()`, `get_job(job_id)`, `cancel_job(job_id)` and later `retry_job(job_id)`. Return a `JobInfo` dataclass or a copied plain dictionary, never the queue's stored dictionary. |
| **Tests needed first** | Characterize queue window sorting/filtering fields and application shutdown checks for active jobs. |
| **Priority** | Critical. |
| **Status** | Open. |

## C10 — Queue UI contains timing workarounds for observer races

| Field | Detail |
|---|---|
| **Direction** | UI compensates for processing event timing |
| **Location** | Queue-window observer registration/update code in `toolkit_ui.py` |
| **Current behaviour** | UI code re-checks queue status after registering observers because a job may finish before the listener is attached. |
| **Why it matters** | Events alone are being treated as authoritative state, but they are not replayed. A UI can miss a transition. |
| **Version 1 treatment** | Make job snapshots authoritative and events advisory: subscribe, then call `get_job`/`list_jobs`; on any event, refresh the affected snapshot. This avoids building durable event replay in version 1. |
| **Tests needed first** | Job that completes immediately; queue window opened after completion; listener attached during completion. |
| **Priority** | High. |
| **Status** | Open. |

## C11 — UI directly constructs search engines and owns worker threads

| Field | Detail |
|---|---|
| **Direction** | UI -> processing implementation |
| **Location** | Advanced search code in `toolkit_ui.py`; `TextSearch`, `VideoSearch` and `ToolkitSearch` in `core/toolkit_ops/search.py` |
| **Current behaviour** | UI code instantiates text/video search objects, calls loading/indexing methods, accesses search-related settings/state through `ToolkitOps`, and starts processing threads itself. Search classes receive the entire `ToolkitOps` object. |
| **Why it matters** | Model/resource ownership, thread ownership and presentation are mixed. A future second UI could load duplicate models or implement different threading behaviour. |
| **Version 1 treatment** | Add engine operations such as `search_text(...)`, `search_video(...)`, `prepare_search(...)` and `start_indexing(...)`. Engine/processing owns worker execution and model state. UI owns only display and cancellation controls. Avoid redesigning search result models unless needed. |
| **Tests needed first** | Text search with fake embeddings/index; video search with fake index; filtered file paths; search cancellation/error; index-not-ready behaviour. |
| **Priority** | High; major extraction after queue foundation. |
| **Status** | Open. |

## C12 — Search classes receive the entire operations object

| Field | Detail |
|---|---|
| **Direction** | Search processing -> global application state |
| **Location** | Constructors and helper methods in `core/toolkit_ops/search.py` |
| **Current behaviour** | Search objects derive settings, model/device state and the application object through `toolkit_ops_obj`; global instance caching is also used. |
| **Why it matters** | The true requirements of search code are hidden, and tests must construct a large object graph. |
| **Version 1 treatment** | Replace the broad argument gradually with the actual values needed: settings access, model/device selection and an event/progress callback. Do not introduce interfaces for each value. Plain constructor arguments are sufficient. |
| **Tests needed first** | Constructor/settings behaviour and model cache reuse. |
| **Priority** | Medium-high. |
| **Status** | Open. |

## C13 — Assistant inherits a hidden UI back-reference

| Field | Detail |
|---|---|
| **Direction** | Assistant processing -> UI/global operations state |
| **Location** | `ToolkitAssistant.__init__` and assistant handlers in `core/toolkit_ops/assistant.py` |
| **Current behaviour** | The assistant stores `toolkit_ops_obj`, derives `stAI`, and copies `toolkit_ops_obj.toolkit_UI_obj`. |
| **Why it matters** | Even if the UI field is currently rarely or never used, it propagates the circular dependency and obscures the assistant's real configuration needs. |
| **Version 1 treatment** | Remove the UI field first. Pass only the application settings/provider data and callbacks actually used. Keep assistant behaviour otherwise unchanged. |
| **Tests needed first** | Assistant initialization with fake settings/provider; response/error handling. |
| **Priority** | Medium; likely a small early cleanup after tests. |
| **Status** | Open. |

## C14 — Resolve state is stored globally on `NLE`

| Field | Detail |
|---|---|
| **Direction** | Shared mutable state between processing and UI |
| **Location** | `NLE` class in `toolkit_ops.py`; Resolve/menu code in `ui/menu.py` and `ui/toolkit_ui.py` |
| **Current behaviour** | Class attributes hold current project, timeline, markers, timecode, bin, Resolve connection and polling flags. UI reads those attributes directly. |
| **Why it matters** | State changes are hidden, tests leak state, and a future process/client cannot inspect Python class attributes. |
| **Version 1 treatment** | Keep `NLE` internally if replacing it now would be too disruptive, but expose snapshots through engine methods such as `get_resolve_status()` and `get_resolve_context()`. UI must stop importing/reading `NLE` directly. Emit a `resolve.changed` event when the snapshot changes. |
| **Tests needed first** | Connect/disconnect, project/timeline change and no-timeline states using fake Resolve data. Reset global `NLE` state between tests. |
| **Priority** | High. |
| **Status** | Open. |

## C15 — Menu commands pass the UI object into processing

| Field | Detail |
|---|---|
| **Direction** | UI -> processing, followed by processing -> UI |
| **Location** | Resolve menu command handlers in `storytoolkitai/ui/menu.py` |
| **Current behaviour** | Menu handlers call `execute_resolve_operation(...)` and pass `self.toolkit_UI_obj`. |
| **Why it matters** | The public operation requires a concrete Tk application rather than operation arguments. |
| **Version 1 treatment** | Move all prompts before the engine call. Call explicit engine methods with plain values. Prefer operation-specific names over a single stringly typed `execute_resolve_operation`. |
| **Tests needed first** | Menu command argument construction; engine operation tests are covered by C04. |
| **Priority** | High, paired with C04. |
| **Status** | Open. |

## C16 — CLI calls Resolve implementation details

| Field | Detail |
|---|---|
| **Direction** | CLI -> processing/integration internals |
| **Location** | Resolve command handling in `storytoolkitai/ui/toolkit_cli.py` |
| **Current behaviour** | CLI code receives `ToolkitOps`, enables/polls Resolve and calls methods on `resolve_api` directly. |
| **Why it matters** | The CLI bypasses the future engine boundary and knows the integration's lifecycle. |
| **Version 1 treatment** | Expose engine methods for Resolve status and render operations. Keep current CLI output and exit behaviour. |
| **Tests needed first** | CLI Resolve command with fake engine; current success/failure exit behaviour. |
| **Priority** | Medium-high. |
| **Status** | Open. |

## C17 — Processing infers runtime mode from `sys.argv` and `cli_args`

| Field | Detail |
|---|---|
| **Direction** | Startup/UI mode -> processing behaviour |
| **Location** | `ToolkitOps.__init__`; related application state in `core/storytoolkitai.py`; Resolve helper launch paths |
| **Current behaviour** | `ToolkitOps` checks `--noresolve` in `sys.argv` and reads `stAI.cli_args.mode` to decide Resolve initialization and queue resume behaviour. Some Resolve workflows launch CLI-mode subprocesses. |
| **Why it matters** | The same processing object behaves differently based on ambient process arguments, which is hard to test and unsuitable for an engine created by another host. |
| **Version 1 treatment** | Parse arguments once in startup. Pass explicit construction options, for example `enable_resolve` and `resume_queue`. Retain subprocess behaviour only behind a named engine method/configuration. |
| **Tests needed first** | ToolkitOps/engine construction for GUI, CLI, `--noresolve` and queue-resume cases. |
| **Priority** | High. |
| **Status** | Open. |

## C18 — UI uses a wildcard import from the large operations module

| Field | Detail |
|---|---|
| **Direction** | UI -> all names exported by processing module |
| **Location** | Import section of `storytoolkitai/ui/toolkit_ui.py` |
| **Current behaviour** | The UI uses `from storytoolkitai.core.toolkit_ops.toolkit_ops import *`. |
| **Why it matters** | Dependencies are implicit, name origins are difficult to follow and an engine boundary cannot be reviewed reliably. |
| **Version 1 treatment** | Replace with explicit imports immediately or as each feature is migrated. Ultimately the UI should import `StoryToolkitEngine`, event/job data types, and UI-independent model types only where intentionally allowed. |
| **Tests needed first** | Normal import/startup test. |
| **Priority** | High and low-risk, but avoid a large noisy import-only change if it blocks ongoing work. |
| **Status** | Open. |

## C19 — UI holds the application object, operations object and model objects broadly

| Field | Detail |
|---|---|
| **Direction** | UI -> broad internal object graph |
| **Location** | Constructors throughout `toolkit_ui.py`, including the main UI, item/editor helpers and windows |
| **Current behaviour** | Many UI helpers keep `toolkit_UI_obj`, `toolkit_ops_obj` and `stAI`, then call whichever internal behaviour is needed. |
| **Why it matters** | Dependencies are difficult to identify and gradually expand. Testing a small UI component requires the full application graph. |
| **Version 1 treatment** | Do not introduce dependency-injection machinery. Pass the engine to top-level UI objects and, when a helper needs only one capability, pass the engine or one explicit callable. Stop passing `ToolkitOps` into new code. |
| **Tests needed first** | Existing UI smoke coverage; no special framework required. |
| **Priority** | Medium; resolve incrementally. |
| **Status** | Open. |

## C20 — UI directly creates, mutates and saves live project/content models

| Field | Detail |
|---|---|
| **Direction** | UI -> model/storage behaviour |
| **Location** | Project, transcription, story and document workflows throughout `toolkit_ui.py` |
| **Current behaviour** | UI code constructs model objects and calls methods that mutate, link/unlink and save them. Some model managers use process-local caches. |
| **Why it matters** | These calls cannot become a remote client API unchanged, and storage behaviour can be triggered from many presentation paths. |
| **Version 1 treatment** | Make a deliberate limited choice: model classes may remain shared in-process where they are already UI-independent, but creation/loading/saving and multi-object operations should gain engine entry points as screens are migrated. Do not design version 2 edit commands yet. |
| **Tests needed first** | Existing load/save/round-trip tests already provide part of the safety net; add workflow-specific tests before moving project linking or transcript/story editing. |
| **Priority** | Medium for version 1; process-safe redesign deferred. |
| **Status** | Open / accepted temporarily under stated limits. |

## C21 — `StoryToolkitAI` combines engine settings with launcher/UI state

| Field | Detail |
|---|---|
| **Direction** | Shared application object across startup, processing and UI |
| **Location** | `storytoolkitai/core/storytoolkitai.py::StoryToolkitAI` |
| **Current behaviour** | The object stores settings and application paths, but also command-line arguments, mode-dependent behaviour, update/API lifecycle and values related to file-dialog navigation. |
| **Why it matters** | Passing this object into all processing modules hides which values are actually needed and mixes engine configuration with UI/launcher state. |
| **Version 1 treatment** | Do not replace it wholesale. Keep it behind the engine and gradually pass explicit values to extracted processing modules. Move clearly UI-only state to the UI when touched. |
| **Tests needed first** | Settings read/write and startup-mode characterization. |
| **Priority** | Medium; gradual containment. |
| **Status** | Open. |

## C22 — Operation dispatch and result values are inconsistent

| Field | Detail |
|---|---|
| **Direction** | Processing API ambiguity exposed to UI/queue |
| **Location** | `ToolkitOps` processing methods and `ProcessingQueue.execute_item_tasks` |
| **Current behaviour** | Queue tasks receive merged dictionaries and return varying values, including dictionaries, booleans, paths or `None`; comments in the queue acknowledge inconsistent results. |
| **Why it matters** | A small engine API is hard to document when callers must know each implementation's ad hoc return shape. |
| **Version 1 treatment** | Normalize only methods exposed by the engine. Use small `JobInfo`/operation-result dataclasses or well-documented plain values. Internal legacy task returns may remain until their operation is migrated. |
| **Tests needed first** | Characterize result values for each task before changing it. |
| **Priority** | Medium-high; handle per vertical slice. |
| **Status** | Open. |

# Workflow assessment

## Transcription

### Current flow

```text
Tk UI
  -> builds ingest/transcription settings
  -> calls ToolkitOps
  -> ToolkitOps adds raw queue items
  -> ProcessingQueue dispatches ToolkitOps.whisper_transcribe
  -> transcription updates queue dictionaries
  -> transcription calls Tk OS notifications
  -> queue invokes observer callback objects
  -> Tk UI re-reads queue dictionaries
```

### Version 1 boundary

```text
Tk UI
  -> engine.start_transcription(settings)
  <- job snapshot

Engine / queue
  -> emits job events with job_id and status

Tk UI
  -> engine.get_job(job_id)
  -> presents progress/notification
```

### Required tests before refactoring

- successful mocked transcription;
- initialization/model failure;
- cancellation before execution and during execution;
- existing-output/retranscribe behaviour;
- queue item status sequence;
- generated transcription path and saved output;
- start/completion event payloads.

This is the recommended first complete vertical slice after the engine and event
objects exist.

## Processing queue

The queue is central to almost every future UI, so version 1 should give it a
small stable surface without replacing its persistence design.

Recommended initial public data:

```python
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class JobInfo:
    """Read-only snapshot returned to UIs.

    `details` is temporary compatibility data for fields not yet promoted to
    explicit attributes. The dictionary must be a copy, never the queue's
    stored mutable item.
    """

    id: str
    task: str | None
    item_type: str | None
    name: str
    status: str
    progress: float | str | None = None
    error: str | None = None
    details: dict[str, Any] | None = None
```

Recommended initial engine surface:

```python
def list_jobs(self) -> list[JobInfo]: ...
def get_job(self, job_id: str) -> JobInfo | None: ...
def cancel_job(self, job_id: str) -> bool: ...
```

A new queue database, durable event replay and multi-process locking are version
2 concerns unless current tests expose a release-blocking defect.

## Resolve

Resolve is the largest mixed UI/processing workflow. Do not begin by creating a
generic Resolve service hierarchy. Split concrete operations.

Example direction:

```python
# UI side: gather native/user input.
request = RenderMarkersRequest(
    target_dir=selected_dir,
    marker_color=selected_color,
    starts_with=prefix or None,
    render_kind="stills",
)

# Engine side: validate Resolve state and execute only.
result = engine.render_resolve_markers(request)
```

The engine can return a simple result/error code. The UI chooses the message box
wording. Operation-specific methods are easier to maintain than a single method
accepting operation-name strings and a UI object.

## Search and video indexing

Search currently crosses the boundary in both directions: UI constructs and
controls processing objects, while processing objects receive the broad
`ToolkitOps` object.

The smallest useful correction is:

```text
UI -> engine.search_text(...)
UI -> engine.search_video(...)
UI -> engine.start_text_index(...)
UI -> engine.start_video_index(...)
```

The existing search classes and cache strategy may remain behind those methods
for version 1. Thread creation belongs behind the engine/processing call, not in
Tk window code.

## Assistant

The first correction is small: remove the copied UI reference from
`ToolkitAssistant` and identify the exact settings/provider values it needs.
There is no need to redesign assistant providers as part of Step 4.

## Project, transcription, story and document models

The reviewed model modules are substantially more UI-independent than
`ToolkitOps`, queue, search and Resolve. They do not need to be renamed into a
"domain" layer.

For version 1:

- keep their current names and formats;
- keep existing round-trip compatibility;
- allow live model objects inside the same process where useful;
- prefer engine methods for loading, creating, saving and operations involving
  several models;
- do not expose cache dictionaries or storage implementation details to new UI
  code.

A process-safe editing API belongs to version 2.

## Startup and runtime mode

Argument parsing should remain at the application entry point. Engine creation
should receive explicit options rather than allowing processing constructors to
inspect `sys.argv`.

A minimal construction shape could be:

```python
@dataclass(frozen=True)
class EngineOptions:
    enable_resolve: bool = True
    resume_queue: bool = True


def create_engine(stAI, options: EngineOptions) -> StoryToolkitEngine:
    ...
```

This is a simple data object, not a dependency-injection framework.

# Findings that are encouraging

The review found useful existing separation that should be preserved:

- project, transcription, story, document, ingest and media concepts already
  live in their own modules;
- Pydantic settings models already exist for some processing requests;
- `mots_resolve.py` appears to contain Resolve API work without Tk presentation
  code; the UI coupling is concentrated primarily in `ToolkitOps` orchestration;
- queue jobs already have IDs, statuses, dependencies, cancellation and saved
  state;
- most problematic coupling is concentrated in `ToolkitOps`, queue observers,
  search UI and Resolve orchestration rather than spread evenly through every
  module.

The reviewed core/integration files did not reveal an obvious direct import of
`storytoolkitai.ui`; most coupling is hidden through passed objects and
callbacks. The accompanying import-boundary test verifies this against the full
local checkout and prevents new direct imports from being added.

# Recommended order after this inventory

This ordering minimizes risk and avoids a large rewrite:

1. **Add the direct-import guard.** It should pass now and prevents the boundary
   from getting worse.
2. **Add missing characterization tests for engine construction and queue
   lifecycle.**
3. **Create a thin `StoryToolkitEngine` facade** around existing behaviour.
4. **Add `EngineEvent` and a small in-process emitter.**
5. **Migrate transcription notifications** as the first processing -> UI event
   slice.
6. **Expose queue snapshots and cancel/list/get methods through the engine.**
7. **Migrate the queue UI** off `processing_queue` internals.
8. **Replace the live observer path** feature by feature.
9. **Separate Resolve prompts from Resolve execution.**
10. **Move search object/thread ownership behind engine methods.**
11. **Remove assistant's UI back-reference.**
12. **Pass explicit runtime options instead of reading `sys.argv` in
    processing.**
13. **Migrate remaining Tk and CLI calls to the engine.**
14. **Remove the `toolkit_UI_obj` field and compatibility adapters.**

# Tests to add before the related refactors

The following are not required to finish the documentation inventory, but they
are prerequisites for changing the associated coupling safely:

| Area | Minimum characterization coverage |
|---|---|
| Engine/bootstrap | Construct in GUI/CLI-like modes; Resolve enabled/disabled; queue resume enabled/disabled. |
| Queue | Submit, dispatch, dependency, status/progress, completion, failure, cancellation, reload from file. |
| Transcription | Mocked success, failure, cancellation, output path, status sequence and notifications. |
| Resolve | Fake API for no connection/timeline/bin/markers, copy markers and marker rendering. |
| Search | Fake text/video indexes, model/cache behavior, filtered paths, errors and cancellation. |
| Assistant | Construction without UI; fake provider success/error. |
| Tk integration | UI event listener schedules Tk updates without processing receiving a window. |

# Repeatable local audit

Run these commands from the repository root. They produce precise source line
numbers for the current checkout.

Install `ripgrep` on macOS if it is not present:

```bash
brew install ripgrep
```

## Processing references to UI concepts

```bash
rg -n --glob '*.py' \
  'toolkit_UI_obj|notify_via_os|notify_via_messagebox|AskDialog|ask_for_target_dir|receive_notification' \
  storytoolkitai
```

## Observer and callback coupling

```bash
rg -n --glob '*.py' \
  'attach_observer|dettach_observer|notify_observers|add_observer_to_window|window\.after\(' \
  storytoolkitai
```

## UI access to queue implementation

```bash
rg -n --glob '*.py' \
  'processing_queue|queue_history|queue_threads|queue_tasks|get_all_queue_items|get_item\(|set_to_canceled' \
  storytoolkitai/ui
```

## Shared NLE state and Resolve calls

```bash
rg -n --glob '*.py' \
  '\bNLE\.|execute_resolve_operation|resolve_check_timeline|resolve_api|resolve_enable|resolve_disable' \
  storytoolkitai/ui storytoolkitai/core
```

## Search objects and UI-owned worker threads

```bash
rg -n --glob '*.py' \
  'TextSearch\(|VideoSearch\(|ToolkitSearch\(|Thread\(|index_text|index_video' \
  storytoolkitai/ui storytoolkitai/core/toolkit_ops/search.py
```

## Broad object construction in UI

```bash
rg -n --glob '*.py' \
  'Project\(|Transcription\(|Story\(|Document\(|ToolkitAssistant\(' \
  storytoolkitai/ui
```

## Ambient runtime-mode reads

```bash
rg -n --glob '*.py' \
  'sys\.argv|cli_args|--noresolve|--mode.?cli|subprocess\.(Popen|run)' \
  storytoolkitai/core storytoolkitai/integrations
```

## Direct UI imports from processing

```bash
rg -n --glob '*.py' \
  '(^|[[:space:]])(from|import)[[:space:]]+storytoolkitai\.ui|from[[:space:]]+\.\.?ui' \
  storytoolkitai/core storytoolkitai/integrations
```

## Wildcard operations import

```bash
rg -n --glob '*.py' \
  'from storytoolkitai\.core\.toolkit_ops\.toolkit_ops import \*' \
  storytoolkitai/ui
```

The accompanying `audit_ui_coupling.sh` runs these searches and writes a single
report to `/tmp/storytoolkitai-ui-coupling-audit.txt` by default. Pass another
output path as its first argument when needed.

# Open decisions for Step 4

These decisions should be made while implementing the first engine facade, not
through a separate architecture exercise:

1. **Where should `StoryToolkitEngine` live initially?**  
   Recommended: `storytoolkitai/core/engine.py` to minimize file movement.

2. **Are live model objects allowed through the version 1 engine?**  
   Recommended: yes, temporarily, when the model is UI-independent. Do not
   expose their global caches or promise that this is the version 2 API.

3. **What is the minimum event shape?**  
   Recommended:

   ```python
   @dataclass(frozen=True)
   class EngineEvent:
       type: str
       data: dict[str, Any]
   ```

   Add structure only when an actual workflow needs it.

4. **Should all queue item fields be modeled immediately?**  
   Recommended: no. Start with common `JobInfo` fields and a copied temporary
   `details` dictionary.

5. **Should CLI subprocess rendering be removed in version 1?**  
   Recommended: not automatically. Hide it behind an engine operation and
   characterize it first. Replacing the process model can wait for version 2.

# Step 3 completion checklist

Step 3 can be marked complete when:

- [x] Processing -> UI calls have been inventoried.
- [x] UI -> processing-internal calls have been inventoried.
- [x] Observer/callback coupling has been inventoried.
- [x] Queue coupling has been inventoried.
- [x] Resolve/NLE shared state has been inventoried.
- [x] Search ownership and UI-created worker threads have been inventoried.
- [x] Assistant UI/global-state coupling has been inventoried.
- [x] Startup/runtime-mode coupling has been inventoried.
- [x] Shared live model usage has been classified rather than prematurely redesigned.
- [x] Run `audit_ui_coupling.sh` in the local `dev` checkout and review any additional matches.
- [x] Run `test_ui_import_boundary.py` in the local test suite.
- [x] Add any newly discovered coupling as another `Cxx` entry.
- [x] Commit the inventory and import guard.

Suggested commit:

```text
docs: inventory current UI and processing coupling
```

Or, if the import guard is committed at the same time:

```text
docs: inventory UI coupling and guard import direction
```

# Exit condition

This document completes Step 3 once the local audit has been run and any missed
relationships have been added. No production-code coupling needs to be removed
in Step 3. The next production change should be Step 4: a thin engine facade,
preceded only by characterization tests for the first methods it exposes.
