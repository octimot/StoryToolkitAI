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

## R01 — DaVinci Resolve API does not connect on macOS with Resolve 20+

| Field                        | Detail                                                                                                                                                                                                                                                     |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **First observed**           | During the StoryToolkitAI 1.0 architecture migration, after Steps 1–6.                                                                                                                                                                                     |
| **Environment**              | macOS with DaVinci Resolve 20 or newer.                                                                                                                                                                                                                    |
| **Observed behavior**        | StoryToolkitAI does not establish a Resolve API connection.                                                                                                                                                                                                |
| **Known comparison**         | Not yet reproduced against the last pre-refactor commit, the current `main` branch or an older Resolve release using the same machine and Python environment.                                                                                              |
| **Possible external factor** | The machine is using a newer major Resolve release than the previously working setup. This has not yet been confirmed as the cause.                                                                                                                        |
| **Current decision**         | Do not change Resolve integration while completing the remaining architecture refactor steps.                                                                                                                                                              |
| **Future check**             | Compare `main` and `dev` using the same Resolve installation, StoryToolkitAI settings and Python environment. Verify Resolve external scripting configuration, API availability and supported Python runtime before attributing the issue to the refactor. |
| **Regression range**         | Unknown.                                                                                                                                                                                                                                                   |
| **Status**                   | Deferred                                                                                                                                                                                                                                                   |

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
