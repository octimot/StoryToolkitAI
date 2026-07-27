"""Exercise the public runtime wiring without importing the full Tk UI."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ENTRY_PATH = PROJECT_ROOT / "storytoolkitai" / "__main__.py"
TK_UI_PATH = PROJECT_ROOT / "storytoolkitai" / "ui" / "toolkit_ui.py"
CLI_PATH = PROJECT_ROOT / "storytoolkitai" / "ui" / "toolkit_cli.py"


def _load_function(
    path: Path,
    function_name: str,
    namespace: dict[str, Any],
):
    """Load one real function without importing its heavyweight module."""

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == function_name
    )
    module = ast.fix_missing_locations(
        ast.Module(body=[function], type_ignores=[])
    )
    exec(compile(module, str(path), "exec"), namespace)
    return namespace[function_name]


def test_tk_and_cli_entry_points_receive_the_engine() -> None:
    """Both interfaces must operate on the public engine they receive."""

    state = object()
    engine = SimpleNamespace(
        subscribed=[],
        unsubscribed=[],
    )
    engine.subscribe = engine.subscribed.append
    engine.unsubscribe = engine.unsubscribed.append
    gui_activity: list[Any] = []

    class FakeTkUI:
        def __init__(self, *, stAI, engine):
            gui_activity.append(("constructed", stAI, engine))

        def receive_engine_event(self, event):
            gui_activity.append(("event", event))

        def create_main_window(self):
            gui_activity.append("main_window")

        def _stop_engine_event_polling(self):
            gui_activity.append("polling_stopped")

    run_gui = _load_function(
        TK_UI_PATH,
        "run_gui",
        {"toolkit_UI": FakeTkUI},
    )
    run_gui(state, engine)

    assert ("constructed", state, engine) in gui_activity
    assert "main_window" in gui_activity
    assert "polling_stopped" in gui_activity
    assert engine.subscribed
    assert engine.subscribed == engine.unsubscribed

    cli_activity: list[Any] = []

    def fake_cli(*, args, parser, engine):
        cli_activity.append((args, parser, engine))
        return "completed"

    run_cli = _load_function(
        CLI_PATH,
        "run_cli",
        {"toolkit_CLI": fake_cli},
    )
    args = object()
    parser = object()

    assert run_cli(args, parser, engine) == "completed"
    assert (args, parser, engine) in cli_activity


def test_application_entry_point_passes_public_runtime_objects(monkeypatch) -> None:
    """Runtime construction results flow to Tk and CLI without private objects."""

    for mode in ("gui", "cli"):
        args = object()
        parser = object()
        state = object()
        engine = object()
        calls: list[tuple[Any, ...]] = []

        gui_module = ModuleType("storytoolkitai.ui.toolkit_ui")
        gui_module.run_gui = lambda **kwargs: calls.append(
            ("gui", kwargs)
        )
        cli_module = ModuleType("storytoolkitai.ui.toolkit_cli")
        cli_module.run_cli = lambda **kwargs: calls.append(
            ("cli", kwargs)
        )
        monkeypatch.setitem(sys.modules, gui_module.__name__, gui_module)
        monkeypatch.setitem(sys.modules, cli_module.__name__, cli_module)

        main = _load_function(
            APP_ENTRY_PATH,
            "main",
            {
                "build_runtime": lambda options: (state, engine),
                "create_parser": lambda: (parser, args),
                "logger": SimpleNamespace(error=lambda message: None),
                "runtime_options_from_args": lambda value: (
                    SimpleNamespace(mode=mode)
                ),
            },
        )
        main()

        if mode == "gui":
            assert (
                "gui",
                {"stAI": state, "engine": engine},
            ) in calls
            assert not any(call[0] == "cli" for call in calls)
        else:
            assert (
                "cli",
                {
                    "args": args,
                    "parser": parser,
                    "engine": engine,
                },
            ) in calls
            assert not any(call[0] == "gui" for call in calls)
