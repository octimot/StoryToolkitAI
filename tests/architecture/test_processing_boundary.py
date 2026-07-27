"""Protect processing code from hidden imports and ambient runtime decisions.

The UI dependency direction is protected by separate architecture tests. This
file enforces two processing-side Version 1 decisions that could otherwise
regress unnoticed:

- boundary modules use explicit imports;
- processing receives runtime decisions explicitly instead of reading the
  ambient command line.
"""

from __future__ import annotations

import ast
from pathlib import Path


# This file lives in tests/architecture, so parents[2] is the repository root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# These processing packages must keep their dependencies explicit.
EXPLICIT_IMPORT_ROOTS = (
    PROJECT_ROOT / "storytoolkitai" / "core" / "toolkit_ops",
    PROJECT_ROOT / "storytoolkitai" / "integrations",
)

# These files form part of the public runtime and engine boundary but live
# outside the processing package roots above.
EXPLICIT_IMPORT_FILES = (
    PROJECT_ROOT / "storytoolkitai" / "app.py",
    PROJECT_ROOT / "storytoolkitai" / "core" / "engine.py",
    PROJECT_ROOT / "storytoolkitai" / "core" / "events.py",
    PROJECT_ROOT / "storytoolkitai" / "core" / "search_sessions.py",
)

# Processing modules must receive runtime policy through constructor arguments
# and RuntimeOptions. Parsing modules and logger configuration are deliberately
# outside this check.
RUNTIME_INPUT_ROOTS = (
    PROJECT_ROOT / "storytoolkitai" / "core" / "toolkit_ops",
    PROJECT_ROOT / "storytoolkitai" / "integrations",
)

RUNTIME_INPUT_FILES = (
    PROJECT_ROOT / "storytoolkitai" / "core" / "storytoolkitai.py",
    PROJECT_ROOT / "storytoolkitai" / "core" / "engine.py",
    PROJECT_ROOT / "storytoolkitai" / "core" / "search_sessions.py",
)


def _python_files(
    roots: tuple[Path, ...],
    files: tuple[Path, ...],
) -> list[Path]:
    """Return a sorted, duplicate-free list of checked Python files."""

    paths = set(files)

    for root in roots:
        if root.exists():
            paths.update(root.rglob("*.py"))

    return sorted(paths)


def _source_line(
    *,
    source: str,
    line_number: int,
) -> str:
    """Return one stripped source line for a useful failure message."""

    lines = source.splitlines()

    if line_number < 1 or line_number > len(lines):
        return "<unknown>"

    return lines[line_number - 1].strip()


def _wildcard_imports_in_file(
    path: Path,
) -> list[tuple[int, str]]:
    """Return prohibited wildcard imports from one Python file."""

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    violations: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue

        if not any(alias.name == "*" for alias in node.names):
            continue

        line_number = getattr(node, "lineno", 0)
        violations.append(
            (
                line_number,
                _source_line(
                    source=source,
                    line_number=line_number,
                ),
            )
        )

    return violations


def _is_sys_argv(node: ast.AST) -> bool:
    """Return whether an AST node is the direct ``sys.argv`` attribute."""

    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "sys"
        and node.attr == "argv"
    )


def _ambient_runtime_reads_in_file(
    path: Path,
) -> list[tuple[int, str]]:
    """Return command-line policy reads from one processing file.

    Process restart and executable-path operations may legitimately use
    ``sys.argv`` or ``sys.argv[0]``. The architecture boundary prohibits
    processing code from branching on command-line flags or retaining the
    parsed argparse namespace.
    """

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    violations: set[tuple[int, str]] = set()

    for node in ast.walk(tree):
        prohibited = False

        # Reject retained argparse state such as ``stAI.cli_args``.
        if isinstance(node, ast.Attribute) and node.attr == "cli_args":
            prohibited = True

        # Reject ``from sys import argv``. Using a local ``argv`` name makes
        # command-line policy reads difficult to distinguish from process
        # restart and executable-path operations.
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module == "sys"
            and any(alias.name == "argv" for alias in node.names)
        ):
            prohibited = True

        # Reject indirect compatibility reads such as
        # ``getattr(stAI, "cli_args", None)``.
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"getattr", "hasattr"}
            and len(node.args) >= 2
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value == "cli_args"
        ):
            prohibited = True

        # Reject command-line policy comparisons such as
        # ``"--debug" in sys.argv`` or ``"--flag" not in sys.argv``.
        elif isinstance(node, ast.Compare):
            compared_values = (
                node.left,
                *node.comparators,
            )

            prohibited = any(
                _is_sys_argv(value)
                for value in compared_values
            )

        if not prohibited:
            continue

        line_number = getattr(node, "lineno", 0)
        violations.add(
            (
                line_number,
                _source_line(
                    source=source,
                    line_number=line_number,
                ),
            )
        )

    return sorted(violations)

def test_processing_boundary_uses_explicit_imports() -> None:
    """Processing boundary modules must not use wildcard imports."""

    violations: list[str] = []

    for root in EXPLICIT_IMPORT_ROOTS:
        if not root.exists():
            violations.append(
                f"Expected source directory does not exist: {root}"
            )

    for path in EXPLICIT_IMPORT_FILES:
        if not path.exists():
            violations.append(
                f"Expected source file does not exist: {path}"
            )

    for path in _python_files(
        roots=EXPLICIT_IMPORT_ROOTS,
        files=EXPLICIT_IMPORT_FILES,
    ):
        if not path.exists():
            continue

        for line_number, source_line in _wildcard_imports_in_file(path):
            relative_path = path.relative_to(PROJECT_ROOT)
            violations.append(
                f"{relative_path}:{line_number}: {source_line}"
            )

    assert not violations, (
        "Processing boundary modules must use explicit imports.\n"
        "Import only the names used by the module instead of importing '*'."
        "\n\n"
        + "\n".join(violations)
    )


def test_processing_does_not_read_ambient_runtime_state() -> None:
    """Processing must receive runtime decisions through explicit inputs."""

    violations: list[str] = []

    for root in RUNTIME_INPUT_ROOTS:
        if not root.exists():
            violations.append(
                f"Expected source directory does not exist: {root}"
            )

    for path in RUNTIME_INPUT_FILES:
        if not path.exists():
            violations.append(
                f"Expected source file does not exist: {path}"
            )

    for path in _python_files(
        roots=RUNTIME_INPUT_ROOTS,
        files=RUNTIME_INPUT_FILES,
    ):
        if not path.exists():
            continue

        for line_number, source_line in _ambient_runtime_reads_in_file(path):
            relative_path = path.relative_to(PROJECT_ROOT)
            violations.append(
                f"{relative_path}:{line_number}: {source_line}"
            )

    assert not violations, (
        "Processing modules must not inspect command-line flags or retained "
        "cli_args.\n"
        "Convert command-line policy into RuntimeOptions before constructing "
        "processing objects.\n\n"
        + "\n".join(violations)
    )
