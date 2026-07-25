"""Ensure the engine boundary can be imported without loading UI modules."""

from __future__ import annotations

import subprocess
import sys


def test_engine_boundary_imports_without_ui() -> None:
    """Importing the runtime boundary must not load Tk or UI modules."""

    code = """
import sys

import storytoolkitai.app
import storytoolkitai.core.engine
import storytoolkitai.core.events

loaded_modules = set(sys.modules)

assert "tkinter" not in loaded_modules
assert "customtkinter" not in loaded_modules
assert not any(
    name == "storytoolkitai.ui"
    or name.startswith("storytoolkitai.ui.")
    for name in loaded_modules
)
"""

    subprocess.run(
        [sys.executable, "-c", code],
        check=True,
    )


def test_runtime_constructs_without_importing_or_starting_tk() -> None:
    """Real runtime wiring must accept headless processing substitutes.

    StoryToolkitAI and ToolkitOps are replaced because constructing their
    production dependency trees is a separate runtime smoke test. This check
    exercises the real build_runtime function and StoryToolkitEngine wiring.
    """

    code = """
import sys
import types

from storytoolkitai.app import RuntimeOptions, build_runtime
from storytoolkitai.core.engine import StoryToolkitEngine
from storytoolkitai.core.events import EventEmitter


class FakeStoryToolkitAI:
    ffmpeg_checked = False

    @classmethod
    def check_ffmpeg(cls):
        cls.ffmpeg_checked = True

    def __init__(self, **kwargs):
        self.options = kwargs


class FakeProcessingQueue:
    pass


class FakeToolkitOps:
    def __init__(self, **kwargs):
        self.options = kwargs
        self.events = EventEmitter()
        self.processing_queue = FakeProcessingQueue()


storytoolkitai_module = types.ModuleType(
    "storytoolkitai.core.storytoolkitai"
)
storytoolkitai_module.StoryToolkitAI = FakeStoryToolkitAI
sys.modules[storytoolkitai_module.__name__] = storytoolkitai_module

toolkit_ops_module = types.ModuleType(
    "storytoolkitai.core.toolkit_ops.toolkit_ops"
)
toolkit_ops_module.ToolkitOps = FakeToolkitOps
sys.modules[toolkit_ops_module.__name__] = toolkit_ops_module

state, engine = build_runtime(
    RuntimeOptions(
        mode="cli",
        debug=False,
        disable_resolve=True,
        skip_python_check=True,
        resume_queue=False,
        check_api_key=False,
        check_updates=False,
    )
)

assert FakeStoryToolkitAI.ffmpeg_checked is True
assert isinstance(state, FakeStoryToolkitAI)
assert isinstance(engine, StoryToolkitEngine)
assert isinstance(engine._toolkit_ops, FakeToolkitOps)

loaded_modules = set(sys.modules)

assert "tkinter" not in loaded_modules
assert "customtkinter" not in loaded_modules
assert not any(
    name == "storytoolkitai.ui"
    or name.startswith("storytoolkitai.ui.")
    for name in loaded_modules
)
"""

    subprocess.run(
        [sys.executable, "-c", code],
        check=True,
    )
