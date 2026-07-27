# Version 1 macOS release checklist

**Scope:** Manual Version 1 release verification on macOS

**Initial status:** Not run

**Required for:** The final `v1.0.0` source tree and every macOS artifact
selected for publication.

This checklist records checks that the automated suite cannot prove. Every
item is manual unless it explicitly points to prior automated coverage.
Unchecked items are **Not run**, not passed.

Use only `Pass`, `Fail`, `Blocked`, or `Not run` in the result record. A pass
requires the stated observation and evidence from the environment being
tested. Do not claim that model, hardware, packaged-application, Notification
Center, Assistant-provider, or Resolve behavior passed based on mocks.

## Result record

Copy this table into the release issue or release notes and fill it in without
removing failed or blocked rows.

| Check | Result | Evidence or issue |
| --- | --- | --- |
| Source startup | Not run | |
| Packaged-application startup | Not run | |
| Clean shutdown | Not run | |
| FFmpeg discovery | Not run | |
| Apple silicon supported/MPS processing | Not run | |
| Intel CPU processing, if published | Not run | |
| Difficult notification content | Not run | |
| Representative transcription | Not run | |
| Queue progress and cancellation | Not run | |
| Queue dependencies and recovery | Not run | |
| Text search | Not run | |
| Video search | Not run | |
| Assistant configuration | Not run | |
| Resolve source connection and timeline operations | Not run | |
| Resolve packaged connection and timeline operations | Not run | |
| Stable-release user data | Not run | |

## Environment record

Record before testing:

- [ ] macOS version and build:
- [ ] Mac model and Intel/Apple silicon architecture:
- [ ] available RAM and free disk space:
- [ ] Python version used by the source checkout:
- [ ] StoryToolkitAI commit:
- [ ] packaged artifact filename, architecture, checksum,
      signing/notarization status, and build source commit:
- [ ] current stable StoryToolkitAI version used to prepare compatibility
      data:
- [ ] FFmpeg path and `ffmpeg -version` first line:
- [ ] transcription model name, device, and model-cache state:
- [ ] text-search model name and model-cache state:
- [ ] video-search model name and model-cache state:
- [ ] Assistant provider and model, with secrets omitted:
- [ ] Resolve version, edition, scripting mode, and active test project:
- [ ] log locations and release issue:

## Preparation and data safety

- [ ] Run the complete automated suite, compile check, and `git diff --check`
      separately. Attach their output; do not treat it as manual evidence.
