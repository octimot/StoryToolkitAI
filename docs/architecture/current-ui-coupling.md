# Current UI and processing coupling

**Status:** Version 1 migration inventory after completion of the first-party Tk and CLI engine boundary  
**Branch reviewed:** `dev`  
**Reviewed through:** `13836ca23215f605054d3498c852b1a708e5b314`  
**Related decision:** [`engine-ui-separation.md`](./engine-ui-separation.md)  
**Implemented boundary:** [`tk-engine-boundary.md`](./tk-engine-boundary.md)

Known runtime behaviour noticed during the migration is tracked in [`known-refactor-issues.md`](./known-refactor-issues.md).

## Purpose

This document records the remaining relationship between user interfaces and processing code.

It is a migration checklist, not a proposal for a framework. Resolved entries remain here so the reason for the architecture tests and current object graph is not lost.

## Status legend

- **Resolved** — the identified first-party interface coupling no longer exists.
- **Resolved for Version 1** — the required in-process boundary is complete; a stricter process boundary belongs to Version 2.
- **Accepted for Version 1** — deliberately retained while the application remains in one Python process.
- **Compatibility cleanup** — no longer required by the first-party UI boundary, but unused or transitional implementation remains.
- **In progress** — useful improvements exist, but the item is not yet complete.

## Current dependency picture

```text
__main__.py
    |
    +--> RuntimeOptions
    |
    +--> build_runtime(...)
            |
            +--> StoryToolkitAI
            |
            +--> private ToolkitOps
            |       |
            |       +--> ProcessingQueue
            |       +--> search processors
            |       +--> assistant implementations
            |       +--> Resolve integration
            |       +--> EventEmitter
            |
            +--> StoryToolkitEngine
                    |
                    +--> public processing operations
                    +--> detached state snapshots
                    +--> engine-owned search sessions
                    +--> engine-owned assistant sessions
                    +--> Resolve operations
                    +--> event subscriptions

StoryToolkitAI + StoryToolkitEngine
    |
    v
Tk UI

StoryToolkitEngine
    |
    v
CLI
```

The main first-party processing boundary is now:

```text
Tk UI / CLI
        |
        v
StoryToolkitEngine
        |
        v
ToolkitOps and processing internals
```

Tk still receives `StoryToolkitAI` for application settings, paths and lifecycle behaviour. UI-independent content models also remain shared in-process. Those accepted limits are tracked under C20 and C21.

# Coupling inventory

## C01 — Application construction exposes broad internals to interfaces

| Field | Detail |
|---|---|
| **Direction** | Bootstrap -> first-party interfaces |
| **Previous state** | Startup returned `StoryToolkitAI`, `ToolkitOps` and `StoryToolkitEngine`. Tk received all three, and the CLI received broad processing objects. |
| **Current state** | `build_runtime(...)` privately creates `ToolkitOps` and returns only `StoryToolkitAI` and `StoryToolkitEngine`. Tk receives `stAI` and `engine`. CLI receives only `engine` for processing. |
| **Accepted limit** | Tk still receives `StoryToolkitAI`; that separate responsibility issue is tracked under C21. |
| **Status** | Resolved for processing internals |
| **Related commits** | `201ca62b576adecec333c061c35977f5dd5bfa96`, `99a82f8afcda1b284416f6c9cdbf33b7d05b3793` |

## C02 — `ToolkitOps` stores the live Tk application

| Field | Detail |
|---|---|
| **Previous state** | `ToolkitOps` stored `toolkit_UI_obj`, and GUI startup assigned the complete Tk application back to processing. |
| **Current state** | Processing does not receive or store the Tk application. Tk subscribes to engine events. |
| **Status** | Resolved |
| **Related commits** | `9a6f1f05f1b7c0d4116e7027410a61a8a6f6467d`, `0de06f4bde23b8655bcf88cfb08fd65ccb0b1d0a` |

## C03 — Transcription processing issues OS notifications directly

| Field | Detail |
|---|---|
| **Previous state** | Transcription processing called Tk notification methods. |
| **Current state** | Processing emits transcription events. Tk decides whether and how to display an OS notification. |
| **Status** | Resolved |
| **Related commit** | `9a6f1f05f1b7c0d4116e7027410a61a8a6f6467d` |

## C04 — Resolve operations receive and invoke a UI object

| Field | Detail |
|---|---|
| **Previous state** | Resolve processing accepted a Tk object, displayed dialogs and requested presentation input. |
| **Current state** | Tk gathers user input and calls explicit engine operations. Processing returns results or state without displaying UI. |
| **Status** | Resolved |
| **Related commits** | `0de06f4bde23b8655bcf88cfb08fd65ccb0b1d0a`, `7f19e1aeb9295d6ca017389c2c317f693b97fdc9` |

