# Known refactor issues

This file records behavior noticed during the StoryToolkitAI 1.0 architecture
migration that is intentionally outside the scope of the current refactor step.

An entry here does not establish that the refactor caused the issue. Recording
it prevents the observation from being lost while unrelated architecture work
continues.

## Status legend

* **Open** — ready to investigate
* **Deferred** — intentionally postponed until a stated migration milestone
* **Investigating** — active comparison or diagnosis is underway
* **Resolved** — cause and resolution have been confirmed
* **Not a regression** — reproduced independently of the refactor

## R01 — DaVinci Resolve API temporarily failed to connect on macOS with Resolve 20+

| Field | Detail |
| --- | --- |
| **First observed** | During the StoryToolkitAI 1.0 architecture migration, after Steps 1–6. |
| **Environment** | macOS with DaVinci Resolve 20 or newer. |
| **Original behavior** | StoryToolkitAI did not establish a Resolve API connection. |
| **Current behavior** | The current `dev` branch now establishes the Resolve API connection successfully in the same development environment. |
| **Cause** | Unknown. No specific code or configuration change has been confirmed as the cause of either the original failure or its disappearance. |
| **Regression status** | No current evidence of a persistent refactor regression. |
| **Future action** | Reopen this investigation if the connection failure returns. Record the exact Resolve, macOS, Python and StoryToolkitAI versions at that time. |
| **Status** | No longer reproducible |                                                                                                                                                                                                                                               |

### Investigation checklist

When the architecture refactor is complete:

1. Record the exact macOS, Resolve and Python versions.
2. Confirm that external scripting is enabled in Resolve.
3. Confirm that the Resolve scripting modules and environment variables are
   available to the Python process.
4. Test the current `main` branch with the same environment.
5. Test the `dev` branch with the same environment.
6. Compare startup and connection logs from both branches.
7. Test an older supported Resolve release when practical.
8. Decide whether the cause is:

   * a StoryToolkitAI regression;
   * a Resolve 20 compatibility change;
   * local configuration;
   * Python runtime compatibility;
   * or another environment issue.
9. Add the confirmed cause, affected versions and resolution to this entry.
