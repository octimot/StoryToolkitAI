from __future__ import annotations

from typing import Any

import pytest

from storytoolkitai.core.engine import StoryToolkitEngine
from storytoolkitai.core.events import EngineEvent, EventEmitter


def _fake_task(**kwargs: Any) -> dict[str, Any]:
    """Runtime-only callable used to verify that tasks are not exposed."""

    return kwargs


class FakeProcessingQueue:
    """
    Minimal queue replacement for testing the engine facade.

    The fake deliberately returns references to its internal dictionaries. This
    lets the tests prove that StoryToolkitEngine detaches data before returning
    it to callers.
    """

    def __init__(self) -> None:
        self.items: dict[str, dict[str, Any]] = {
            "job-queued": {
                "queue_id": "job-queued",
                "name": "Queued job",
                "status": "queued",
                "tasks": "test_task",
                "task_data": {
                    "source": "example.wav",
                    "options": {
                        "language": "en",
                    },
                },
                "device": "cpu",
                "task_queue": [_fake_task],
                "last_task": _fake_task,
                "output": [
                    {
                        "temporary": True,
                    }
                ],
            },
            "job-done": {
                "queue_id": "job-done",
                "name": "Completed job",
                "status": "done",
                "tasks": "test_task",
                "task_data": {
                    "source": "finished.wav",
                },
                "device": "cpu",
                "task_queue": [_fake_task],
            },
        }

        self.last_status_filter: str | list[str] | None = None
        self.last_not_status_filter: str | list[str] | None = None
        self.cancel_requests: list[str] = []
        self.generated_names: list[str | None] = []
        self.updated_items: list[dict[str, Any]] = []

    def get_item(self, queue_id: str) -> dict[str, Any] | None:
        """Return the real stored item, matching current queue behaviour."""

        return self.items.get(queue_id)

    def get_all_queue_items(
        self,
        status: str | list[str] | None = None,
        not_status: str | list[str] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Apply the current queue filters and return stored item references."""

        self.last_status_filter = status
        self.last_not_status_filter = not_status

        included_statuses = [status] if isinstance(status, str) else status
        excluded_statuses = (
            [not_status]
            if isinstance(not_status, str)
            else not_status
        )

        selected_items: dict[str, dict[str, Any]] = {}

        for job_id, item in self.items.items():
            if (
                included_statuses is not None
                and item.get("status") not in included_statuses
            ):
                continue

            if (
                excluded_statuses is not None
                and item.get("status") in excluded_statuses
            ):
                continue

            selected_items[job_id] = item

        return selected_items

    def generate_queue_id(
        self,
        name: str | None = None,
    ) -> str:
        """Create a pending queue item and return its generated ID."""

        self.generated_names.append(name)

        queue_id = "job-generated-{}".format(
            len(self.generated_names),
        )

        self.items[queue_id] = {
            "queue_id": queue_id,
            "name": "",
            "status": "pending",
        }

        return queue_id

    def update_queue_item(
        self,
        queue_id: str,
        **kwargs: Any,
    ) -> dict[str, Any] | bool:
        """Update a fake queue item using the real queue method's shape."""

        item = self.items.get(queue_id)

        if item is None:
            return False

        item.update(kwargs)
        item["queue_id"] = queue_id

        self.updated_items.append(
            {
                "queue_id": queue_id,
                **kwargs,
            }
        )

        return item

    def set_to_canceled(
        self,
        queue_id: str,
    ) -> dict[str, Any] | None:
        """Record and perform a simple safe cancellation request."""
        self.cancel_requests.append(queue_id)

        item = self.items.get(queue_id)
        if item is None:
            return None

        if item.get("status") in {"done", "failed", "canceled"}:
            return None

        item["status"] = "canceled"
        return item


class FakeToolkitOps:
    """ToolkitOps replacement containing the engine's current dependencies."""

    def __init__(self) -> None:
        # the real ToolkitOps owns one shared emitter,
        # the fake mirrors that public shape without
        # importing the heavyweight processing module.
        self.events = EventEmitter()
        self.processing_queue = FakeProcessingQueue()
        self.ingest_requests: list[Any] = []

    def add_media_to_queue(
        self,
        ingest_settings: Any,
    ) -> list[str]:
        """Record an ingest request and return a representative queue ID."""

        self.ingest_requests.append(ingest_settings)

        return ["job-ingest"]


@pytest.fixture
def toolkit_ops() -> FakeToolkitOps:
    """Return fresh fake operations for each test."""

    return FakeToolkitOps()


@pytest.fixture
def engine(toolkit_ops: FakeToolkitOps) -> StoryToolkitEngine:
    """Return an engine using the fake operations object."""

    return StoryToolkitEngine(
        toolkit_ops_obj=toolkit_ops,
    )


def test_get_job_returns_none_for_unknown_job(
    engine: StoryToolkitEngine,
) -> None:
    """Unknown queue IDs are represented as a missing job."""

    assert engine.get_job("missing-job") is None


def test_get_job_returns_detached_public_data(
    engine: StoryToolkitEngine,
    toolkit_ops: FakeToolkitOps,
) -> None:
    """
    Job data returned by the engine cannot mutate the queue's stored item.
    """

    job = engine.get_job("job-queued")

    assert job is not None

    assert job["queue_id"] == "job-queued"
    assert job["status"] == "queued"
    assert job["task_data"]["options"]["language"] == "en"

    # Runtime implementation details must not cross the engine boundary.
    assert "task_queue" not in job
    assert "last_task" not in job
    assert "output" not in job

    # Mutating nested returned data must not modify the queue's real item.
    job["task_data"]["options"]["language"] = "de"

    stored_item = toolkit_ops.processing_queue.items["job-queued"]

    assert stored_item["task_data"]["options"]["language"] == "en"


def test_list_jobs_forwards_filters_and_returns_detached_data(
    engine: StoryToolkitEngine,
    toolkit_ops: FakeToolkitOps,
) -> None:
    """
    Job filters reach the queue and returned items remain detached.
    """

    jobs = engine.list_jobs(
        status=["queued", "processing"],
        not_status="canceled",
    )

    assert set(jobs) == {"job-queued"}

    assert (
        toolkit_ops.processing_queue.last_status_filter
        == ["queued", "processing"]
    )
    assert toolkit_ops.processing_queue.last_not_status_filter == "canceled"

    assert "task_queue" not in jobs["job-queued"]
    assert "last_task" not in jobs["job-queued"]
    assert "output" not in jobs["job-queued"]

    jobs["job-queued"]["task_data"]["source"] = "changed.wav"

    stored_item = toolkit_ops.processing_queue.items["job-queued"]

    assert stored_item["task_data"]["source"] == "example.wav"


def test_list_jobs_returns_all_jobs_without_filters(
    engine: StoryToolkitEngine,
) -> None:
    """Omitting filters returns all jobs exposed by the queue."""

    jobs = engine.list_jobs()

    assert set(jobs) == {
        "job-queued",
        "job-done",
    }


def test_cancel_job_delegates_to_safe_queue_cancellation(
    engine: StoryToolkitEngine,
    toolkit_ops: FakeToolkitOps,
) -> None:
    """A successful cancellation reaches the queue's safe cancel path."""
    result = engine.cancel_job("job-queued")

    assert result is True
    assert toolkit_ops.processing_queue.cancel_requests == ["job-queued"]
    assert (
        toolkit_ops.processing_queue.items["job-queued"]["status"]
        == "canceled"
    )


def test_cancel_unknown_job_returns_false(
    engine: StoryToolkitEngine,
    toolkit_ops: FakeToolkitOps,
) -> None:
    """A cancellation request for an unknown job returns False."""

    result = engine.cancel_job("missing-job")

    assert result is False
    assert toolkit_ops.processing_queue.cancel_requests == ["missing-job"]

def test_create_ingest_job_owns_placeholder_status(
    engine: StoryToolkitEngine,
    toolkit_ops: FakeToolkitOps,
) -> None:
    """A normal ingest placeholder is created in the waiting-user state."""

    job_id = engine.create_ingest_job()

    assert job_id == "job-generated-1"
    assert toolkit_ops.processing_queue.generated_names == [None]
    assert toolkit_ops.processing_queue.items[job_id] == {
        "queue_id": job_id,
        "name": "",
        "status": "waiting user",
    }


def test_create_timeline_ingest_job_waits_for_render(
    engine: StoryToolkitEngine,
    toolkit_ops: FakeToolkitOps,
) -> None:
    """A Resolve timeline ingest is visible while its render is pending."""

    job_id = engine.create_timeline_ingest_job(
        name="Interview Timeline.wav",
    )

    assert job_id == "job-generated-1"
    assert toolkit_ops.processing_queue.generated_names == [
        "Interview Timeline.wav",
    ]
    assert toolkit_ops.processing_queue.items[job_id] == {
        "queue_id": job_id,
        "name": "Interview Timeline.wav",
        "status": "waiting for render",
    }


def test_ingest_job_can_move_from_render_to_user_input(
    engine: StoryToolkitEngine,
    toolkit_ops: FakeToolkitOps,
) -> None:
    """A rendered timeline moves to waiting user when its form opens."""

    job_id = engine.create_timeline_ingest_job(
        name="Interview Timeline.wav",
    )

    result = engine.mark_ingest_job_waiting_for_user(job_id)

    assert result is True
    assert (
        toolkit_ops.processing_queue.items[job_id]["status"]
        == "waiting user"
    )


def test_mark_unknown_ingest_job_returns_false(
    engine: StoryToolkitEngine,
) -> None:
    """An unknown ingest placeholder cannot be updated."""

    assert (
        engine.mark_ingest_job_waiting_for_user("missing-job")
        is False
    )


def test_start_ingest_delegates_to_processing(
    engine: StoryToolkitEngine,
    toolkit_ops: FakeToolkitOps,
) -> None:
    """The engine forwards the completed settings to processing."""

    ingest_settings = object()

    result = engine.start_ingest(ingest_settings)

    assert result == ["job-ingest"]
    assert toolkit_ops.ingest_requests == [ingest_settings]

def test_engine_subscriber_receives_processing_event(
    engine: StoryToolkitEngine,
    toolkit_ops: FakeToolkitOps,
) -> None:
    """Events published by processing reach subscribers through the engine."""

    received: list[EngineEvent] = []
    engine.subscribe(received.append)

    event = EngineEvent(
        type="job.changed",
        data={
            "job_id": "job-queued",
            "status": "processing",
        },
    )
    toolkit_ops.events.emit(event)

    assert received == [event]


def test_engine_unsubscribe_stops_processing_events(
    engine: StoryToolkitEngine,
    toolkit_ops: FakeToolkitOps,
) -> None:
    """The engine can remove a previously subscribed event listener."""

    received: list[EngineEvent] = []
    engine.subscribe(received.append)
    engine.unsubscribe(received.append)

    toolkit_ops.events.emit(
        EngineEvent(
            type="job.changed",
            data={
                "job_id": "job-queued",
                "status": "processing",
            },
        )
    )

    assert received == []

def test_publish_transcription_changed_emits_named_event(
    engine: StoryToolkitEngine,
) -> None:
    """Transcription refreshes use a named event and plain identifier."""
    received: list[EngineEvent] = []
    engine.subscribe(received.append)

    result = engine.publish_transcription_changed(
        "transcription-123"
    )

    assert result is True
    assert received == [
        EngineEvent(
            type="transcription.changed",
            data={
                "transcription_id": "transcription-123",
            },
        )
    ]


def test_publish_transcription_changed_rejects_empty_identifier(
    engine: StoryToolkitEngine,
) -> None:
    """An empty transcription identifier publishes no event."""
    received: list[EngineEvent] = []
    engine.subscribe(received.append)

    result = engine.publish_transcription_changed("")

    assert result is False
    assert received == []


def test_publish_project_changed_emits_named_event(
    engine: StoryToolkitEngine,
) -> None:
    """Project refreshes use a named event without live project data."""
    received: list[EngineEvent] = []
    engine.subscribe(received.append)

    result = engine.publish_project_changed()

    assert result is True
    assert received == [
        EngineEvent(
            type="project.changed",
        )
    ]
