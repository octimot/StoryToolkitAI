"""
Protect the runtime and CLI boundaries introduced during Step 10.

The command-line parser may know about command-line arguments. Processing
objects receive explicit runtime decisions and must not inspect argparse
namespaces or command-line flags themselves.

The CLI may use StoryToolkitEngine but must not access ToolkitOps,
StoryToolkitAI or the Resolve API wrapper directly.
"""

from __future__ import annotations

import ast
from pathlib import Path


# This file lives in tests/architecture, so parents[2] is the repository root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

CLI_PATH = (
    PROJECT_ROOT
    / 'storytoolkitai'
    / 'ui'
    / 'toolkit_cli.py'
)
STORYTOOLKITAI_PATH = (
    PROJECT_ROOT
    / 'storytoolkitai'
    / 'core'
    / 'storytoolkitai.py'
)
TOOLKIT_OPS_PATH = (
    PROJECT_ROOT
    / 'storytoolkitai'
    / 'core'
    / 'toolkit_ops'
    / 'toolkit_ops.py'
)


def _read_source(path: Path) -> str:
    return path.read_text(
        encoding='utf-8',
    )


def _parse_source(path: Path) -> ast.Module:
    return ast.parse(
        _read_source(path),
        filename=str(path),
    )


def _find_method(
    tree: ast.Module,
    class_name: str,
    method_name: str,
) -> ast.FunctionDef:

    for node in tree.body:

        if (
            isinstance(node, ast.ClassDef)
            and node.name == class_name
        ):

            for class_node in node.body:

                if (
                    isinstance(class_node, ast.FunctionDef)
                    and class_node.name == method_name
                ):
                    return class_node

    raise AssertionError(
        'Unable to find {}.{}'.format(
            class_name,
            method_name,
        )
    )


def test_cli_does_not_reference_processing_implementation():
    tree = _parse_source(CLI_PATH)

    used_names = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
    }
    used_attributes = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
    }

    assert 'toolkit_ops_obj' not in used_names
    assert 'stAI' not in used_names
    assert 'resolve_api' not in used_attributes

    for node in ast.walk(tree):

        if not isinstance(node, ast.ImportFrom):
            continue

        module_name = node.module or ''

        assert not module_name.startswith(
            'storytoolkitai.core.toolkit_ops'
        )


def test_storytoolkitai_does_not_store_cli_namespace():
    tree = _parse_source(STORYTOOLKITAI_PATH)
    constructor = _find_method(
        tree,
        'StoryToolkitAI',
        '__init__',
    )

    used_attributes = {
        node.attr
        for node in ast.walk(constructor)
        if isinstance(node, ast.Attribute)
    }

    assert 'cli_args' not in used_attributes


def test_toolkit_ops_constructor_does_not_inspect_cli_state():
    tree = _parse_source(TOOLKIT_OPS_PATH)
    constructor = _find_method(
        tree,
        'ToolkitOps',
        '__init__',
    )

    used_attributes = {
        node.attr
        for node in ast.walk(constructor)
        if isinstance(node, ast.Attribute)
    }

    assert 'cli_args' not in used_attributes
