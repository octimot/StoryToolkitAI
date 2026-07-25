"""
Prevent Tk queue presentation code from bypassing StoryToolkitEngine.

Queue inspection, cancellation, queue ID generation and queue-item mutation
must go through StoryToolkitEngine. The UI may display detached job snapshots,
but it must not access ProcessingQueue directly.
"""

from __future__ import annotations

import ast
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
        tree = ast.parse(source, filename=str(path))

        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {
                    call.rsplit(".", 1)[-1][:-1]
                    for call in FORBIDDEN_QUEUE_CALLS
                }
                and isinstance(node.func.value, ast.Attribute)
                and node.func.value.attr == "processing_queue"
            ):
                continue

            violations.append(
                "{}:{} calls processing_queue.{}".format(
                    path.relative_to(PROJECT_ROOT),
                    node.lineno,
                    node.func.attr,
                )
            )

    assert not violations, (
        "UI queue operations must use StoryToolkitEngine.\n"
        "Replace the following direct ProcessingQueue calls:\n\n"
        + "\n".join(violations)
    )
