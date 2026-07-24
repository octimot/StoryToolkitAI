# Testing StoryToolkitAI

StoryToolkitAI uses pytest for automated tests. The architecture migration introduced a separate set of boundary-checking tests that are faster to run and can be executed independently of the full suite.

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

## Check compilation with warnings

Verify that all Python source files compile cleanly and surface syntax errors and some compile-time warnings early.

```bash
.venv-test/bin/python -m compileall -q -f storytoolkitai tests
```

This does not replace runtime testing, but it catches syntax errors and surfaces some compile-time warnings.

## Heavy processing tests (manual, not in normal CI)

The following require real media files or long-running operations and are not included in the regular automated suite:

- Transcribe a sample audio file end-to-end and verify the output transcription exists.
- Run a text search on an existing project with multiple transcriptions and verify results.
- Create, submit, cancel and re-submit a queue job to exercise the full lifecycle.
- Start a Resolve connection (on macOS or Windows with Resolve installed) and run a marker operation.
- Generate a story via Assistant and export it as EDL/XML.

Run these manually before a release candidate. Record the environment (OS version, Python version, Resolve version if applicable) alongside each test.

## Platform-specific manual checks (release-only)

Before cutting a release candidate on macOS, verify:

1. **Tk startup** — launch the application from the build or installed package; confirm the main window opens without traceback.
2. **Transcription smoke test** — transcribe a short sample audio file and confirm it completes successfully.
3. **Queue restart/recovery** — start processing, terminate the application forcefully (or close normally), reopen and confirm queued jobs are recoverable or reported consistently.
4. **Resolve connection** — on a machine with Resolve running, confirm StoryToolkitAI connects and can read/write timeline markers.
5. **Cancellation** — cancel a running transcription or search job; confirm it stops within a reasonable time and the queue state updates.
6. **OS notification with special characters** — trigger a completion notification for a file whose name contains single quotes or other shell-special characters (e.g., `test'file.wav`); confirm no traceback.
7. **Existing project and transcription compatibility** — open a project created with the previous stable version; confirm all transcriptions load correctly without migration errors.

Record any failures and their environment in the release notes before merging to the stable branch.
