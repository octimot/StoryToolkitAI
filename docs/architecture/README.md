# Architecture documentation

This directory contains practical documents explaining structural decisions in StoryToolkitAI.

The documentation prefers plain language over formal architecture terminology. Each document should explain:

- the problem being solved;
- the decision that was made;
- the rules maintainers should follow;
- what is intentionally postponed;
- how the decision is checked.

## Current documents

- [`engine-ui-separation.md`](./engine-ui-separation.md) — the Version 1 decision to separate UI-independent processing from first-party interfaces.
- [`tk-engine-boundary.md`](./tk-engine-boundary.md) — the implemented Tk, CLI and engine boundary that current code must preserve.
- [`current-ui-coupling.md`](./current-ui-coupling.md) — the closed Version 1 coupling inventory and accepted in-process limits.
- [`known-refactor-issues.md`](./known-refactor-issues.md) — runtime behaviour noticed during the migration that may still require compatibility monitoring.

## Document roles

`engine-ui-separation.md` records the architectural decision and its Version 1 scope.

`tk-engine-boundary.md` records the implemented first-party interface boundary and the checks that protect it.

`current-ui-coupling.md` records the completed migration state, resolved coupling and accepted Version 1 limits. Version 2 work should use a separate migration plan instead of reopening this inventory.

`known-refactor-issues.md` records behaviour that must remain classified as a regression, compatibility issue, monitoring item or unrelated external problem.

## Maintenance

Update an architecture document when a dependency direction, public boundary or accepted limitation changes. Small implementation details do not need architecture documentation.

Add or revise a document only when a decision affects several modules, first-party interfaces, compatibility, testing, packaging or future process separation.

When a boundary is enforced by a test, keep the document and test aligned. A document must not claim a stronger boundary than the tests and current code enforce.
