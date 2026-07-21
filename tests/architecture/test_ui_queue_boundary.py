"""
Prevent Tk queue presentation code from bypassing StoryToolkitEngine.

This guard is intentionally narrow. Other UI workflows still create and
update queue items directly during the version 1 migration. Step 7 removes
only queue inspection and cancellation from the UI, so those are the calls
protected here.
"""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOLKIT_UI_PATH = (
    PROJECT_ROOT
    / "storytoolkitai"
    / "ui"
    / "toolkit_ui.py"
)

FORBIDDEN_QUEUE_CALLS = (
    ".processing_queue.get_all_queue_items(",
    ".processing_queue.get_item(",
    ".processing_queue.set_to_canceled(",
    ".processing_queue.cancel_item(",
)


def test_ui_does_not_read_or_cancel_jobs_through_processing_queue() -> None:
    """
    Queue snapshots and cancellation must go through StoryToolkitEngine.
    """

    source = TOOLKIT_UI_PATH.read_text(encoding="utf-8")

    violations = [
        forbidden_call
        for forbidden_call in FORBIDDEN_QUEUE_CALLS
        if forbidden_call in source
    ]

    assert not violations, (
        "Tk queue reads and cancellation must use StoryToolkitEngine.\n"
        "Replace the following ProcessingQueue calls:\n\n"
        + "\n".join(violations)
    )
