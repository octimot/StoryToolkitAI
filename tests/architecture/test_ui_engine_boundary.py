import ast

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
UI_ROOT = PROJECT_ROOT / "storytoolkitai" / "ui"

# UI code may import UI-independent models from the toolkit_ops package, but
# it must not import processing coordinators, queues or Resolve internals.
FORBIDDEN_MODULE_ENDINGS = (
    "toolkit_ops.toolkit_ops",
    "toolkit_ops.processing_queue",
    "integrations.mots_resolve",
)

# These names belong to processing implementation details and must not become
# part of the Tk or CLI object graph again.
FORBIDDEN_NAMES = {
    "NLE",
    "ProcessingQueue",
    "ToolkitOps",
    "toolkit_ops_obj",
}

# Attribute access is checked separately so indirect references such as
# object.resolve_api cannot bypass the import checks above.
FORBIDDEN_ATTRIBUTES = {
    "processing_queue",
    "resolve_api",
    "toolkit_ops_obj",
}


def _ui_python_files() -> list[Path]:
    """
    Return every Python source file belonging to a first-party interface.
    """

    return sorted(UI_ROOT.rglob("*.py"))


def _parse_python_file(file_path: Path) -> ast.AST:
    """
    Parse one Python file for architecture-level source inspection.
    """

    return ast.parse(
        file_path.read_text(encoding="utf-8"),
        filename=str(file_path),
    )


def _display_path(file_path: Path) -> str:
    """
    Return a stable project-relative path for assertion messages.
    """

    return str(file_path.relative_to(PROJECT_ROOT))


def _is_forbidden_module(module_name: str) -> bool:
    """
    Return whether an imported module exposes a processing implementation.
    """

    return any(
        module_name == module_ending
        or module_name.endswith("." + module_ending)
        for module_ending in FORBIDDEN_MODULE_ENDINGS
    )


def test_ui_uses_no_wildcard_imports():
    """
    Require every dependency used by an interface to be named explicitly.
    """

    violations = []

    for file_path in _ui_python_files():
        tree = _parse_python_file(file_path)

        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue

            if not any(alias.name == "*" for alias in node.names):
                continue

            violations.append(
                "{}:{} imports * from {}".format(
                    _display_path(file_path),
                    node.lineno,
                    node.module or "<relative module>",
                )
            )

    assert not violations, (
        "UI modules must not use wildcard imports:\n"
        + "\n".join(violations)
    )


def test_ui_does_not_import_processing_implementations():
    """
    Prevent interfaces from importing processing coordinators or integrations.
    """

    violations = []

    for file_path in _ui_python_files():
        tree = _parse_python_file(file_path)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules = [
                    alias.name
                    for alias in node.names
                ]

            elif isinstance(node, ast.ImportFrom):
                imported_modules = [
                    node.module or ""
                ]

            else:
                continue

            for module_name in imported_modules:
                if not _is_forbidden_module(module_name):
                    continue

                violations.append(
                    "{}:{} imports {}".format(
                        _display_path(file_path),
                        node.lineno,
                        module_name,
                    )
                )

    assert not violations, (
        "UI modules must access processing through StoryToolkitEngine:\n"
        + "\n".join(violations)
    )


def test_ui_does_not_reference_processing_implementation_names():
    """
    Prevent legacy processing objects from returning to the UI object graph.
    """

    violations = []

    for file_path in _ui_python_files():
        tree = _parse_python_file(file_path)

        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Name)
                and node.id in FORBIDDEN_NAMES
            ):
                violations.append(
                    "{}:{} references name {}".format(
                        _display_path(file_path),
                        node.lineno,
                        node.id,
                    )
                )

            elif (
                isinstance(node, ast.arg)
                and node.arg in FORBIDDEN_NAMES
            ):
                violations.append(
                    "{}:{} declares argument {}".format(
                        _display_path(file_path),
                        node.lineno,
                        node.arg,
                    )
                )

            elif (
                isinstance(node, ast.Attribute)
                and node.attr in FORBIDDEN_ATTRIBUTES
            ):
                violations.append(
                    "{}:{} accesses attribute {}".format(
                        _display_path(file_path),
                        node.lineno,
                        node.attr,
                    )
                )

    assert not violations, (
        "UI modules contain processing implementation references:\n"
        + "\n".join(violations)
    )
