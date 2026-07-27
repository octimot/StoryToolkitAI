# Version 1 Windows release checklist

**Scope:** Manual Version 1 release verification on Windows

**Initial status:** Not run

**Required for:** The final `v1.0.0` source tree and every Windows artifact
selected for publication.

This checklist records checks that automated and mocked tests cannot prove.
Unchecked items are **Not run**, not passed.

Use only `Pass`, `Fail`, `Blocked`, or `Not run` in the result record. A pass
requires evidence from the exact source checkout or packaged artifact being
tested.

## Result record

| Check                             | Result  | Evidence or issue |
| --------------------------------- | ------- | ----------------- |
| Source startup                    | Not run |                   |
| Packaged CPU startup              | Not run |                   |
| Packaged CUDA startup             | Not run |                   |
| Installer, upgrade, and uninstall | Not run |                   |
| Clean shutdown                    | Not run |                   |
| FFmpeg discovery                  | Not run |                   |
| CPU transcription                 | Not run |                   |
| CUDA device detection             | Not run |                   |
| CUDA transcription                | Not run |                   |
| CUDA video indexing/search        | Not run |                   |
| CUDA cancellation and recovery    | Not run |                   |
| Text search                       | Not run |                   |
| Assistant configuration           | Not run |                   |
| Resolve source connection         | Not run |                   |
| Resolve packaged connection       | Not run |                   |
| Stable-release user data          | Not run |                   |

## Environment record

Record before testing:

* [ ] Windows edition, version, and OS build:
* [ ] CPU architecture and installed RAM:
* [ ] available disk space:
* [ ] Python version used by the source checkout:
* [ ] StoryToolkitAI commit:
* [ ] CPU artifact filename and checksum:
* [ ] CUDA artifact filename and checksum:
* [ ] installer signing status and build source commit:
* [ ] GPU model and VRAM:
* [ ] NVIDIA driver version:
* [ ] `nvidia-smi` output:
* [ ] `torch.__version__`:
* [ ] `torch.version.cuda`:
* [ ] `torch.cuda.is_available()`:
* [ ] `torch.cuda.get_device_name(0)`:
* [ ] FFmpeg path and version:
* [ ] transcription model and model-cache state:
* [ ] text- and video-search model/cache state:
* [ ] Resolve version, edition, scripting configuration, and test project:
* [ ] current stable StoryToolkitAI version used for compatibility data:
* [ ] log locations and release issue:

## Preparation and data safety

