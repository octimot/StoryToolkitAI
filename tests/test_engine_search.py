"""Tests for search ownership through StoryToolkitEngine."""

from __future__ import annotations

from typing import Any
import time

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
        self.prepared = False

    def prepare_search_corpus(self):
        self.prepared = True
        return [], {}

    def load_model(self, model_name=None):
        if model_name:
            self.model_name = model_name
        return self.model_name

    def search(self, query: str, max_results: int = 5):
        return (
            [
                {
                    "type": "text",
                    "text": query,
                    "metadata": {
                        "source": "fake",
                    },
                }
            ],
            max_results,
        )


class FakeVideoSearch:
    """Small video search processor used by engine tests."""

    def __init__(self) -> None:
        self.search_file_paths = ["/tmp/interview.npy"]
        self.search_file_paths_count = 1
        self.index_paths_loaded = False
        self.model_loaded = False

    def load_index_paths(self):
        self.index_paths_loaded = True

    def load_model(self):
        self.model_loaded = True

    def search(
        self,
        query: str,
        max_results: int = 5,
        threshold: int = 35,
        combine_patches: bool = True,
    ):
        return (
            [
                {
                    "type": "video",
                    "query": query,
                    "frame": 12,
                }
            ],
            1,
        )
    def video_frame(self, full_path: str, frame: int):
        return {
            "full_path": full_path,
            "frame": frame,
        }


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
        self.index_text_calls: list[dict[str, Any]] = []
        self.index_text_queue_calls: list[dict[str, Any]] = []

    def create_search_items(
        self,
        search_file_paths: list[str],
        use_analyzer: bool = False,
    ) -> tuple[FakeTextSearch, FakeVideoSearch]:
        # mirror the real ToolkitOps behavior so the session carries the
        # analyzer choice into direct or queued text indexing
        self.text_search_item.use_analyzer = use_analyzer

        return self.text_search_item, self.video_search_item

    def index_text(self, **kwargs):
        self.index_text_calls.append(kwargs)
        return True

    def add_index_text_to_queue(
        self,
        queue_item_name: str,
        search_file_paths: list[str],
        use_analyzer: bool = False,
    ) -> str:
        """
        Record the exact queue boundary used by SearchSessionManager.

        Keeping an explicit signature prevents tests from hiding mismatches
        between the manager and the real ToolkitOps implementation.
        """

        self.index_text_queue_calls.append(
            {
                "queue_item_name": queue_item_name,
                "search_file_paths": list(search_file_paths),
                "use_analyzer": use_analyzer,
            }
        )

        return "text-index-job"

def wait_for_search_status(
    engine: StoryToolkitEngine,
    search_id: str,
    expected_status: str,
    timeout: float = 2.0,
) -> dict[str, Any]:
    """Wait briefly for the engine-owned search worker."""

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        search_info = engine.get_search(search_id)

        if (
            search_info is not None
            and search_info["status"] == expected_status
        ):
            return search_info

        time.sleep(0.01)

    raise AssertionError(
        "Search {!r} did not reach status {!r}".format(
            search_id,
            expected_status,
        )
    )

def wait_for_index_text_queue_call(
    toolkit_ops: FakeToolkitOps,
    timeout: float = 2.0,
) -> dict[str, Any]:
    """Wait briefly for the engine-owned preparation worker to queue indexing."""

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if toolkit_ops.index_text_queue_calls:
            return toolkit_ops.index_text_queue_calls[-1]

        time.sleep(0.01)

    raise AssertionError(
        "Search preparation did not add a text indexing job to the queue."
    )


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

def test_engine_prepares_search_processors_outside_the_ui():
    """The engine owns text and video preparation."""

    toolkit_ops = FakeToolkitOps()
    engine = StoryToolkitEngine(toolkit_ops)

    search_info = engine.create_search(
        search_file_paths=["/tmp/interview.transcription.json"],
    )

    engine.prepare_search(search_info["search_id"])

    prepared_info = wait_for_search_status(
        engine,
        search_info["search_id"],
        "ready",
    )

    assert prepared_info["text_status"] == "ready"
    assert prepared_info["video_status"] == "ready"
    assert toolkit_ops.text_search_item.prepared is True
    assert toolkit_ops.video_search_item.index_paths_loaded is True
    assert toolkit_ops.video_search_item.model_loaded is True
    assert len(toolkit_ops.index_text_calls) == 1

def test_engine_queues_large_text_search_with_analyzer_setting():
    """Queued indexing must preserve the search session's analyzer choice."""

    toolkit_ops = FakeToolkitOps()

    # force the persistent queue path instead of direct in-thread indexing
    toolkit_ops.text_search_item.search_file_paths_size = 300001
    toolkit_ops.text_search_item.cache_exists = False

    engine = StoryToolkitEngine(toolkit_ops)

    search_info = engine.create_search(
        search_file_paths=[
            "/tmp/interview.transcription.json",
        ],
        use_analyzer=True,
    )

    engine.prepare_search(
        search_id=search_info["search_id"],
        queue_item_name="Indexing interview search",
    )

    queue_call = wait_for_index_text_queue_call(toolkit_ops)

    assert queue_call == {
        "queue_item_name": "Indexing interview search",
        "search_file_paths": [
            "/tmp/interview.transcription.json",
        ],
        "use_analyzer": True,
    }

def test_engine_runs_text_search_with_detached_results():
    """Text search results must not expose processor-owned dictionaries."""

    toolkit_ops = FakeToolkitOps()
    engine = StoryToolkitEngine(toolkit_ops)

    search_info = engine.create_search(
        search_file_paths=["/tmp/interview.transcription.json"],
    )
    engine.prepare_search(search_info["search_id"])
    wait_for_search_status(engine, search_info["search_id"], "ready")

    results, max_results = engine.search_text(
        search_id=search_info["search_id"],
        query="red car",
        max_results=7,
    )

    results[0]["metadata"]["source"] = "mutated"

    second_results, _ = engine.search_text(
        search_id=search_info["search_id"],
        query="red car",
        max_results=7,
    )

    assert max_results == 7
    assert second_results[0]["metadata"]["source"] == "fake"


def test_engine_runs_video_search():
    """Video search execution and its result count pass through the engine."""

    toolkit_ops = FakeToolkitOps()
    engine = StoryToolkitEngine(toolkit_ops)

    search_info = engine.create_search(
        search_file_paths=["/tmp/interview.transcription.json"],
    )
    engine.prepare_search(search_info["search_id"])
    wait_for_search_status(engine, search_info["search_id"], "ready")

    results, max_results = engine.search_video(
        search_id=search_info["search_id"],
        query="red car",
    )

    assert max_results == 1
    assert results == [
        {
            "type": "video",
            "query": "red car",
            "frame": 12,
        }
    ]


def test_engine_returns_video_result_frame():
    """The version 1 frame bridge remains owned by the engine."""

    toolkit_ops = FakeToolkitOps()
    engine = StoryToolkitEngine(toolkit_ops)

    search_info = engine.create_search(
        search_file_paths=["/tmp/interview.transcription.json"],
    )

    frame = engine.get_search_video_frame(
        search_id=search_info["search_id"],
        full_path="/tmp/interview.mov",
        frame=12,
    )

    assert frame == {
        "full_path": "/tmp/interview.mov",
        "frame": 12,
    }
