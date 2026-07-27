"""Tests for search ownership through StoryToolkitEngine."""

from __future__ import annotations

from threading import Barrier, Event, Thread, enumerate as enumerate_threads
from typing import Any
import time

from storytoolkitai.core.engine import StoryToolkitEngine
from storytoolkitai.core.events import EventEmitter
from storytoolkitai.core.search_sessions import SearchInfo


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

    def get_item_snapshot(
        self,
        queue_id: str,
        exclude_keys=None,
    ):
        return None

    def get_all_queue_items_snapshot(
        self,
        status=None,
        not_status=None,
        exclude_keys=None,
    ):
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
        self.index_text_queue_result: str | bool = "text-index-job"

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
    ) -> str | bool:
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

        return self.index_text_queue_result


class RotatingSearchToolkitOps(FakeToolkitOps):
    """Return distinct processors that deliberately reuse one search ID."""

    def __init__(self, text_search_items: list[FakeTextSearch]) -> None:
        super().__init__()
        self._text_search_items = iter(text_search_items)

    def create_search_items(
        self,
        search_file_paths: list[str],
        use_analyzer: bool = False,
    ) -> tuple[FakeTextSearch, FakeVideoSearch]:
        text_search_item = next(self._text_search_items)
        text_search_item.use_analyzer = use_analyzer
        video_search_item = FakeVideoSearch()
        self.text_search_item = text_search_item
        self.video_search_item = video_search_item
        return text_search_item, video_search_item


def wait_for_search_status(
    engine: StoryToolkitEngine,
    search_id: str,
    expected_status: str,
    timeout: float = 2.0,
) -> SearchInfo:
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


def wait_for_video_search_status(
    engine: StoryToolkitEngine,
    search_id: str,
    expected_status: str,
    timeout: float = 2.0,
) -> SearchInfo:
    """Wait briefly for one video-search preparation state."""

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        search_info = engine.get_search(search_id)

        if (
            search_info is not None
            and search_info["video_status"] == expected_status
        ):
            return search_info

        time.sleep(0.01)

    raise AssertionError(
        "Search {!r} video component did not reach status {!r}".format(
            search_id,
            expected_status,
        )
    )


def call_in_thread_and_wait(call, timeout: float = 0.5):
    """Call a function in a thread and require it to stay responsive."""

    results = []
    worker = Thread(target=lambda: results.append(call()), daemon=True)
    worker.start()
    worker.join(timeout)

    assert not worker.is_alive(), "The registry call blocked on third-party work."
    return results[0]


def find_preparation_worker(search_id: str, timeout: float = 1.0) -> Thread:
    """Return the preparation worker created for one search session."""

    expected_name = "search-preparation-{}".format(search_id[:8])
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        for worker in enumerate_threads():
            if worker.name == expected_name:
                return worker

        time.sleep(0.01)

    raise AssertionError("Search preparation worker was not started.")


def test_engine_creates_detached_search_information():
    """The public search snapshot has one stable detached dictionary shape."""

    toolkit_ops = FakeToolkitOps()
    engine = StoryToolkitEngine(toolkit_ops)

    search_info = engine.create_search(
        search_file_paths=["/tmp/interview.transcription.json"],
    )

    expected_info: SearchInfo = {
        "search_id": "search-1",
        "status": "created",
        "text_status": "created",
        "video_status": "created",
        "text_file_paths": [
            "/tmp/interview.transcription.json",
        ],
        "video_file_paths": [
            "/tmp/interview.npy",
        ],
        "text_file_count": 1,
        "video_file_count": 1,
        "model_name": "fake-model",
        "text_job_id": None,
        "error": None,
    }

    assert search_info == expected_info

    # Public snapshots must not expose the manager's mutable path lists.
    search_info["text_file_paths"].append("/tmp/mutated.txt")
    search_info["video_file_paths"].append("/tmp/mutated.npy")

    stored_info = engine.get_search("search-1")

    assert stored_info == expected_info


