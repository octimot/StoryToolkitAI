"""Architecture tests for advanced search ownership."""

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SEARCH_SOURCE_PATH = (
    PROJECT_ROOT
    / "storytoolkitai"
    / "core"
    / "toolkit_ops"
    / "search.py"
)

TK_UI_SOURCE_PATH = (
    PROJECT_ROOT
    / "storytoolkitai"
    / "ui"
    / "toolkit_ui.py"
)


def parse_source(path: Path) -> ast.Module:
    """Parse one source file without importing heavyweight dependencies."""

    return ast.parse(
        path.read_text(encoding="utf-8"),
        filename=str(path),
    )


def test_search_processing_does_not_receive_toolkit_ops():
    """Search processors must depend only on their narrow SearchConfig."""

    tree = parse_source(SEARCH_SOURCE_PATH)
    forbidden_names = {
        "ToolkitOps",
        "stAI",
        "toolkit_ops_obj",
    }
    violations = [
        (node.lineno, node.id)
        for node in ast.walk(tree)
        if (
            isinstance(node, ast.Name)
            and node.id in forbidden_names
        )
    ]
    violations.extend(
        (node.lineno, node.arg)
        for node in ast.walk(tree)
        if (
            isinstance(node, ast.arg)
            and node.arg in forbidden_names
        )
    )
    violations.extend(
        (node.lineno, node.attr)
        for node in ast.walk(tree)
        if (
            isinstance(node, ast.Attribute)
            and node.attr in forbidden_names
        )
    )

    assert not violations


def test_tk_ui_does_not_construct_search_processors():
    """Tk must ask StoryToolkitEngine to create search processors."""

    tree = parse_source(TK_UI_SOURCE_PATH)
    constructed_names = {
        (
            node.func.id
            if isinstance(node.func, ast.Name)
            else node.func.attr
        )
        for node in ast.walk(tree)
        if (
            isinstance(node, ast.Call)
            and (
                (
                    isinstance(node.func, ast.Name)
                    and node.func.id in {"TextSearch", "VideoSearch"}
                )
                or (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"TextSearch", "VideoSearch"}
                )
            )
        )
    }

    assert not constructed_names


def test_tk_ui_does_not_keep_live_search_processors():
    """Tk windows and callbacks must retain only an engine search ID."""

    tree = parse_source(TK_UI_SOURCE_PATH)
    forbidden_names = {
        "text_search_item",
        "video_search_item",
    }
    references = {
        node.id
        for node in ast.walk(tree)
        if (
            isinstance(node, ast.Name)
            and node.id in forbidden_names
        )
    }
    references.update(
        node.attr
        for node in ast.walk(tree)
        if (
            isinstance(node, ast.Attribute)
            and node.attr in forbidden_names
        )
    )

    assert not references


def test_tk_ui_does_not_prepare_search_processing():
    """Corpus and model preparation belong to the engine."""

    tree = parse_source(TK_UI_SOURCE_PATH)
    processing_calls = {
        node.func.attr
        for node in ast.walk(tree)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {
                "load_index_paths",
                "prepare_search_corpus",
            }
        )
    }

    assert not processing_calls
