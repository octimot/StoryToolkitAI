# Architecture documentation

This directory contains practical documents explaining structural decisions in StoryToolkitAI.

The documentation avoids formal architecture terminology where a plain description is sufficient. Each document should explain:

- the problem being solved;
- the decision that was made;
- the rules maintainers should follow;
- what is intentionally postponed;
- how the decision is checked.

## Current documents

- [`engine-ui-separation.md`](./engine-ui-separation.md) — the Version 1 decision to separate UI-independent processing from Tkinter and other interfaces.
- [`tk-engine-boundary.md`](./tk-engine-boundary.md) — the implemented first-party interface boundary after the Tk, CLI, Resolve, search, queue and assistant migrations.
- [`current-ui-coupling.md`](./current-ui-coupling.md) — the current migration inventory, accepted Version 1 limits and remaining cleanup work.
- [`known-refactor-issues.md`](./known-refactor-issues.md) — runtime behaviour noticed while the architecture work is in progress.

## Document roles

`engine-ui-separation.md` records the decision.

`tk-engine-boundary.md` records the implemented boundary that current code must preserve.

`current-ui-coupling.md` records remaining exceptions and follow-up work. It may change frequently until the Version 1 architecture work is complete.

`known-refactor-issues.md` records behaviour that must be classified as a regression, compatibility issue or unrelated external problem before release.

## Maintenance

Update an architecture document when a rule, dependency direction or accepted boundary changes.

Small implementation details do not need architecture documentation. Add or revise a document only when the change affects several modules, first-party interfaces, compatibility, testing, packaging or future process separation.

When a boundary is enforced by a test, keep the document and test aligned. A documentation statement must not claim a stronger boundary than the tests and current code actually enforce.
