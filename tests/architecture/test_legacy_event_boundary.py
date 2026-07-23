"""
Prevent callback-shaped processing refresh actions from returning.

Processing publishes named EngineEvent values. Historical callback names may
still exist inside the Tk presentation layer, but they must not be used as a
processing communication mechanism.
"""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

# These packages belong to the UI-independent processing side.
CHECKED_ROOTS = (
    PROJECT_ROOT / "storytoolkitai" / "core",
    PROJECT_ROOT / "storytoolkitai" / "integrations",
)

# These strings previously told processing which UI callback to invoke.
# Tk may use equivalent local names for its own window callbacks, but
# processing must communicate with named EngineEvent types instead.
LEGACY_REFRESH_ACTIONS = {
    "project_changed",
    "update_NLE_status",
    "update_all_transcriptions",
    "NLE_project_changed",
    "NLE_timeline_changed",
    "NLE_markers_changed",
    "NLE_bin_changed",
    "NLE_tc_changed",
    "NLE_timecode_data_changed",
    "update_transcription_",
    "update_transcription_{}",
    "update_transcription_groups_",
    "update_transcription_groups_{}",
}


def _processing_python_files() -> list[Path]:
    """Return all Python files belonging to the processing side."""

    files: list[Path] = []

    for checked_root in CHECKED_ROOTS:
        files.extend(
            sorted(
                checked_root.rglob("*.py")
            )
        )

    return files


def _parse_python_file(file_path: Path) -> ast.AST:
    """Parse one processing file for architecture-level inspection."""

    return ast.parse(
        file_path.read_text(encoding="utf-8"),
        filename=str(file_path),
    )


def _display_path(file_path: Path) -> str:
    """Return a stable repository-relative path for assertion messages."""

    return str(
        file_path.relative_to(PROJECT_ROOT)
    )


def _called_name(node: ast.Call) -> str | None:
    """Return the simple name used by one function or method call."""

    if isinstance(node.func, ast.Name):
        return node.func.id

    if isinstance(node.func, ast.Attribute):
        return node.func.attr

    return None


def test_processing_does_not_define_or_call_notify_observers() -> None:
    """The removed processing observer bridge must not return."""

    violations: list[str] = []

    for file_path in _processing_python_files():
        tree = _parse_python_file(file_path)

        for node in ast.walk(tree):
            if (
                isinstance(
                    node,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                    ),
                )
                and node.name == "notify_observers"
            ):
                violations.append(
                    "{}:{} defines notify_observers".format(
                        _display_path(file_path),
                        node.lineno,
                    )
                )

            elif (
                isinstance(node, ast.Call)
                and _called_name(node) == "notify_observers"
            ):
                violations.append(
                    "{}:{} calls notify_observers".format(
                        _display_path(file_path),
                        node.lineno,
                    )
                )

    assert not violations, (
        "Processing must publish named EngineEvent values instead of using "
        "the removed notify_observers compatibility bridge:\n"
        + "\n".join(violations)
    )


def test_processing_contains_no_legacy_refresh_action_strings() -> None:
    """Historical UI callback names must remain outside processing."""

    violations: list[str] = []

    for file_path in _processing_python_files():
        tree = _parse_python_file(file_path)

        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value in LEGACY_REFRESH_ACTIONS
            ):
                continue

            violations.append(
                "{}:{} contains legacy refresh action {!r}".format(
                    _display_path(file_path),
                    node.lineno,
                    node.value,
                )
            )

    assert not violations, (
        "Processing contains callback-shaped refresh action strings. "
        "Publish a named EngineEvent instead:\n"
        + "\n".join(violations)
    )
