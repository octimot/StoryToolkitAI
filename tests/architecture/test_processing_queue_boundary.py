"""
Protect the narrow dependency boundary of ProcessingQueue.

The queue may receive task handlers and an event emitter. It must not regain
a dependency on the complete ToolkitOps object.
"""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSING_QUEUE_PATH = (
    PROJECT_ROOT
    / "storytoolkitai"
    / "core"
    / "toolkit_ops"
    / "processing_queue.py"
)


def test_processing_queue_does_not_depend_on_toolkit_ops() -> None:
    """ProcessingQueue must not store or call the ToolkitOps object."""

    source = PROCESSING_QUEUE_PATH.read_text(
        encoding="utf-8",
    )

    prohibited_names = (
        "toolkit_ops_obj",
        "notify_observers",
    )

    violations = [
        name
        for name in prohibited_names
        if name in source
    ]

    assert not violations, (
        "ProcessingQueue must receive only its explicit task handlers and "
        "event emitter.\n"
        "Prohibited references: {}".format(
            ", ".join(violations)
        )
    )
