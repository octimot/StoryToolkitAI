"""
Protect the narrow dependency boundary of ProcessingQueue.

The queue may receive task handlers and an event emitter. It must not regain
a dependency on the complete ToolkitOps object.
"""

from __future__ import annotations

import ast
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
    tree = ast.parse(
        source,
        filename=str(PROCESSING_QUEUE_PATH),
    )
    prohibited_names = {
        "ToolkitOps",
        "toolkit_ops_obj",
    }
    violations: list[str] = []

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Name)
            and node.id in prohibited_names
        ):
            violations.append(
                "{}:{} references {}".format(
                    PROCESSING_QUEUE_PATH.relative_to(PROJECT_ROOT),
                    node.lineno,
                    node.id,
                )
            )

        elif (
            isinstance(node, ast.arg)
            and node.arg in prohibited_names
        ):
            violations.append(
                "{}:{} declares {}".format(
                    PROCESSING_QUEUE_PATH.relative_to(PROJECT_ROOT),
                    node.lineno,
                    node.arg,
                )
            )

        elif (
            isinstance(node, ast.Attribute)
            and node.attr in prohibited_names
        ):
            violations.append(
                "{}:{} accesses {}".format(
                    PROCESSING_QUEUE_PATH.relative_to(PROJECT_ROOT),
                    node.lineno,
                    node.attr,
                )
            )

        elif (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "notify_observers"
        ):
            violations.append(
                "{}:{} defines notify_observers".format(
                    PROCESSING_QUEUE_PATH.relative_to(PROJECT_ROOT),
                    node.lineno,
                )
            )

        elif (
            isinstance(node, ast.Call)
            and (
                (
                    isinstance(node.func, ast.Name)
                    and node.func.id == "notify_observers"
                )
                or (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "notify_observers"
                )
            )
        ):
            violations.append(
                "{}:{} calls notify_observers".format(
                    PROCESSING_QUEUE_PATH.relative_to(PROJECT_ROOT),
                    node.lineno,
                )
            )

    assert not violations, (
        "ProcessingQueue must receive only its explicit task handlers and "
        "event emitter.\n"
        + "\n".join(violations)
    )
