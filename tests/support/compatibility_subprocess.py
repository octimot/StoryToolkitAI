"""
Run compatibility scenarios that need optional-dependency import stubs.

This module is executed in a child Python process. Its temporary ``torch`` and
``media`` modules therefore disappear with the process and cannot affect
pytest collection order or later imports.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any


REPOSITORY_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _install_torch_stub_if_needed() -> None:
    """Provide only the type check required by ProcessingQueue."""

    try:
        import torch  # noqa: F401
    except ModuleNotFoundError:
        torch_stub = ModuleType("torch")

        class _TorchDevice:
            def __init__(self, device_type: str) -> None:
                self.type = device_type

        torch_stub.device = _TorchDevice
        sys.modules["torch"] = torch_stub


def _install_media_stub() -> None:
    """Avoid importing OpenCV/MoviePy for story JSON and text checks."""

    media_module_name = "storytoolkitai.core.toolkit_ops.media"
    media_stub = ModuleType(media_module_name)

    class _MediaItem:
        def __init__(self, path: str) -> None:
            self.path = path

    media_stub.MediaItem = _MediaItem
    sys.modules[media_module_name] = media_stub


def _compatibility_task(**kwargs: Any) -> dict[str, Any]:
    """Harmless stand-in for a restored processing task."""

    return kwargs


def _story_round_trip(story_path: Path) -> None:
    _install_media_stub()

    from storytoolkitai.core.toolkit_ops.story import Story

    original = _read_json(story_path)
    story = Story(story_file_path=str(story_path))

    assert story.exists is True
    assert story.is_story_file is True
    assert story.to_dict() == original

    story.set("language", "de")
    assert story.save_soon(sec=0)


def _story_text_export(
    story_path: Path,
    export_path: Path,
) -> None:
    _install_media_stub()

    from storytoolkitai.core.toolkit_ops.story import Story, StoryUtils

    story = Story(story_file_path=str(story_path))

    assert story.exists is True
    assert story.is_story_file is True
    StoryUtils.write_txt(story.lines, export_path)


def _queue_recovery(queue_path: Path) -> None:
    _install_torch_stub_if_needed()

    from storytoolkitai.core.engine import StoryToolkitEngine
    from storytoolkitai.core.events import EventEmitter
    from storytoolkitai.core.toolkit_ops import (
        processing_queue as processing_queue_module,
    )
    from storytoolkitai.core.toolkit_ops.processing_queue import (
        ProcessingQueue,
    )

    processing_queue_module.QUEUE_FILE_PATH = str(queue_path)
    queue = ProcessingQueue(
        task_handlers={
            "transcribe": [_compatibility_task],
            "speaker_detection": [_compatibility_task],
        },
    )
    ping_calls: list[list[str]] = []
    queue.ping_queue = (
        lambda: ping_calls.append(list(queue.queue)) or True
    )

    assert queue.resume_queue_from_file(ignore_finished=False) is True
    assert ping_calls
    assert queue.queue == [
        "stable-transcribe",
        "stable-speaker-detection",
    ]
    assert queue.get_status("stable-transcribe") == "queued"
    assert queue.get_status("stable-canceling") == "canceled"
    assert queue.get_status("stable-done") == "done"

    dependent = queue.get_item("stable-speaker-detection")
    assert dependent is not None
    assert dependent["dependencies"] == ["stable-transcribe"]
    assert (
        queue._item_can_start("stable-speaker-detection")
        is False
    )

    queue.update_status("stable-transcribe", "done")
    assert queue._item_can_start("stable-speaker-detection") is True

    toolkit_ops = SimpleNamespace(
        processing_queue=queue,
        events=EventEmitter(),
    )
    engine = StoryToolkitEngine(toolkit_ops_obj=toolkit_ops)
    jobs = engine.list_jobs()

    jobs["stable-speaker-detection"]["task_data"][
        "transcription_file_path"
    ] = "/changed/by/caller.json"

    stored_dependent = queue.get_item("stable-speaker-detection")
    assert stored_dependent is not None
    assert (
        stored_dependent["task_data"]["transcription_file_path"]
        == "/sanitized/interview.transcription.json"
    )
    assert "task_queue" not in jobs["stable-speaker-detection"]

    assert engine.cancel_job("stable-speaker-detection") is True
    assert queue.get_status("stable-speaker-detection") == "canceled"
    assert "stable-speaker-detection" not in queue.queue


def main(arguments: list[str]) -> int:
    if len(arguments) < 2:
        raise ValueError("A compatibility scenario is required.")

    scenario = arguments[1]
    paths = [Path(value) for value in arguments[2:]]

    if scenario == "story_round_trip" and len(paths) == 1:
        _story_round_trip(paths[0])
    elif scenario == "story_text_export" and len(paths) == 2:
        _story_text_export(paths[0], paths[1])
    elif scenario == "queue_recovery" and len(paths) == 1:
        _queue_recovery(paths[0])
    else:
        raise ValueError(
            f"Unknown compatibility scenario or arguments: {scenario}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
