# Architecture documentation

This directory contains short documents explaining important structural decisions in StoryToolkitAI.

The aim is practical documentation, not formal architecture terminology. Each document should explain:

* the problem being solved;
* the decision that was made;
* the rules maintainers should follow;
* what is intentionally postponed;
* how to tell when the decision has been implemented.

## Current documents

* [`engine-ui-separation.md`](engine-ui-separation.md) — separates UI-independent processing from Tkinter and future user interfaces.

## Maintenance

Update these documents when an architectural rule changes.

Small implementation details do not need an architecture document. Add or revise a document only when the decision affects several modules, future interfaces, compatibility, or the direction of dependencies.