## C05 — Core notification service stores frontend receivers

| Field | Detail |
|---|---|
| **Previous state** | Notification helpers in processing stored live receiver objects. |
| **Current state** | Notification helpers and receivers are UI-owned. |
| **Status** | Resolved |
| **Related commit** | `4473562f3d7a63c76109c39e3c7f74ab647e135d` |

## C06 — Processing observers are live UI callback objects

| Field | Detail |
|---|---|
| **Previous state** | Processing stored observer objects and invoked their callbacks. |
| **Current state** | Processing emits named engine events. Tk owns and schedules presentation callbacks locally. No processing observer bridge or live UI callback object remains. |
| **Status** | Resolved |
| **Related commits** | `3c9515dc094aba4a174a97d0a9aca13c7e45fe20`, `df324563dcaad7d9de10e1502871a3a297b7e27a`; final bridge removed during Step 12.4. |

## C07 — Queue and compatibility notifications use implicit action strings

| Field | Detail |
|---|---|
| **Previous state** | Queue lifecycle, search completion, Resolve polling and transcription-group updates relied on UI-oriented action names. |
| **Current state** | Queue changes emit `job.changed`; completed tasks emit `job.task_completed`; advanced search reads engine-owned state. Resolve polling and question grouping publish named engine events directly. No processing compatibility action bridge remains. |
| **Status** | Resolved |
| **Related commits** | `866d438`, `f97d0b3`, `ffef103`, `0df67f0`, `3ce19ad`, `e9684f2`, `3518c45b9c56a60b5e76ab65994bd12223d94e50`, `df324563dcaad7d9de10e1502871a3a297b7e27a`; final bridge removed during Step 12.4. |

## C08 — `ProcessingQueue` depends on the whole `ToolkitOps` object

| Field | Detail |
|---|---|
| **Previous state** | The queue stored `ToolkitOps` and used it for task dispatch and notifications. |
| **Current state** | The queue receives an explicit task-handler mapping and the shared event emitter. |
| **Status** | Resolved |
| **Related commit** | `ffef103` |

## C09 — UI reads and mutates queue implementation details

| Field | Detail |
|---|---|
| **Previous state** | Tk read queue dictionaries, generated IDs, changed statuses and cancelled items directly. |
| **Current state** | Queue state and operations are exposed through `StoryToolkitEngine`. Tk receives detached job snapshots and does not access `ProcessingQueue`. |
| **Status** | Resolved |
| **Related commits** | `a3865d6`, `059909c`, `2a15029`, `fe95896`, `7c1babe`, `3518c45b9c56a60b5e76ab65994bd12223d94e50` |

## C10 — Queue UI contains observer-race workarounds

| Field | Detail |
|---|---|
| **Previous state** | Tk relied on payload-free observers and timing-sensitive direct queue reads. |
| **Current state** | Events signal possible changes; engine snapshots remain authoritative. Search preparation follows the same snapshot or polling pattern. |
| **Status** | Resolved |
| **Related commits** | `059909c`, `866d438`, `f97d0b3`, `0df67f0`, `3ce19ad` |

## C11 — UI directly constructs search processors and owns worker threads

| Field | Detail |
|---|---|
| **Previous state** | Tk created text and video search processors, loaded models and owned preparation workers. |
| **Current state** | The engine owns search processors, session state, preparation workers and query execution. Tk stores only a search ID and presentation state. |
| **Accepted limit** | Video-frame presentation still returns an in-process image array. |
| **Status** | Resolved for Version 1 |
| **Related commits** | `9cfc6f5`, `a576250`, `e67b05f`, `537d032`, `3ce19ad`, `e9684f2` |

## C12 — Search classes receive the complete operations object

| Field | Detail |
|---|---|
| **Previous state** | Search processors received `ToolkitOps` and derived all settings and resources through it. |
| **Current state** | Search processors receive a narrow `SearchConfig`. Live processors remain private to the engine. |
| **Status** | Resolved for Version 1 |
| **Related commits** | `9f7e644`, `e9684f2` |

## C13 — Assistant processing is owned by the UI or carries a UI back-reference

| Field | Detail |
|---|---|
| **Previous state** | Assistant implementations inherited a Tk back-reference, and Tk constructed and replaced live assistant objects using `ToolkitOps`. |
| **Current state** | The back-reference is removed. The engine owns assistant implementations and exposes an `AssistantSession` handle. Model replacement and conversation-state copying occur behind the engine boundary. |
| **Accepted limit** | `AssistantSession` is an in-process handle, not a Version 2 network contract. Assistant implementations may still use private `ToolkitOps` dependencies internally. |
| **Status** | Resolved for Version 1 |
| **Related commits** | `fdc93adc07f1c2177857da6300651b56fbb8eecb`, `dec9242c6e9064f46de0be4b806fbd4fe139e48e` |

