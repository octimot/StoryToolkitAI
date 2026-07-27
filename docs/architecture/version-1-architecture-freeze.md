# Version 1 architecture freeze

**Status:** Active until the Version 1 release
**Code reviewed through:** `f62b7877936902615a5cf62f46c73d48b4bdd5d1`
**Intended release:** `v1.0.0`

## Purpose

The processing and UI separation planned for Version 1 is implemented. Until
Version 1 is released, development should focus on correctness, compatibility,
tests, and release hardening rather than another round of restructuring.

This freeze is intended to prevent useful hardening work from expanding into a
larger architecture project. It is not a permanent restriction on Version 2.

## Frozen dependency direction

```text
Tk / CLI
    |
    v
StoryToolkitEngine
    |
    v
ToolkitOps and private processing implementation
```

`ToolkitOps`, `ProcessingQueue`, search processors, assistant implementations,
and Resolve implementation objects remain private behind
`StoryToolkitEngine`.

The Tk application may also receive `StoryToolkitAI` for existing application
state and lifecycle responsibilities. It must not use that object to recover or
bypass private processing implementation objects.

At runtime, `build_runtime(...)` returns only `(StoryToolkitAI,
StoryToolkitEngine)`. `run_gui(...)` receives both objects. `run_cli(...)`
receives the parsed arguments and parser for CLI presentation plus
`StoryToolkitEngine`; it does not receive `StoryToolkitAI` or `ToolkitOps`.

## Changes allowed before Version 1

The following changes are within the Version 1 scope:

- concurrency and thread-safety fixes;
- Tk main-thread scheduling fixes;
- correctness and regression fixes;
- compatibility fixes for existing data and settings;
- tests and test fixtures;
- documentation corrections;
- removal of obsolete migration or compatibility code;
- small local refactors required to make one of the above changes safe and
  understandable.

## Changes deferred until Version 2

Do not add the following merely to make the architecture look more complete:

- an HTTP server or WebSocket transport;
- a separate engine process;
- a replacement job database or queue architecture;
- a new public client or SDK layer;
- a web UI, TUI, or Tauri application;
- a repository split;
- broad package or directory renaming;
- a strict layered architecture;
- generic repositories, factories, or dependency-injection frameworks;
- classes that only wrap or rename existing functions;
- public engine methods that expose private implementation objects;
- splitting `StoryToolkitEngine` only because the file is large.

Version 2 work may be discussed and documented, but it should not be mixed into
Version 1 release-hardening commits.

## Exception rule

An architecture change during the freeze is justified only when a concrete
Version 1 correctness or compatibility problem cannot be fixed safely within
the current boundary.

When an exception is needed, the commit message or related issue should state:

1. the concrete problem;
2. why a local fix is insufficient;
3. the smallest boundary change that solves it;
4. the tests that protect the new behaviour.

## Review checklist

Before committing a Version 1 hardening change, check:

- Does processing remain independent of UI modules?
- Do Tk and CLI still use `StoryToolkitEngine` for processing operations?
- Does the change avoid exposing a private queue, search, assistant, or Resolve
  implementation object?
- Is a new engine method a real operation or state query rather than a bypass?
- Could the problem be solved with a smaller local change?
- Are existing file formats and user data preserved?
- Is the relevant behaviour covered by an automated or documented manual test?

## End of the freeze

The freeze ends when Version 1 is released from the stabilized `dev` branch.
Version 2 architecture work should then begin from the released Version 1
boundary rather than reopening the completed migration without a concrete need.