def test_engine_unknown_search_returns_stable_empty_result_shapes():
    """Unknown and closed IDs reject every kind of search work."""

    engine = StoryToolkitEngine(FakeToolkitOps())

    assert engine.search_text(
        search_id="missing-search",
        query="red car",
        max_results=7,
    ) == ([], 7)
    assert engine.search_video(
        search_id="missing-search",
        query="red car",
        max_results=9,
    ) == ([], 9)
    assert engine.prepare_search("missing-search") is None
    assert engine.load_search_model("missing-search", "new-model") is None
    assert engine.get_search_video_frame(
        search_id="missing-search",
        full_path="/tmp/interview.mov",
        frame=12,
    ) is None

    engine.create_search(
        search_file_paths=["/tmp/interview.transcription.json"],
    )
    assert engine.close_search("search-1") is True
    assert engine.prepare_search("search-1") is None
    assert engine.search_text("search-1", "red car") == ([], 5)
    assert engine.search_video("search-1", "red car") == ([], 5)
    assert engine.get_search_video_frame(
        search_id="search-1",
        full_path="/tmp/interview.mov",
        frame=12,
    ) is None


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


def test_status_reads_remain_responsive_during_concurrent_preparation():
    """Preparation and duplicate requests never hold the registry lock."""

    toolkit_ops = FakeToolkitOps()
    prepare_started = Event()
    release_prepare = Event()
    prepare_calls = []

    def blocked_prepare_search_corpus():
        prepare_calls.append(True)
        prepare_started.set()
        assert release_prepare.wait(2.0)
        return [], {}

    toolkit_ops.text_search_item.prepare_search_corpus = (
        blocked_prepare_search_corpus
    )
    engine = StoryToolkitEngine(toolkit_ops)
    search_info = engine.create_search(
        search_file_paths=["/tmp/interview.transcription.json"],
    )
    start_barrier = Barrier(3)

    def request_preparation():
        start_barrier.wait()
        engine.prepare_search(search_info["search_id"])

    callers = [Thread(target=request_preparation) for _ in range(2)]

    try:
        for caller in callers:
            caller.start()

        start_barrier.wait()
        assert prepare_started.wait(1.0)

        for caller in callers:
            caller.join(0.5)
            assert not caller.is_alive()

        current_info = call_in_thread_and_wait(
            lambda: engine.get_search(search_info["search_id"])
        )

        assert current_info is not None
        assert current_info["status"] == "preparing"
        assert len(prepare_calls) == 1
    finally:
        release_prepare.set()

    wait_for_search_status(engine, search_info["search_id"], "ready")


def test_close_during_preparation_discards_late_worker_completion():
    """A closed preparation worker cannot publish work or restore a session."""

    toolkit_ops = FakeToolkitOps()
    prepare_started = Event()
    release_prepare = Event()

    def blocked_prepare_search_corpus():
        prepare_started.set()
        assert release_prepare.wait(2.0)
        return [], {}

    toolkit_ops.text_search_item.prepare_search_corpus = (
        blocked_prepare_search_corpus
    )
    engine = StoryToolkitEngine(toolkit_ops)
    search_info = engine.create_search(
        search_file_paths=["/tmp/interview.transcription.json"],
    )
    engine.prepare_search(search_info["search_id"])
    assert prepare_started.wait(1.0)
    worker = find_preparation_worker(search_info["search_id"])

    assert engine.close_search(search_info["search_id"]) is True
    release_prepare.set()
    worker.join(1.0)

    assert not worker.is_alive()
    assert engine.get_search(search_info["search_id"]) is None
    assert toolkit_ops.index_text_calls == []


def test_late_preparation_cannot_update_same_id_replacement():
    """Identity checks isolate a replacement that reuses a closed search ID."""

    first_text_search = FakeTextSearch()
    replacement_text_search = FakeTextSearch()
    prepare_started = Event()
    release_prepare = Event()

    def blocked_prepare_search_corpus():
        prepare_started.set()
        assert release_prepare.wait(2.0)
        return [], {}

    first_text_search.prepare_search_corpus = blocked_prepare_search_corpus
    toolkit_ops = RotatingSearchToolkitOps(
        [first_text_search, replacement_text_search]
    )
    engine = StoryToolkitEngine(toolkit_ops)
    first_info = engine.create_search(
        search_file_paths=["/tmp/interview.transcription.json"],
    )
    engine.prepare_search(first_info["search_id"])
    assert prepare_started.wait(1.0)
    first_worker = find_preparation_worker(first_info["search_id"])

    assert engine.close_search(first_info["search_id"]) is True
    replacement_info = engine.create_search(
        search_file_paths=["/tmp/interview.transcription.json"],
    )
    release_prepare.set()
    first_worker.join(1.0)

    assert not first_worker.is_alive()
    assert engine.get_search(replacement_info["search_id"]) == replacement_info
    assert replacement_info["status"] == "created"
    assert toolkit_ops.index_text_calls == []


