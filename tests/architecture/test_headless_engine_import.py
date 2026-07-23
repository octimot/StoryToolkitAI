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


