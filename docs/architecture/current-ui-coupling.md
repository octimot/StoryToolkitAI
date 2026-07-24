# Version 1 UI and processing coupling

**Status:** Closed Version 1 architecture inventory
**Branch reviewed:** `dev`
**Reviewed through:** `b37334263e8620d91365dc32d333e536d06c1a58`
**Related decision:** [`engine-ui-separation.md`](./engine-ui-separation.md)
**Implemented boundary:** [`tk-engine-boundary.md`](./tk-engine-boundary.md)
**Runtime issues:** [`known-refactor-issues.md`](./known-refactor-issues.md)

## Purpose

This document records the final Version 1 relationship between first-party interfaces and processing code.

The migration inventory is closed for Version 1. Resolved entries remain here so the reasons for the architecture tests and current object graph are not lost.

Accepted in-process limits belong to Version 2 planning. They do not reopen the Version 1 boundary.

## Final dependency picture

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
          +--> private ToolkitOps
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
                  +--> Resolve operations and snapshots
                  +--> processing events

Tk receives:  StoryToolkitAI + StoryToolkitEngine
CLI receives: StoryToolkitEngine
```

The direct processing-to-UI dependency has been removed.

`ToolkitOps` remains an internal processing coordinator. It is not passed to first-party interfaces and does not need to be removed for Version 1.

## Status legend

- **Resolved** — the identified first-party coupling no longer exists.
- **Resolved for Version 1** — the required in-process boundary is complete; a stricter process boundary belongs to Version 2.
- **Accepted for Version 1** — deliberately retained while the application remains in one Python process.
- **Deferred to Version 2** — intentionally outside the completed Version 1 boundary.

## Closed inventory

| ID | Coupling | Final status | Version 1 disposition |
| --- | --- | --- | --- |
| C01 | Application construction exposed broad processing objects to interfaces | Resolved | `build_runtime(...)` returns `StoryToolkitAI` and `StoryToolkitEngine`; `ToolkitOps` remains private. |
| C02 | `ToolkitOps` stored the live Tk application | Resolved | Processing no longer stores or calls the Tk application. |
| C03 | Transcription processing sent OS notifications directly | Resolved | Processing emits events; Tk decides whether to display notifications. |
| C04 | Resolve processing received and invoked a UI object | Resolved | Resolve operations accept plain values and return UI-independent results. |
| C05 | Core notification service stored frontend receivers | Resolved | Notification presentation helpers are UI-owned. |
| C06 | Processing observers stored live callback objects | Resolved | UI callback objects are no longer stored in processing. |
| C07 | Queue and compatibility workflows used implicit UI action strings | Resolved | Queue and named processing events use structured event data; removed compatibility paths are guarded by tests. |
| C08 | `ProcessingQueue` depended on the complete `ToolkitOps` object | Resolved | The queue receives explicit task handlers and the shared event emitter. |
| C09 | UI read and mutated queue implementation details | Resolved | Queue queries and mutations go through engine methods. |
| C10 | Queue and search UI relied on timing workarounds around callbacks | Resolved | Engine queries return copied queue data; snapshot synchronization remains a release-hardening requirement. Events and polling indicate that state may have changed. |
| C11 | UI constructed search processors and owned search workers | Resolved for Version 1 | The engine owns search sessions, processors and workers. |
| C12 | Search classes received the complete operations object | Resolved for Version 1 | Search receives narrow explicit configuration. |
| C13 | Assistant copied a hidden UI reference | Resolved | Assistant implementations remain processing-owned and UI-independent. |
| C14 | Tk and CLI read global Resolve implementation state | Resolved for Version 1 | First-party interfaces use engine snapshots and commands; internal `NLE` state may remain inside processing. |
| C15 | Menu commands passed the UI object into processing | Resolved | Menu handlers collect input and call explicit engine methods. |
| C16 | CLI called Resolve implementation details | Resolved | CLI processing uses `StoryToolkitEngine`. |
| C17 | Processing inferred runtime policy from `sys.argv` or `cli_args` | Resolved | Runtime policy is converted into `RuntimeOptions`; process restart and path discovery remain allowed mechanics. |
| C18 | UI wildcard-imported the large operations module | Resolved | UI and boundary imports are explicit and guarded by tests. |
| C19 | UI held broad processing implementation objects | Resolved for Version 1 | Tk keeps `StoryToolkitAI` for existing application state and uses the engine for processing. |
| C20 | UI creates and mutates live project and content models | Accepted for Version 1 | UI-independent models may be shared inside the current process; a serialized API belongs to Version 2. |
| C21 | `StoryToolkitAI` combines settings, paths, lifecycle and some UI-facing state | Accepted for Version 1 | Decompose only when a concrete Version 2 process or packaging requirement benefits from it. |
| C22 | Operation result shapes are inconsistent | Deferred to Version 2 | Standardize public operations as they cross a real process API; do not add a generic result framework solely for Version 1. |

## Accepted Version 1 limits

The following are not release blockers:

- Tk receives `StoryToolkitAI` for existing settings, paths and lifecycle behaviour.
- UI-independent project and content models remain live in the same process.
- `AssistantSession` is an in-process handle rather than a network contract.
- some Resolve workflows use existing `Timecode` and render-monitor objects;
- video-search presentation may use an image array;
- engine methods may retain operation-specific return shapes;
- `ToolkitOps` remains a large internal coordinator;
- internal Resolve state may continue to use `NLE`.

These limits must be revisited before a separate engine process or independently released API is introduced.

## Repeatable local audit

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

The architecture test distinguishes command-line policy reads from legitimate process restart and executable-path operations.

```bash
python -m pytest   tests/architecture/test_processing_boundary.py::test_processing_does_not_read_ambient_runtime_state   -q
```

Expected result: the test passes.

### Removed legacy event paths

Expected result: no matches under core or integrations.

```bash
rg -n --glob '*.py'   'notify_observers|action\.triggered|create_action_triggered_event|_emit_legacy_action|on_stop_action_name'   storytoolkitai/core   storytoolkitai/integrations
```

### Architecture tests

```bash
python -m pytest tests/architecture -q
```

### Remaining tests

```bash
python -m pytest --ignore=tests/architecture -q
```

## Update rule

When a Version 1 boundary changes:

1. update only the affected inventory row and accepted-limit text;
2. record the commit that changed the boundary;
3. keep accepted in-process limits explicit;
4. do not describe an in-process handle as ready for a network boundary;
5. add a new item only when the issue is materially different from C01–C22.

Version 2 work should create a separate migration inventory instead of reopening this completed Version 1 inventory.
