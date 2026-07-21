"""
Prevent Tk queue presentation code from bypassing StoryToolkitEngine.

Queue inspection, cancellation, queue ID generation and queue-item mutation
must go through StoryToolkitEngine. The UI may display detached job snapshots,
but it must not access ProcessingQueue directly.
"""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
UI_ROOT = PROJECT_ROOT / "storytoolkitai" / "ui"

# Queue reads and cancellation were moved behind StoryToolkitEngine in Step 7.
FORBIDDEN_QUEUE_READ_OR_CANCEL_CALLS = (
    ".processing_queue.get_all_queue_items(",
    ".processing_queue.get_item(",
    ".processing_queue.set_to_canceled(",
    ".processing_queue.cancel_item(",
)

# Queue ID generation and queue-item mutation are moved behind
# StoryToolkitEngine in Step 8.
FORBIDDEN_QUEUE_MUTATION_CALLS = (
    ".processing_queue.generate_queue_id(",
    ".processing_queue.add_to_queue(",
    ".processing_queue.update_queue_item(",
    ".processing_queue.update_status(",
)

FORBIDDEN_QUEUE_CALLS = (
    FORBIDDEN_QUEUE_READ_OR_CANCEL_CALLS
    + FORBIDDEN_QUEUE_MUTATION_CALLS
)


def test_ui_does_not_access_processing_queue_directly() -> None:
    """
    UI modules must use StoryToolkitEngine for queue operations.
    """

    violations: list[str] = []

    for path in sorted(UI_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")

        for forbidden_call in FORBIDDEN_QUEUE_CALLS:
            if forbidden_call not in source:
                continue

            violations.append(
                "{}: contains {}".format(
                    path.relative_to(PROJECT_ROOT),
                    forbidden_call,
                )
            )

    assert not violations, (
        "UI queue operations must use StoryToolkitEngine.\n"
        "Replace the following direct ProcessingQueue calls:\n\n"
        + "\n".join(violations)
    )