## C14 — Resolve state is stored globally on `NLE`

| Field | Detail |
|---|---|
| **Previous state** | Tk and CLI read global Resolve state and raw integration objects directly. |
| **Current state** | First-party interfaces use engine snapshots and explicit Resolve operations. Architecture tests forbid `NLE`, `MotsResolve` and `resolve_api` access in UI modules. |
| **Accepted limit** | `NLE` may remain an internal processing implementation during Version 1. Removing the global is not required to preserve the interface boundary. |
| **Status** | Resolved for the first-party interface boundary |
| **Related commits** | `201ca62b576adecec333c061c35977f5dd5bfa96`, `7f19e1aeb9295d6ca017389c2c317f693b97fdc9`, `13836ca23215f605054d3498c852b1a708e5b314` |

## C15 — Menu commands pass the UI object into processing

| Field | Detail |
|---|---|
| **Previous state** | Resolve menu handlers passed the complete UI object into a generic processing operation. |
| **Current state** | UI handlers call explicit engine operations with plain input values. |
| **Status** | Resolved |
| **Related commit** | `0de06f4bde23b8655bcf88cfb08fd65ccb0b1d0a` |

## C16 — CLI calls Resolve or processing implementation details

| Field | Detail |
|---|---|
| **Previous state** | CLI received broad objects, controlled Resolve lifecycle and invoked raw Resolve operations. |
| **Current state** | CLI receives only `StoryToolkitEngine` for processing. It parses command-line presentation input and calls public engine operations. |
| **Status** | Resolved |
| **Related commits** | `201ca62b576adecec333c061c35977f5dd5bfa96`, `13836ca23215f605054d3498c852b1a708e5b314` |

## C17 — Processing infers runtime mode from ambient arguments

| Field | Detail |
|---|---|
| **Previous state** | Processing inspected argparse state, `sys.argv` and mode flags to decide runtime policy. |
| **Current state** | Parsed arguments are converted into immutable `RuntimeOptions`. Processing constructors receive explicit decisions. |
| **Status** | Resolved |
| **Related commit** | `201ca62b576adecec333c061c35977f5dd5bfa96` |

## C18 — UI uses wildcard imports

| Field | Detail |
|---|---|
| **Previous state** | Tk imported all names from the large operations module and used other wildcard imports. |
| **Current state** | UI imports are explicit. An AST-based architecture test rejects wildcard imports throughout first-party UI modules. |
| **Status** | Resolved |
| **Related commit** | `13836ca23215f605054d3498c852b1a708e5b314` |

## C19 — UI stores broad processing implementation objects

| Field | Detail |
|---|---|
| **Previous state** | The Tk object graph stored `ToolkitOps`; helpers and workflows could bypass the engine. |
| **Current state** | `ToolkitOps` and related processing implementation names are absent from the UI object graph. `run_gui(...)` accepts only `stAI` and `engine`. AST and runtime-object-graph tests enforce the boundary. |
| **Accepted limit** | Tk still stores `StoryToolkitAI` and UI-independent content models. Those are tracked under C20 and C21. |
| **Status** | Resolved for processing internals |
| **Related commits** | `3518c45b9c56a60b5e76ab65994bd12223d94e50`, `7f19e1aeb9295d6ca017389c2c317f693b97fdc9`, `dec9242c6e9064f46de0be4b806fbd4fe139e48e`, `99a82f8afcda1b284416f6c9cdbf33b7d05b3793`, `13836ca23215f605054d3498c852b1a708e5b314` |

## C20 — UI directly creates and mutates live content models

| Field | Detail |
|---|---|
| **Current state** | Tk creates, loads, mutates and saves UI-independent project, transcription, story, document and related model objects. |
| **Accepted limit** | These objects may remain shared while Version 1 uses one Python process. |
| **Future requirement** | A separate Version 2 engine process must replace live cross-process objects with serializable models, IDs, commands and results. |
| **Status** | Accepted for Version 1 |

## C21 — `StoryToolkitAI` combines settings, launcher and UI state

| Field | Detail |
|---|---|
| **Current state** | Runtime mode is explicit, but `StoryToolkitAI` still combines settings, paths, update lifecycle and values used by Tk. It is passed to both `ToolkitOps` and Tk. |
| **Accepted limit** | Retain this object for Version 1 unless a specific testability, packaging or process-boundary problem requires a smaller dependency. |
| **Future requirement** | Before a separate engine process, identify which configuration belongs to engine startup and which belongs to the frontend. |
| **Status** | Accepted for Version 1; deferred |

