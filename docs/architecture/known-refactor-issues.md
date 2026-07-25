# Known refactor issues

This file records runtime behaviour noticed during the StoryToolkitAI Version 1 architecture migration that is tracked separately from the architecture boundary.

An entry here does not establish that the refactor caused the issue. Recording it prevents the observation from being lost while architecture and release work continues.

## Status legend

- **Open** — ready to investigate.
- **Deferred** — intentionally postponed until a stated milestone.
- **Investigating** — active comparison or diagnosis is underway.
- **Monitoring** — no longer reproducible, but the cause remains unconfirmed.
- **Resolved** — cause and resolution have been confirmed.
- **Not a regression** — reproduced independently of the refactor.

## R01 — DaVinci Resolve API temporarily failed to connect on macOS with Resolve 20+

| Field | Detail |
| --- | --- |
| **First observed** | During the StoryToolkitAI Version 1 architecture migration. |
| **Environment** | macOS with DaVinci Resolve 20 or newer. |
| **Original behaviour** | StoryToolkitAI did not establish a Resolve API connection. |
| **Current behaviour** | The current development branch establishes the Resolve API connection successfully in the same development environment. |
| **Cause** | Unknown. No specific code or configuration change has been confirmed as the cause of either the original failure or its disappearance. |
| **Regression status** | There is no current evidence of a persistent refactor regression. |
| **Future action** | Reopen the investigation if the connection failure returns. Record exact Resolve, macOS, Python and StoryToolkitAI versions and compare the same environment against the relevant stable branch. |
| **Status** | Monitoring |

### Reopen checklist

If the connection failure returns:

1. Record the exact macOS version and Mac architecture.
2. Record the exact Resolve version and edition.
3. Record the exact Python version and StoryToolkitAI commit.
4. Confirm that external scripting is enabled in Resolve.
5. Confirm that the Resolve scripting modules and required environment variables are available to the Python process.
6. Capture StoryToolkitAI startup and Resolve connection logs.
7. Test the current stable branch in the same environment.
8. Test the current development branch in the same environment.
9. Test an older supported Resolve release when practical.
10. Classify the cause as one of:
    - a StoryToolkitAI regression;
    - a Resolve compatibility change;
    - local Resolve configuration;
    - Python runtime compatibility;
    - scripting-module discovery;
    - another environment issue.
11. Add the confirmed cause, affected versions and resolution to this entry.

## R02 — Queue state and snapshot concurrency

| Field | Detail |
| --- | --- |
| **First observed** | During the Version 1 architecture migration review. |
| **Environment** | All platforms; exposed by the engine boundary change. |
| **Original behaviour** | Queue snapshots were copied from live, unsynchronized internal state. A copy could fail or capture inconsistent data if another thread modified the queue mid-copy. |
| **Current behaviour** | Snapshots are detached copies but remain non-atomic with respect to concurrent queue mutations. |
| **Cause** | The `ProcessingQueue` internal state is not protected by a lock during snapshot construction. |
| **Regression status** | Runtime correctness issue exposed by the new boundary, not a coupling regression. |
| **Future action** | Add a queue-level lock for snapshot construction and concurrent access. This is classified as a release-hardening fix rather than an architecture migration item. |
| **Status** | Open |

## R03 — Tk event-thread scheduling and queue-refresh coalescing

| Field | Detail |
| --- | --- |
| **First observed** | During the Version 1 architecture migration review. |
| **Environment** | All platforms using the Tk interface. |
| **Original behaviour** | Engine listeners may run on processing threads. Some listener paths schedule Tk work indirectly rather than first marshalling the complete event to the Tk event loop. Rapid job events can also enqueue redundant queue refreshes. |
| **Current behaviour** | Engine listeners only place events into a thread-safe Python queue. A bounded callback owned by the Tk thread drains that queue, and rapid `job.changed` events share one pending idle refresh. Shutdown stops polling; an event already entering concurrently may remain in the abandoned queue but cannot reach Tk. |
| **Cause** | Engine listeners run synchronously on the emitting thread, while the original Tk listener did not centralize thread marshalling or refresh coalescing. |
| **Regression status** | Runtime usability concern exposed by the new boundary and event-driven model. |
| **Future action** | Retain the worker-thread delivery, pre-mainloop retention, bounded polling, refresh-coalescing and shutdown lifecycle tests. No lock is required solely to make event rejection atomic during teardown. |
| **Status** | Fixed |

## R04 — macOS notification command quoting

| Field | Detail |
| --- | --- |
| **First observed** | During the Version 1 architecture migration review. |
| **Environment** | macOS using `osascript` for native notifications. |
| **Original behaviour** | Filenames containing single quotes or other shell-special characters in notification content can cause `osascript` to fail with a syntax error. |
| **Current behaviour** | Notification messages and titles are passed to a fixed AppleScript program as process arguments. No shell parses the values, and AppleScript receives them through its `run` handler. The legacy still-render notification is presented by the Tk caller rather than the Resolve integration. |
| **Cause** | The historical macOS notification helper interpolated text into both a shell command and AppleScript source instead of passing it as data. |
| **Regression status** | Runtime correctness issue, not caused by the refactor but worth tracking before release candidate. |
| **Future action** | Retain command-construction tests for quotes, backslashes, newlines, Unicode and shell metacharacters. Before a release candidate, manually trigger a macOS notification with the same characters to verify native presentation. |
| **Status** | Resolved |

## R05 — Tuple identity comparison warning

| Field | Detail |
| --- | --- |
| **First observed** | During the Version 1 architecture migration review. |
| **Environment** | All platforms and supported Python versions. Some Python versions or warning configurations surface a `SyntaxWarning` during compilation. |
| **Original behaviour** | One tuple and two lists were compared using identity (`is` or `is not`) rather than value equality. Identity checks whether two references point to the same object, not whether the containers contain equal values. |
| **Current behaviour** | The timecode sentinel checks use value equality, separately created `(None, None)` and `[None, None]` values take the intended fallback paths, and compilation no longer emits the tuple-literal `SyntaxWarning`. |
| **Cause** | Historical use of identity comparisons where value comparisons were intended. |
| **Regression status** | Potential correctness concern, not caused by the refactor but worth tracking before release candidate. |
| **Future action** | Retain the focused missing-timecode behavior test and the source audit that rejects identity comparisons against container literals. |
| **Status** | Resolved |

## Release issue tracking

The entries above are brief records to prevent these concerns from being lost while the architecture migration finishes. Before the release candidate, each should have a dedicated GitHub issue with reproduction steps and acceptance criteria. The release checklist should link to those issues rather than duplicating detail here.