def test_model_loading_remains_responsive_and_discards_after_close():
    """Model loading runs unlocked and returns no late result after close."""

    toolkit_ops = FakeToolkitOps()
    load_started = Event()
    release_load = Event()

    def blocked_load_model(model_name=None):
        load_started.set()
        assert release_load.wait(2.0)
        toolkit_ops.text_search_item.model_name = model_name
        return model_name

    toolkit_ops.text_search_item.load_model = blocked_load_model
    engine = StoryToolkitEngine(toolkit_ops)
    search_info = engine.create_search(
        search_file_paths=["/tmp/interview.transcription.json"],
    )
    result = []
    worker = Thread(
        target=lambda: result.append(
            engine.load_search_model(search_info["search_id"], "new-model")
        )
    )
    worker.start()
    assert load_started.wait(1.0)

    try:
        current_info = call_in_thread_and_wait(
            lambda: engine.get_search(search_info["search_id"])
        )
        assert current_info is not None
        assert engine.close_search(search_info["search_id"]) is True
    finally:
        release_load.set()

    worker.join(1.0)
    assert not worker.is_alive()
    assert result == [None]


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


def test_video_preparation_does_not_clear_text_queue_failure():
    """Concurrent component updates preserve an earlier text-search error."""

    toolkit_ops = FakeToolkitOps()
    toolkit_ops.text_search_item.search_file_paths_size = 300001
    toolkit_ops.text_search_item.cache_exists = False
    toolkit_ops.index_text_queue_result = False

    engine = StoryToolkitEngine(toolkit_ops)
    search_info = engine.create_search(
        search_file_paths=[
            "/tmp/interview.transcription.json",
        ],
    )

    engine.prepare_search(search_info["search_id"])

    prepared_info = wait_for_video_search_status(
        engine,
        search_info["search_id"],
        "ready",
    )

    assert prepared_info["status"] == "failed"
    assert prepared_info["text_status"] == "failed"
    assert prepared_info["video_status"] == "ready"
    assert prepared_info["error"] == (
        "The text search could not be added to the processing queue."
    )

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


def test_status_reads_remain_responsive_and_close_discards_search_result():
    """Active third-party search work neither blocks status nor survives close."""

    toolkit_ops = FakeToolkitOps()
    engine = StoryToolkitEngine(toolkit_ops)
    search_info = engine.create_search(
        search_file_paths=["/tmp/interview.transcription.json"],
    )
    engine.prepare_search(search_info["search_id"])
    wait_for_search_status(engine, search_info["search_id"], "ready")
    search_started = Event()
    release_search = Event()

    def blocked_search(query: str, max_results: int = 5):
        search_started.set()
        assert release_search.wait(2.0)
        return ([{"type": "text", "text": query}], max_results)

    toolkit_ops.text_search_item.search = blocked_search
    result = []
    worker = Thread(
        target=lambda: result.append(
            engine.search_text(search_info["search_id"], "red car", 7)
        )
    )
    worker.start()
    assert search_started.wait(1.0)

    try:
        current_info = call_in_thread_and_wait(
            lambda: engine.get_search(search_info["search_id"])
        )
        assert current_info is not None
        assert current_info["status"] == "ready"
        assert engine.close_search(search_info["search_id"]) is True
    finally:
        release_search.set()

    worker.join(1.0)
    assert not worker.is_alive()
    assert result == [([], 7)]


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


def test_close_during_frame_retrieval_discards_late_frame():
    """A frame already being retrieved may finish but is not returned after close."""

    toolkit_ops = FakeToolkitOps()
    frame_started = Event()
    release_frame = Event()

    def blocked_video_frame(full_path: str, frame: int):
        frame_started.set()
        assert release_frame.wait(2.0)
        return {"full_path": full_path, "frame": frame}

    toolkit_ops.video_search_item.video_frame = blocked_video_frame
    engine = StoryToolkitEngine(toolkit_ops)
    search_info = engine.create_search(
        search_file_paths=["/tmp/interview.transcription.json"],
    )
    result = []
    worker = Thread(
        target=lambda: result.append(
            engine.get_search_video_frame(
                search_id=search_info["search_id"],
                full_path="/tmp/interview.mov",
                frame=12,
            )
        )
    )
    worker.start()
    assert frame_started.wait(1.0)

    assert engine.close_search(search_info["search_id"]) is True
    release_frame.set()
    worker.join(1.0)

    assert not worker.is_alive()
    assert result == [None]
