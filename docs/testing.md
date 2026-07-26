# Testing StoryToolkitAI

**Code reviewed through:** `f62b7877936902615a5cf62f46c73d48b4bdd5d1`
**Intended release candidate:** `v1.0.0-rc.1`

StoryToolkitAI uses three explicit verification categories:

- **Automated** — deterministic tests that run in the normal pytest suite.
- **Mocked** — automated tests that exercise StoryToolkitAI behavior while
  replacing an external system, heavyweight dependency, or task execution.
- **Manual** — checks requiring a real platform environment, source or packaged
  application, media, model, hardware accelerator, account, operating-system
  integration, FFmpeg, or Resolve.

A pytest result is evidence only for automated and mocked coverage. It must not
be reported as a passed manual, hardware, model, packaged-application, or
Resolve check.

## Install the test dependencies

From the repository root:

```bash
python3.11 -m venv .venv-test
.venv-test/bin/python -m pip install -r requirements-test.txt
```

## Run architecture checks only

The architecture tests verify that the Tk/CLI and engine boundary is preserved. They are fast and do not require heavy processing dependencies.

```bash
.venv-test/bin/python -m pytest tests/architecture -q
```

These tests run on every commit to catch boundary regressions early.

## Run normal lightweight tests

The remaining automated tests cover application logic, processing helpers and integration points that do not require long-running media operations.

```bash
.venv-test/bin/python -m pytest --ignore=tests/architecture -q
```

## Run the complete suite

Run all tests together, including architecture checks and application tests. Use this before preparing a release candidate.

```bash
.venv-test/bin/python -m pytest -q
```

## Run Version 1 boundary-hardening checks

The following focused command covers the queue snapshot/event lock, search
session API, event payload isolation, Tk inbox/poll cycle, known correctness
fixes, and compatibility fixtures:

```bash
.venv-test/bin/python -m pytest \
  tests/architecture \
  tests/test_processing_queue_event_locking.py \
  tests/test_engine.py \
  tests/test_search_sessions.py \
  tests/test_engine_search.py \
  tests/test_events.py \
  tests/test_tk_engine_events.py \
  tests/test_ui_notifications.py \
  tests/test_timecode.py \
  tests/test_compatibility.py \
  -q
```

This focused command is useful for quick feedback but does not replace the
complete suite or the manual release checklists.

The current suite covers search status mapping, detached results, normal
prepare/search/close behavior, and unknown session IDs. It does not yet contain
all deterministic lifecycle-race tests called for by the Version 1 hardening
plan: blocked status reads during preparation/search, close during blocked
preparation/search/frame retrieval, duplicate simultaneous prepare calls, and
late completion after removal or same-ID replacement. The implementation uses
short registry-lock sections and identity revalidation for these cases, but
the missing focused regression tests remain release-hardening work.

## Run Version 1 compatibility checks

The compatibility module uses small synthetic fixtures based on the stable
`v0.25.1` serializer shapes:

```bash
.venv-test/bin/python -m pytest tests/test_compatibility.py -q
```

Coverage in this module is classified as follows:

| Area | Classification | What is verified |
| --- | --- | --- |
| Project loading and ZIP export | Automated | The real project loader reads the stable shape and the archive retains the same `project.json`. |
| Transcription round trip and exports | Automated | The real model and deterministic writers preserve known and nested extension data and match pinned SRT/TXT fixtures. |
| Story round trip and text export | Mocked import dependency | The real story model and writer run in an isolated subprocess; only the unused heavyweight `MediaItem` import is replaced. |
| Queue recovery, dependencies and cancellation | Mocked | The real queue persistence and state code runs in an isolated subprocess, but restored task callables and queue scheduling are harmless stand-ins, so no transcription or model work starts. |
| Detached engine job snapshots | Mocked | The real queue snapshot and engine copy paths run around the restored fixture; the surrounding operations object is a narrow test stand-in. |

Optional-dependency stubs exist only inside the short-lived compatibility
subprocess. They cannot change `sys.modules` in pytest's process or affect
later test-module imports.

Fixture provenance and sanitization are recorded in the
[fixture README](../tests/fixtures/compatibility/v0.25.1/README.md). These
fixtures are compatibility examples, not a replacement for checking copied
stable-release user data.

