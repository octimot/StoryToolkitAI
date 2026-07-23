"""Prevent processing-owned packages from importing the UI package.

This is intentionally a narrow architecture guard. It protects the dependency
direction established for Version 1:

    UI -> StoryToolkitEngine -> processing

and never:

    processing -> UI

In-process Version 1 bridges that remain intentionally supported are recorded
in ``docs/architecture/current-ui-coupling.md``.
"""

from __future__ import annotations

import ast
from pathlib import Path


# This file lives in tests/architecture, so parents[2] is the repository root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Add another processing-owned package here only when it is intentionally part
# of the UI-independent engine boundary.
CHECKED_ROOTS = (
    PROJECT_ROOT / "storytoolkitai" / "core",
    PROJECT_ROOT / "storytoolkitai" / "integrations",
)

UI_PACKAGE = "storytoolkitai.ui"


def _is_ui_module(module_name: str) -> bool:
    """Return True when an absolute import targets the UI package."""

    return module_name == UI_PACKAGE or module_name.startswith(f"{UI_PACKAGE}.")


def _relative_import_targets_ui(node: ast.ImportFrom) -> bool:
    """Detect relative imports whose first named module is ``ui``.

    Examples caught by this helper include ``from ..ui import ...`` and
    ``from ..ui.toolkit_ui import ...``. Absolute imports are handled
    separately.
    """

    if node.level == 0:
        return False

    module_name = node.module or ""
    if module_name == "ui" or module_name.startswith("ui."):
        return True

    # Also catch forms such as ``from .. import ui``.
    return not module_name and any(
        alias.name == "ui" or alias.name.startswith("ui.")
        for alias in node.names
    )


def _ui_imports_in_file(path: Path) -> list[tuple[int, str]]:
    """Return ``(line_number, source)`` entries for prohibited imports."""

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    lines = source.splitlines()
    violations: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        prohibited = False

        if isinstance(node, ast.Import):
            prohibited = any(_is_ui_module(alias.name) for alias in node.names)

        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            prohibited = _is_ui_module(module_name) or _relative_import_targets_ui(node)

        if prohibited:
            line_number = getattr(node, "lineno", 0)
            source_line = lines[line_number - 1].strip() if line_number else "<unknown>"
            violations.append((line_number, source_line))

    return violations


def test_core_and_integrations_do_not_import_ui() -> None:
    """Core processing and integrations must remain independent of UI code."""

    violations: list[str] = []

    for checked_root in CHECKED_ROOTS:
        if not checked_root.exists():
            # A missing expected package is more likely a checkout/layout error
            # than an architecture success, so report it clearly.
            violations.append(f"Expected source directory does not exist: {checked_root}")
            continue

        for path in sorted(checked_root.rglob("*.py")):
            for line_number, source_line in _ui_imports_in_file(path):
                relative_path = path.relative_to(PROJECT_ROOT)
                violations.append(f"{relative_path}:{line_number}: {source_line}")

    assert not violations, (
        "Processing-owned packages must not import storytoolkitai.ui.\n"
        "Move presentation behavior to the UI and communicate through the "
        "engine/event boundary instead.\n\n"
        + "\n".join(violations)
    )
