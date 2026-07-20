from __future__ import annotations

from typing import Any

import pytest

from storytoolkitai.core.engine import StoryToolkitEngine


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

    def cancel_item(self, queue_id: str) -> dict[str, Any] | None:
        """Record and perform a simple cancellation request."""

        self.cancel_requests.append(queue_id)

        item = self.items.get(queue_id)

        if item is None:
            return None

        item["status"] = "canceled"

        return item


class FakeToolkitOps:
    """ToolkitOps replacement containing only the processing queue."""

    def __init__(self) -> None:
        self.processing_queue = FakeProcessingQueue()


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


def test_cancel_job_delegates_to_processing_queue(
    engine: StoryToolkitEngine,
    toolkit_ops: FakeToolkitOps,
) -> None:
    """A successful cancellation returns True and reaches the queue."""

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

