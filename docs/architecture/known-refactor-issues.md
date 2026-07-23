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
