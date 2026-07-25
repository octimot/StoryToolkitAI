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


def _find_method(
    tree: ast.Module,
    class_name: str,
    method_name: str,
) -> ast.FunctionDef:
    for node in tree.body:
        if not (
            isinstance(node, ast.ClassDef)
            and node.name == class_name
        ):
            continue

        for class_node in node.body:
            if (
                isinstance(class_node, ast.FunctionDef)
                and class_node.name == method_name
            ):
                return class_node

    raise AssertionError(
        '{}.{} was not found.'.format(
            class_name,
            method_name,
        )
    )


def _parse_file(path: Path) -> ast.Module:
    return ast.parse(
        path.read_text(encoding='utf-8'),
        filename=str(path),
    )


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id

    if isinstance(node.func, ast.Attribute):
        return node.func.attr

    return None


def _keyword_is_name(
    node: ast.Call,
    keyword_name: str,
    expected_name: str,
) -> bool:
    return any(
        keyword.arg == keyword_name
        and isinstance(keyword.value, ast.Name)
        and keyword.value.id == expected_name
        for keyword in node.keywords
    )


def test_run_gui_accepts_only_application_state_and_engine():
    tree = _parse_file(TK_UI_PATH)

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


def test_run_gui_passes_engine_to_tk_and_subscribes_queue_entry_point():
    tree = _parse_file(TK_UI_PATH)
    function = _find_function(
        tree,
        'run_gui',
    )

    calls = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
    ]

    toolkit_ui_calls = [
        call
        for call in calls
        if _call_name(call) == 'toolkit_UI'
    ]
    assert len(toolkit_ui_calls) == 1
    assert _keyword_is_name(
        toolkit_ui_calls[0],
        'stAI',
        'stAI',
    )
    assert _keyword_is_name(
        toolkit_ui_calls[0],
        'engine',
        'engine',
    )

    subscriptions = [
        call
        for call in calls
        if (
            isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id == 'engine'
            and call.func.attr == 'subscribe'
        )
    ]
    assert len(subscriptions) == 1
    assert len(subscriptions[0].args) == 1

    listener = subscriptions[0].args[0]
    assert (
        isinstance(listener, ast.Attribute)
        and isinstance(listener.value, ast.Name)
        and listener.value.id == 'app_UI'
        and listener.attr == 'receive_engine_event'
    )


def test_worker_event_entry_point_only_writes_to_thread_safe_inbox():
    tree = _parse_file(TK_UI_PATH)
    method = _find_method(
        tree,
        'toolkit_UI',
        'receive_engine_event',
    )

    calls = [
        node
        for node in ast.walk(method)
        if isinstance(node, ast.Call)
    ]

    assert len(calls) == 1

    queue_write = calls[0]
    assert (
        isinstance(queue_write.func, ast.Attribute)
        and queue_write.func.attr == 'put'
        and isinstance(queue_write.func.value, ast.Attribute)
        and isinstance(queue_write.func.value.value, ast.Name)
        and queue_write.func.value.value.id == 'self'
        and queue_write.func.value.attr == '_engine_events'
    )

    direct_self_attributes = {
        node.attr
        for node in ast.walk(method)
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == 'self'
        )
    }

    assert direct_self_attributes <= {
        '_accept_engine_events',
        '_engine_events',
    }


def test_build_runtime_returns_two_public_objects():
    tree = _parse_file(APP_PATH)

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

    engine_calls = [
        node
        for node in ast.walk(function)
        if (
            isinstance(node, ast.Call)
            and _call_name(node) == 'StoryToolkitEngine'
        )
    ]

    assert len(engine_calls) == 1
    assert _keyword_is_name(
        engine_calls[0],
        'toolkit_ops_obj',
        'toolkit_ops',
    )


def test_main_passes_only_the_public_engine_to_tk_and_cli():
    tree = _parse_file(MAIN_PATH)
    function = _find_function(
        tree,
        'main',
    )

    runtime_assignments = [
        node
        for node in ast.walk(function)
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Call)
            and _call_name(node.value) == 'build_runtime'
        )
    ]

    assert len(runtime_assignments) == 1
    assert len(runtime_assignments[0].targets) == 1

    target = runtime_assignments[0].targets[0]
    assert isinstance(target, ast.Tuple)
    assert [
        element.id
        for element in target.elts
        if isinstance(element, ast.Name)
    ] == [
        'stAI',
        'engine',
    ]

    interface_calls = [
        node
        for node in ast.walk(function)
        if (
            isinstance(node, ast.Call)
            and _call_name(node) in {'run_gui', 'run_cli'}
        )
    ]
    calls_by_name = {
        interface_name: [
            call
            for call in interface_calls
            if _call_name(call) == interface_name
        ]
        for interface_name in ('run_gui', 'run_cli')
    }

    assert len(calls_by_name['run_gui']) == 1
    assert len(calls_by_name['run_cli']) == 1
    assert _keyword_is_name(
        calls_by_name['run_gui'][0],
        'engine',
        'engine',
    )
    assert _keyword_is_name(
        calls_by_name['run_cli'][0],
        'engine',
        'engine',
    )