## C22 — Public operation results have inconsistent shapes

| Field | Detail |
|---|---|
| **Current state** | Existing operations return booleans, dictionaries, paths, lists, tuples, model objects and `None`. Migrated engine methods document and copy results where practical. |
| **Accepted approach** | Standardize public engine results one migrated workflow at a time. Do not introduce a generic result framework solely to normalize legacy internals. |
| **Version 2 requirement** | Commands and queries crossing a process boundary need documented serializable request, result and error shapes. |
| **Status** | In progress; not a Version 1 Tk-boundary blocker |

# Status summary

| ID | Coupling | Status |
|---|---|---|
| C01 | Broad processing objects passed to interfaces | Resolved for processing internals |
| C02 | `ToolkitOps` stores Tk application | Resolved |
| C03 | Processing sends OS notifications | Resolved |
| C04 | Resolve processing receives UI object | Resolved |
| C05 | Core notification service stores receivers | Resolved |
| C06 | Core stores live UI callbacks | Resolved |
| C07 | Compatibility action strings | Resolved |
| C08 | Queue depends on complete `ToolkitOps` | Resolved |
| C09 | UI accesses queue internals | Resolved |
| C10 | Queue and search observer races | Resolved |
| C11 | UI owns search processors and workers | Resolved for Version 1 |
| C12 | Search receives complete `ToolkitOps` | Resolved for Version 1 |
| C13 | UI owns assistant implementation | Resolved for Version 1 |
| C14 | UI accesses global Resolve state | Resolved for first-party boundary |
| C15 | Resolve menu passes UI into processing | Resolved |
| C16 | CLI calls implementation details | Resolved |
| C17 | Processing reads ambient runtime mode | Resolved |
| C18 | UI uses wildcard imports | Resolved |
| C19 | UI stores processing implementation objects | Resolved for processing internals |
| C20 | UI mutates live content models | Accepted for Version 1 |
| C21 | `StoryToolkitAI` mixes responsibilities | Accepted for Version 1; deferred |
| C22 | Inconsistent public result shapes | In progress; incremental |

# Repeatable local audit

Run from the repository root.

## Processing references to UI concepts

Expected result: no intentional matches under core or integrations.

```bash
rg -n --glob '*.py'   'toolkit_UI_obj|notify_via_os|notify_via_messagebox|AskDialog|ask_for_target_dir|receive_notification|NotificationService|NotificationMessage'   storytoolkitai/core   storytoolkitai/integrations
```

## Direct processing imports of UI modules

Expected result: no matches.

```bash
rg -n --glob '*.py'   '(^|[[:space:]])(from|import)[[:space:]]+storytoolkitai\.ui|from[[:space:]]+\.\.?ui'   storytoolkitai/core   storytoolkitai/integrations
```

## First-party UI processing bypasses

Expected result: no matches.

```bash
rg -n --glob '*.py'   'toolkit_ops_obj|ToolkitOps|\.processing_queue|\.resolve_api|\bNLE\b|MotsResolve'   storytoolkitai/ui
```

## UI wildcard imports

Expected result: no matches.

```bash
rg -n --glob '*.py'   '(^|[[:space:]])(from|import)[[:space:]].*\*'   storytoolkitai/ui
```

## Runtime exposure of `ToolkitOps`

Expected result: no matches in `__main__.py` or UI modules. Matches in `app.py` are expected because it privately constructs the processing implementation.

```bash
rg -n --glob '*.py'   'toolkit_ops_obj|ToolkitOps'   storytoolkitai/__main__.py   storytoolkitai/ui
```

## Legacy processing refresh actions

Expected result: no matches under core or integrations.

```bash
rg -n --glob '*.py' \
  'notify_observers|update_NLE_status|update_all_transcriptions|NLE_project_changed|NLE_timeline_changed|NLE_markers_changed|NLE_bin_changed|NLE_tc_changed|NLE_timecode_data_changed|update_transcription_groups_|update_transcription_' \
  storytoolkitai/core storytoolkitai/integrations

## Architecture tests

```bash
python -m pytest tests/architecture/test_ui_import_boundary.py tests/architecture/test_ui_engine_boundary.py tests/architecture/test_ui_resolve_boundary.py tests/architecture/test_runtime_object_graph.py tests/architecture/test_search_boundary.py tests/architecture/test_legacy_event_boundary.py -q
```

Then:

```bash
python -m pytest -q
```

# Update rule

When a coupling changes:

1. Update only the affected entry and summary row.
2. Record the commit that changed or resolved it.
3. Keep accepted Version 1 limits explicit.
4. Do not claim that an in-process handle is ready for a network boundary.
5. Add a new entry only when the issue is materially different from C01–C22.
