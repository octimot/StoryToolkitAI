"""Tests for search ownership through StoryToolkitEngine."""

from __future__ import annotations

from typing import Any

from storytoolkitai.core.engine import StoryToolkitEngine
from storytoolkitai.core.events import EventEmitter


class FakeTextSearch:
    """Small stateful search processor used by engine tests."""

    def __init__(self) -> None:
        self.search_file_path_id = "search-1"
        self.search_file_paths = ["/tmp/interview.transcription.json"]
        self.search_file_paths_count = 1
        self.search_file_paths_size = 100
        self.model_name = "fake-model"
        self.use_analyzer = False
        self.cache_exists = False


class FakeVideoSearch:
    """Small video search processor used by engine tests."""

    def __init__(self) -> None:
        self.search_file_paths = ["/tmp/interview.npy"]
        self.search_file_paths_count = 1


class FakeProcessingQueue:
    """Queue placeholder required by StoryToolkitEngine."""

    def get_item(self, queue_id: str):
        return None

    def get_all_queue_items(self, status=None, not_status=None):
        return {}

    def set_to_canceled(self, queue_id: str):
        return False


class FakeToolkitOps:
    """Processing object exposing only the methods required by search tests."""

    def __init__(self) -> None:
        self.events = EventEmitter()
        self.processing_queue = FakeProcessingQueue()
        self.text_search_item = FakeTextSearch()
        self.video_search_item = FakeVideoSearch()

    def create_search_items(
        self,
        search_file_paths: list[str],
        use_analyzer: bool = False,
    ) -> tuple[FakeTextSearch, FakeVideoSearch]:
        return self.text_search_item, self.video_search_item


def test_engine_creates_detached_search_information():
    """A caller must not receive mutable engine session state."""

    toolkit_ops = FakeToolkitOps()
    engine = StoryToolkitEngine(toolkit_ops)

    search_info = engine.create_search(
        search_file_paths=["/tmp/interview.transcription.json"],
    )

    search_info["text_file_paths"].append("/tmp/mutated.txt")

    stored_info = engine.get_search("search-1")

    assert stored_info is not None
    assert stored_info["search_id"] == "search-1"
    assert stored_info["status"] == "created"
    assert stored_info["text_file_paths"] == [
        "/tmp/interview.transcription.json"
    ]


def test_engine_reuses_an_open_search_session():
    """Creating the same cached corpus should reuse its engine session."""

    toolkit_ops = FakeToolkitOps()
    engine = StoryToolkitEngine(toolkit_ops)

    first_search = engine.create_search(
        search_file_paths=["/tmp/interview.transcription.json"],
    )
    second_search = engine.create_search(
        search_file_paths=["/tmp/interview.transcription.json"],
    )

    assert first_search["search_id"] == second_search["search_id"]


def test_engine_closes_a_search_session():
    """Closing removes only the engine session registry entry."""

    engine = StoryToolkitEngine(FakeToolkitOps())

    engine.create_search(
        search_file_paths=["/tmp/interview.transcription.json"],
    )

    assert engine.close_search("search-1") is True
    assert engine.get_search("search-1") is None
    assert engine.close_search("search-1") is False