* [ ] Run the full automated suite, compilation check, and `git diff --check`.
* [ ] Follow the
  [packaged-application test procedure](../testing.md#packaged-application-test-procedure),
  and build or obtain the exact CPU and CUDA artifacts being considered for
  release.
* [ ] Prepare short licensed or synthetic audio and video with known content.
* [ ] Create a disposable Resolve project and timeline.
* [ ] Copy stable-release project, transcription, story, queue, and settings
  data into an isolated test directory.
* [ ] Preserve the original compatibility data read-only.
* [ ] Record hashes or recursive file listings before opening copied data.

## 1. Source startup

* [ ] Launch the GUI from a clean source environment.
* [ ] Confirm the main window opens without import errors or traceback.
* [ ] Open settings and queue windows.
* [ ] Confirm normal input and redraw remain responsive.
* [ ] Record startup time and logs.

Pass when the source GUI is usable and no release-blocking startup error occurs.

## 2. Packaged startup

Repeat separately for the CPU and CUDA artifacts:

* [ ] Install the exact recorded artifact on a clean Windows user profile or
  equivalent test environment.
* [ ] Record Microsoft Defender or SmartScreen behavior.
* [ ] Launch from the Start menu or installed shortcut.
* [ ] Confirm all bundled dependencies are available.
* [ ] Quit and launch again.
* [ ] Confirm paths containing spaces and Unicode are handled correctly.
* [ ] Record screenshots and packaged logs.

A CPU-artifact pass is not evidence for the CUDA artifact, and the reverse is
also true.

## 3. Installer, upgrade, and uninstall

* [ ] Perform a clean installation.
* [ ] Upgrade from the current stable release where supported.
* [ ] Confirm existing user data is not deleted by the installer.
* [ ] Confirm installation outside `Program Files` where that remains the
  documented recommendation.
* [ ] Uninstall the application.
* [ ] Confirm application files are removed without deleting user projects.
* [ ] Reinstall and confirm startup remains healthy.

## 4. FFmpeg discovery

Repeat for source, CPU package, and CUDA package:

* [ ] Record the discovered FFmpeg executable.
* [ ] Confirm it is the intended bundled, configured, or `PATH` binary.
* [ ] Run the discovered executable with `-version`.
* [ ] Ingest representative media.
* [ ] Configure an invalid FFmpeg path in a disposable profile.
* [ ] Confirm the failure is reported without crashing.

## 5. CPU transcription

* [ ] Explicitly select CPU processing.
* [ ] Transcribe representative media.
* [ ] Confirm progress, cancellation, completion, save, reopen, and export.
* [ ] Confirm the log and application state report CPU rather than CUDA.
* [ ] Restart and reopen the result.

## 6. CUDA device detection

Use the CUDA artifact on a supported NVIDIA system:

* [ ] Record `nvidia-smi`.
* [ ] Record Torch and CUDA runtime information from the packaged application
  environment.
* [ ] Confirm `torch.cuda.is_available()` is true.
* [ ] Confirm the expected GPU name appears.
* [ ] Confirm StoryToolkitAI offers/selects the CUDA device.
* [ ] Confirm CUDA initialization produces no missing-DLL or driver error.

Pass only when the packaged runtime detects the intended GPU.

## 7. CUDA transcription

* [ ] Select CUDA explicitly.
* [ ] Begin a representative transcription.
* [ ] Observe process GPU memory or utilization using `nvidia-smi`.
* [ ] Confirm the application does not silently fall back to CPU.
* [ ] Confirm progress remains responsive.
* [ ] Save, reopen, and export the result.
* [ ] Record model, duration, peak GPU memory, and processing time.

A completed transcription without evidence of GPU use is not a CUDA pass.

## 8. CUDA video indexing and search

* [ ] Index short video with known visual content using CUDA where supported.
* [ ] Observe GPU allocation or utilization.
* [ ] Run a known-content search.
* [ ] Inspect thumbnails, frames, timestamps, and source association.
* [ ] Close the search during active work and confirm late work is discarded.
* [ ] Record model, cache state, peak GPU memory, and processing time.

## 9. CUDA failure behavior

* [ ] Test CUDA selection with insufficient or unavailable support using a safe
  prepared environment where practical.
* [ ] Confirm an incompatible driver, missing runtime, or unavailable device
  produces a clear error.
* [ ] Confirm the application does not falsely report CUDA processing.
* [ ] Confirm any CPU fallback is explicit and documented.
* [ ] Confirm the UI remains usable after the failure.

Do not deliberately destabilize a production workstation or run an unsafe
out-of-memory workload solely for this check.

## 10. Queue cancellation, dependencies, and recovery

Repeat at least one active-job scenario with CUDA:

* [ ] Cancel a queued job.
* [ ] Cancel an active CUDA job.
* [ ] Confirm state progresses consistently to its terminal value.
* [ ] Run a dependent workflow and confirm dependencies do not start early.
* [ ] Preserve an unfinished resumable job and restart the application.
* [ ] Confirm restored state is readable and does not duplicate processing.
* [ ] Complete or cancel recovered work and restart again.

## 11. Search and Assistant

* [ ] Run representative text search.
* [ ] Run representative video search.
* [ ] Confirm UI responsiveness during model preparation.
* [ ] Configure one supported Assistant provider.
* [ ] Send a non-sensitive request.
* [ ] Test unavailable credentials or model configuration.
* [ ] Confirm failures are useful and do not crash the application.

## 12. Resolve integration

Repeat required checks for source and packaged applications:

* [ ] Configure Resolve external scripting.
* [ ] Connect to a disposable project and timeline.
* [ ] Read existing markers.
* [ ] Write, update, and remove a reversible test marker.
* [ ] Move the playhead to a known timecode.
* [ ] Start Resolve playback and exercise harmless StoryToolkitAI window input;
  confirm the application does not block waiting for Resolve until playback
  stops. If it does, capture logs and open a release issue.
* [ ] Import representative media into a test bin.
* [ ] Run a safe monitored operation.
* [ ] Disconnect and reconnect.
* [ ] Attach StoryToolkitAI and Resolve logs.

A source pass is not a packaged-artifact pass.

## 13. Existing stable-release data

Work only on the isolated copy:

* [ ] Open the copied project.
* [ ] Verify linked transcriptions, stories, documents, timelines, and markers.
* [ ] Open every copied transcription and story.
* [ ] Spot-check timestamps, Unicode, groups, speaker/meta data, and media paths.
* [ ] Save one reversible edit.
* [ ] Compare JSON key sets and unrelated nested values before and after.
* [ ] Confirm the transcription `incomplete` field survives unchanged.
* [ ] Export representative outputs.
* [ ] Quit, relaunch, and reopen the project.
* [ ] Confirm the original stable-release data remains untouched.

## Completion

* [ ] Every result is updated from `Not run`, or a release issue explicitly
  accepts a blocked item.
* [ ] Every pass identifies the exact artifact and environment.
* [ ] CUDA passes include evidence that GPU execution actually occurred.
* [ ] Failures include logs and reproduction steps.
* [ ] Automated, mocked, CPU, and CUDA evidence remain clearly separated.
* [ ] No credentials, private media, or model files were committed.
* [ ] Release notes describe accepted platform limitations.