## Check compilation with warnings

Verify that all Python source files compile cleanly and surface syntax errors and some compile-time warnings early.

```bash
.venv-test/bin/python -m compileall -q -f storytoolkitai tests
```

This does not replace runtime testing, but it catches syntax errors and surfaces some compile-time warnings.

## Heavy processing tests (manual and opt-in)

The following require real media files or long-running operations. They are not
included in the default pytest suite or normal CI and must be started
explicitly in a prepared release environment:

- Transcribe a sample audio file end-to-end and verify the output transcription exists.
- Run a text search on an existing project with multiple transcriptions and verify results.
- Create, submit, cancel and re-submit a queue job to exercise the full lifecycle.
- Start a Resolve connection (on macOS or Windows with Resolve installed) and run a marker operation.
- Generate a story via Assistant and export it as EDL/XML.

Run these manually before a release candidate. Record the environment (OS
version, architecture, Python version, application commit/build, model names,
FFmpeg version and Resolve version/edition when applicable) alongside each
result.

## Current manual release status

The repository contains no completed manual result record for the intended
`v1.0.0-rc.1` candidate. Both platform checklists are deliberately initialized
to **Not run**. Until the release owner attaches environment- and
artifact-specific evidence, all applicable checks below remain open:

- source and packaged startup and clean shutdown;
- installation, upgrade, signing/notarization or SmartScreen behavior, and
  uninstall for each published artifact;
- FFmpeg discovery and a controlled invalid-path failure;
- CPU and every advertised MPS/Metal or CUDA processing path, with evidence
  that accelerated work did not silently fall back;
- native macOS notification presentation with quotes, newlines, Unicode,
  backslashes, and shell metacharacters;
- one representative end-to-end transcription, including cancellation, save,
  reopen, and export;
- queue progress, queued and active cancellation, dependencies, persistence,
  and recovery;
- text and video search, UI responsiveness during preparation/search, and
  close-during-work behavior;
- Assistant setup and a live provider request, including a safe failure case;
- Resolve connection and reversible timeline operations in both source and
  packaged applications where that platform artifact supports Resolve;
- copied stable-release projects, transcriptions, stories, settings, and queue
  data, with unintended format changes ruled out.

An item that does not apply to the publication plan must be marked as such in
the release issue. Leaving it unchecked is not evidence that it was waived.

If a heavyweight automated test is added later, keep it out of the default
suite behind an explicit opt-in command or marker, use repository-external
media/model assets, and document how its result differs from the manual
release checks.

## Version 1 release artifact matrix

Every packaged artifact selected for publication needs its own manual result.
A pass from another architecture or processing build does not carry over.

| Artifact | Required processing evidence |
| --- | --- |
| macOS Apple silicon | CPU transcription plus every Metal/MPS path that the artifact actually advertises or enables. Record the selected device and prove an accelerated workflow did not silently fall back. |
| macOS Intel, if retained | CPU transcription and representative CPU search/indexing. |
| Windows CPU | CPU transcription and representative CPU search/indexing using the CPU package. |
| Windows CUDA | NVIDIA device detection plus actual CUDA transcription and video indexing/search, with GPU allocation or utilization evidence. Completion after a CPU fallback is not a CUDA pass. |

The release owner must remove an artifact from the publication plan or complete
its row in the applicable checklist. The source checkout is tested separately
and does not replace packaged-artifact evidence.

## macOS release verification

Use the
[Version 1 macOS release checklist](release-checklists/version-1-macos.md)
for macOS artifacts. It covers source and packaged startup, shutdown, FFmpeg,
difficult notification text, architecture/device processing, transcription,
queue behavior, search, Assistant, Resolve, and copied stable-release user
data.

The checklist starts with every result set to **Not run**. Record evidence for
each pass, failure, or blocked check. Do not infer a manual pass from the
automated suite.

## Windows release verification

Use the
[Version 1 Windows release checklist](release-checklists/version-1-windows.md)
for Windows CPU and CUDA artifacts.

The CPU and CUDA packages are separate release environments and must be
validated independently. A successful CUDA job must include evidence that the
packaged runtime detected and used the intended NVIDIA GPU; successful
completion alone is not sufficient because processing may otherwise have
fallen back to CPU.
