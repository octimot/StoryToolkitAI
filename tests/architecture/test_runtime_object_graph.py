import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

APP_PATH = PROJECT_ROOT / 'storytoolkitai' / 'app.py'
MAIN_PATH = PROJECT_ROOT / 'storytoolkitai' / '__main__.py'
TK_UI_PATH = (
    PROJECT_ROOT
    / 'storytoolkitai'
    / 'ui'
    / 'toolkit_ui.py'
)


def _find_function(
    tree: ast.AST,
    function_name: str,
) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.FunctionDef)
            and node.name == function_name
        ):
            return node

    raise AssertionError(
        'Function {!r} was not found.'.format(
            function_name
        )
    )


def test_tk_ui_does_not_receive_or_store_toolkit_ops():
    source = TK_UI_PATH.read_text(
        encoding='utf-8'
    )

    assert 'toolkit_ops_obj' not in source
    assert 'ToolkitOps' not in source


def test_main_does_not_receive_toolkit_ops():
    source = MAIN_PATH.read_text(
        encoding='utf-8'
    )

    assert 'toolkit_ops_obj' not in source
    assert 'ToolkitOps' not in source


def test_run_gui_accepts_only_application_state_and_engine():
    tree = ast.parse(
        TK_UI_PATH.read_text(
            encoding='utf-8'
        )
    )

    function = _find_function(
        tree,
        'run_gui',
    )

    argument_names = [
        argument.arg
        for argument in function.args.args
    ]

    assert argument_names == [
        'stAI',
        'engine',
    ]


def test_build_runtime_returns_two_public_objects():
    tree = ast.parse(
        APP_PATH.read_text(
            encoding='utf-8'
        )
    )

    function = _find_function(
        tree,
        'build_runtime',
    )

    return_nodes = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Return)
    ]

    tuple_returns = [
        node.value
        for node in return_nodes
        if isinstance(node.value, ast.Tuple)
    ]

    assert len(tuple_returns) == 1
    assert len(tuple_returns[0].elts) == 2

    returned_names = [
        element.id
        for element in tuple_returns[0].elts
        if isinstance(element, ast.Name)
    ]

    assert returned_names == [
        'stAI',
        'engine',
    ]