- [ ] Follow the
      [packaged-application test procedure](../testing.md#packaged-application-test-procedure),
      and build the packaged application from the recorded commit using the
      maintainer-approved release build procedure.
- [ ] Prepare short licensed or synthetic audio/video with known speech and
      searchable visual content. Keep large media and model files outside the
      repository.
- [ ] Create a disposable Resolve project and timeline. Timeline writes,
      markers, media imports, and renders below must not target production
      projects.
- [ ] In the current stable release, make a project containing at least one
      transcription, story, document, timeline entry, and representative
      export.
- [ ] Quit the stable release, then copy that project's data and any relevant
      queue/settings data to an isolated test user-data directory. Preserve the
      originals read-only.
- [ ] Record hashes or a recursive file listing of the copied JSON/story files
      before opening them in Version 1. Exclude expected logs and caches from
      schema comparisons.
- [ ] Back up the test user-data directory before any recovery or forced-exit
      scenario.

## 1. Source startup

- [ ] With Resolve closed and no development server already running, launch
      the GUI from the source checkout:

      ```bash
      .venv/bin/python -m storytoolkitai --mode gui
      ```

- [ ] Confirm the main window becomes usable without a traceback, unexpected
      modal loop, or import error.
- [ ] Open the queue and settings windows and confirm basic input/redraw
      remains responsive.
- [ ] Record startup logs and elapsed time to a usable main window.

Pass when the source GUI is usable and logs contain no release-blocking startup
error.

## 2. Packaged-application startup

- [ ] Test the exact recorded release artifact, not a different local build.
- [ ] Launch once through Finder on a clean macOS user account or an equivalent
      clean test profile.
- [ ] Confirm Gatekeeper/signing behavior is expected and the main window
      becomes usable without a traceback or missing bundled dependency.
- [ ] Quit and launch it again to exercise initialized user-data state.
- [ ] Record screenshots and packaged-application logs.

Pass when both first and subsequent packaged launches are usable.

## 3. Clean shutdown

Repeat for source and packaged runs:

- [ ] Start and then close a search window, Assistant window, and queue window.
- [ ] Quit using the normal application command while no job is active.
- [ ] Confirm the application exits without a hang, traceback, orphaned GUI
      process, or continuing worker activity.
- [ ] Start a safe short job, wait for it to finish, and quit again.
- [ ] Relaunch and confirm persisted project/queue state is readable.

Pass when normal shutdown completes cleanly and the next launch is healthy.
Forced exit used for queue recovery is recorded separately and is not a clean
shutdown pass.

## 4. FFmpeg discovery

Repeat the applicable checks for source and packaged runs:

- [ ] With the expected FFmpeg installation/bundle available, start with debug
      logging and record the discovered executable path.
- [ ] Confirm the path is the intended configured, colocated, bundled, or
      `PATH` executable rather than an unrelated binary.
- [ ] Run `"<recorded-path>" -version` and record the version.
- [ ] Ingest the representative media and confirm no false “FFmpeg not found”
      warning appears.
- [ ] In a disposable profile, configure an invalid custom FFmpeg path and
      confirm the failure is reported without crashing. Restore the valid
      configuration afterward.

Pass when discovery selects a working intended binary in both release
environments and the invalid-path case fails safely.

## 5. Architecture and processing device paths

Complete the applicable subsection for every macOS artifact selected for
publication. A source pass does not replace packaged evidence, and an Apple
silicon pass does not cover an Intel artifact.

### Apple silicon

- [ ] Record whether the artifact and each tested workflow advertise CPU,
      Metal/MPS, or another supported device path.
- [ ] Run a representative transcription on its supported device path and
      record the device reported by application logs.
- [ ] Run representative text/video search or indexing on the device path each
      workflow actually selects.
- [ ] Where a workflow advertises or enables Metal/MPS, record
      `torch.backends.mps.is_available()`, exercise that workflow, and capture
      evidence that it did not silently fall back to CPU.
- [ ] Where a workflow currently supports CPU only, record that limitation
      explicitly rather than reporting an MPS pass.
- [ ] Repeat the processing smoke check with the exact packaged Apple silicon
      artifact.

### Intel, if retained

- [ ] Run representative CPU transcription and confirm the log reports CPU.
- [ ] Run representative CPU text search and video indexing/search.
- [ ] Repeat with the exact packaged Intel artifact.
- [ ] Record CPU model, processing times, and any accepted performance limit.

Pass each subsection only for the architecture and device path actually
exercised. If an Intel artifact is not being published, record it as not
applicable in the release issue rather than silently omitting it.

## 6. Notification handling with difficult filenames

Automated tests verify command construction only. Native Notification Center
presentation remains manual.

- [ ] Create or copy test media whose displayed filename/content includes
      double quotes, apostrophes, backslashes, Unicode, spaces, and shell
      metacharacters such as `$`, backticks, `;`, and `&`.
- [ ] Include a newline in notification text through a safe test path if the UI
      supports it; do not use shell interpolation to create or pass the value.
- [ ] Trigger a real completion notification from the application.
- [ ] Confirm title and message are displayed as data, special characters are
      unchanged, no command is executed, and no AppleScript traceback appears.
- [ ] Repeat with the packaged application and record a screenshot plus logs.

Pass when difficult content is presented literally and safely in both source
and packaged runs.

## 7. Real or representative transcription

- [ ] Ingest the prepared audio/video through the normal UI.
- [ ] Record model, device, language/task settings, media duration, and start
      time.
- [ ] Observe queue progress changing while the application remains
      responsive.
- [ ] Confirm processing completes and creates a transcription that opens with
      plausible timestamps and text.
- [ ] Save, close, and reopen the transcription.
- [ ] Export SRT and TXT and inspect timestamps, Unicode, line ordering, and
      expected omission of meta/speaker segments.
- [ ] Relaunch the application and reopen the result.

Pass when one end-to-end representative transcription completes and its saved
and exported results remain readable. Record quality observations separately
from runtime compatibility.

## 8. Queue progress, cancellation, dependencies, and recovery

Use disposable media and preserve logs for each scenario.

- [ ] Submit a normal transcription and confirm queued, processing, progress,
      and terminal state changes appear consistently.
- [ ] Cancel a queued job and confirm it becomes canceled without starting.
- [ ] Cancel an active job and confirm it enters the expected canceling state,
      finishes or stops the current non-interruptible work safely, then becomes
      canceled without running remaining tasks.
- [ ] Submit a workflow with a dependent job, such as speaker detection after
      transcription. Confirm the dependent job does not start early.
- [ ] Confirm a successful dependency allows the dependent job to start and
      required data is available to it.
- [ ] In a separate run, make the prerequisite fail or become unavailable and
      confirm the dependent job does not run as if successful.
- [ ] Leave at least one resumable job unfinished, preserve `queue.json`, and
      quit or force-terminate only as planned for this recovery scenario.
- [ ] Relaunch and confirm resumable jobs, finished/canceled history policy,
      progress reset, interrupted cancellation, and dependency order are
      represented consistently.
- [ ] Complete or cancel recovered work, relaunch again, and confirm the queue
      remains readable.

Pass when visible state matches actual execution and recovery neither loses a
resumable job nor starts a dependent job prematurely.

## 9. Text search

- [ ] Use a project with multiple saved transcriptions and known query terms.
- [ ] Prepare/index through the normal UI and record model/cache state.
- [ ] Confirm status reads and other UI actions remain responsive during model
      preparation and search.
- [ ] Run exact and semantic queries with known expected matches.
- [ ] Open representative results and verify the source/timestamp association.
- [ ] Close a search during active work and confirm no late result reopens or
      corrupts the closed session.
- [ ] Relaunch and repeat one query against persisted index data where
      supported.

Pass when known matches are returned, lifecycle behavior is safe, and the UI
remains responsive.

## 10. Video search

- [ ] Use short prepared video with known visual content and record the model,
      cache state, device, and media paths.
- [ ] Prepare/index through the normal UI and confirm status reads remain
      responsive.
- [ ] Search for known visual content and inspect returned thumbnails/frames
      and timestamps.
- [ ] Open or navigate to a representative result if supported.
- [ ] Close the search during active preparation or retrieval and confirm late
      work does not restore a closed session.
- [ ] Record model/download time separately from search time.

Pass when known visual content produces usable frame results without lifecycle
or responsiveness regressions.

## 11. Assistant configuration

- [ ] Configure one supported Assistant provider/model using a test account or
      approved local model; do not place credentials in logs or evidence.
- [ ] Open an Assistant session and send a small non-sensitive query.
- [ ] Confirm a response is displayed and the UI remains responsive.
- [ ] Replace the configured model/provider in the same session where
      supported and confirm the session remains usable.
- [ ] Exercise representative transcription or story context and save a
      generated story only to the disposable project.
- [ ] Relaunch and confirm non-secret settings load as expected.
- [ ] Test an invalid/missing credential or unavailable model and confirm a
      useful error is shown without crashing.

Pass when valid configuration works and invalid configuration fails safely.

## 12. Resolve connection and representative timeline operations

Complete the environment and diagnostic requirements in
[R01's manual Version 1 verification](../architecture/known-refactor-issues.md#manual-version-1-verification).
Run this section separately for source and packaged applications.

- [ ] Enable Resolve external scripting, open the disposable project and
      timeline, and start StoryToolkitAI with debug logging.
- [ ] Confirm connection state reports the active project and timeline.
- [ ] Start StoryToolkitAI before Resolve once, then open Resolve and use the
      manual connection command; confirm the connection recovers.
- [ ] Read existing timeline markers.
- [ ] Write, update, and remove a reversible uniquely named test marker.
- [ ] Move the Resolve playhead to a known timecode and confirm it does not
      continue moving unexpectedly.
- [ ] Start Resolve playback and exercise harmless StoryToolkitAI window input;
      confirm the application does not block waiting for Resolve until playback
      stops. If it does, capture logs and open a release issue.
- [ ] Import a small representative media item into the intended test bin.
- [ ] Run one safe representative timeline/render-monitor operation supported
      by the UI and confirm progress/terminal state is reported.
- [ ] Disable and reconnect once; confirm project, timeline, marker, and
      connection display clears and repopulates correctly.
- [ ] Repeat the connection and reversible marker/playhead checks with the
      packaged application.
- [ ] Attach Resolve and StoryToolkitAI logs. If connection fails, complete
      R01's reopen checklist before classifying the cause.

Pass only for the environment actually exercised. A source pass is not a
packaged pass, and mocked Resolve tests are not evidence for either.

## 13. Existing user data copied from the stable release

Work only on the isolated copy prepared above.

- [ ] Open the copied stable-release project and verify its name, linked
      transcriptions, stories, documents, timelines, markers, and last export
      directory.
- [ ] Open every copied transcription and story; spot-check segment/line
      counts, timestamps, Unicode, groups, notes, speaker/meta data, and linked
      media paths.
- [ ] Save one copied transcription and one copied story after a reversible
      edit. Compare JSON key sets and nested structures before/after, allowing
      only the requested edit and documented modification metadata.
- [ ] Confirm the persisted transcription `incomplete` flag remains present
      and retains its boolean value when no code intentionally changes it.
- [ ] Export representative SRT/TXT and story EDL/XML outputs and compare them
      with stable-release output or document every intentional difference.
- [ ] Open queue/settings copies where compatible and confirm failures are
      reported rather than silently discarded.
- [ ] Quit, relaunch, and reopen the project.
- [ ] Confirm the original stable-release data remains untouched and record
      hashes/listings for the modified test copy.

Pass when the copied data opens and remains structurally compatible without an
undocumented migration or silent field loss.

## Completion

- [ ] Every result row is updated from `Not run`, or a release issue explicitly
      accepts a `Blocked` item.
- [ ] Failures include logs, reproduction steps, affected artifact, and whether
      the same behavior occurs in the current stable release.
- [ ] Automated, mocked, and manual evidence are labeled separately.
- [ ] No secrets, private user content, or large media/model files were added
      to the repository or release issue.
- [ ] Release notes list any accepted compatibility limitation.

The checklist is complete only when the release owner signs off the recorded
results. This document itself does not assert that any manual check passed.
