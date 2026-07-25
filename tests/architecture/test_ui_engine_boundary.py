import ast

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
UI_ROOT = PROJECT_ROOT / "storytoolkitai" / "ui"

# UI code may import UI-independent models from the toolkit_ops package, but
# it must not import processing coordinators, queues or Resolve internals.
FORBIDDEN_MODULE_ENDINGS = (
    "toolkit_ops.assistant",
    "toolkit_ops.toolkit_ops",
    "toolkit_ops.processing_queue",
    "toolkit_ops.search",
    "integrations.mots_resolve",
)

# These names belong to processing implementation details and must not become
# part of the Tk or CLI object graph again.
FORBIDDEN_NAMES = {
    "AssistantUtils",
    "ChatGPT",
    "MotsResolve",
    "NLE",
    "ProcessingQueue",
    "SearchItem",
    "TextSearch",
    "ToolkitAssistant",
    "ToolkitOps",
    "VideoSearch",
    "toolkit_ops_obj",
}

# Attribute access is checked separately so indirect references such as
# object.resolve_api cannot bypass the import checks above.
FORBIDDEN_ATTRIBUTES = {
    "_assistant_sessions",
    "_get_assistant_item",
    "_search_session_manager",
    "_toolkit_ops",
    "processing_queue",
    "queue_history",
    "queue_threads",
    "queue_variables",
    "resolve_api",
    "text_search_item",
    "toolkit_ops_obj",
    "video_search_item",
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


def _is_type_checking_guard(node: ast.AST) -> bool:
    """Return whether an if-test is the standard TYPE_CHECKING guard."""

    return (
        isinstance(node, ast.Name)
        and node.id == "TYPE_CHECKING"
    ) or (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "typing"
        and node.attr == "TYPE_CHECKING"
    )


def _runtime_nodes(tree: ast.AST) -> list[ast.AST]:
    """Return executable nodes while ignoring type-checking-only bodies."""

    nodes: list[ast.AST] = []

    class RuntimeNodeVisitor(ast.NodeVisitor):

        def generic_visit(self, node: ast.AST) -> None:
            nodes.append(node)
            super().generic_visit(node)

        def visit_If(self, node: ast.If) -> None:
            nodes.append(node)

            if not _is_type_checking_guard(node.test):
                self.visit(node.test)

                for statement in node.body:
                    self.visit(statement)

            for statement in node.orelse:
                self.visit(statement)

    RuntimeNodeVisitor().visit(tree)
    return nodes


def _is_forbidden_module(module_name: str) -> bool:
    """
    Return whether an imported module exposes a processing implementation.
    """

    return any(
        module_name == module_ending
        or module_name.endswith("." + module_ending)
        or (
            "." + module_ending + "."
            in "." + module_name + "."
        )
        for module_ending in FORBIDDEN_MODULE_ENDINGS
    )


def _literal_attribute_name(node: ast.Call) -> str | None:
    """Return a literal name used by getattr/hasattr, when present."""

    if not (
        isinstance(node.func, ast.Name)
        and node.func.id in {"getattr", "hasattr"}
        and len(node.args) >= 2
        and isinstance(node.args[1], ast.Constant)
        and isinstance(node.args[1].value, str)
    ):
        return None

    return node.args[1].value


def _literal_dynamic_import(node: ast.Call) -> str | None:
    """Return a literal module passed to a supported dynamic importer."""

    is_import_call = (
        isinstance(node.func, ast.Name)
        and node.func.id in {"__import__", "import_module"}
    ) or (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "import_module"
    )

    if not (
        is_import_call
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    ):
        return None

    return node.args[0].value


def test_ui_uses_no_wildcard_imports():
    """
    Require every dependency used by an interface to be named explicitly.
    """

    violations = []

    for file_path in _ui_python_files():
        tree = _parse_python_file(file_path)

        for node in _runtime_nodes(tree):
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

        for node in _runtime_nodes(tree):
            if isinstance(node, ast.Import):
                imported_modules = [
                    alias.name
                    for alias in node.names
                ]
                imported_names = []

            elif isinstance(node, ast.ImportFrom):
                imported_modules = [
                    node.module or ""
                ]
                imported_names = [
                    alias.name
                    for alias in node.names
                ]

            elif isinstance(node, ast.Call):
                dynamic_module = _literal_dynamic_import(node)

                if dynamic_module is None:
                    continue

                imported_modules = [dynamic_module]
                imported_names = []

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

            for imported_name in imported_names:
                if imported_name not in FORBIDDEN_NAMES:
                    continue

                violations.append(
                    "{}:{} imports implementation name {}".format(
                        _display_path(file_path),
                        node.lineno,
                        imported_name,
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

        for node in _runtime_nodes(tree):
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

            elif isinstance(node, ast.Call):
                attribute_name = _literal_attribute_name(node)

                if attribute_name not in FORBIDDEN_ATTRIBUTES:
                    continue

                violations.append(
                    "{}:{} dynamically accesses attribute {}".format(
                        _display_path(file_path),
                        node.lineno,
                        attribute_name,
                    )
                )

    assert not violations, (
        "UI modules contain processing implementation references:\n"
        + "\n".join(violations)
    )
