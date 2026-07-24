from __future__ import annotations

import sys
from types import ModuleType
from typing import Any

import pytest


# ProcessingQueue imports torch, but the queue lifecycle tested here only needs
# torch.device to exist for an isinstance check. Keep the fast test environment
# lightweight by providing a tiny stand-in when PyTorch is not installed.
#
# When PyTorch is installed, the real module is used instead.
try:
    import torch as _torch  # noqa: F401
except ModuleNotFoundError:
    torch_stub = ModuleType("torch")

    class _TorchDevice:
        """Minimal replacement for torch.device used by ProcessingQueue."""

        def __init__(self, device_type: str) -> None:
            self.type = device_type

    torch_stub.device = _TorchDevice
    sys.modules["torch"] = torch_stub


from storytoolkitai.core.events import EngineEvent
from storytoolkitai.core.toolkit_ops import processing_queue as processing_queue_module

ProcessingQueue = processing_queue_module.ProcessingQueue


def _run_test_task(**kwargs: Any) -> dict[str, Any]:
    """Harmless queue task used to exercise the existing task dispatcher."""

    return kwargs

TEST_TASK_HANDLERS = {
    "test_task": [_run_test_task],
}

class FakeToolkitOps:
    """
    Small replacement for ToolkitOps containing only what ProcessingQueue
    currently needs for the lifecycle operations covered by these tests.
    """

    def __init__(self) -> None:
        self.queue_tasks = {
            "test_task": [_run_test_task],
        }
        self.notifications: list[str] = []

    def notify_observers(self, action: str) -> None:
        """Record observer notifications without starting any UI code."""

        self.notifications.append(action)


@pytest.fixture
def processing_queue(tmp_path, monkeypatch):
    """
    Return an empty queue whose queue.json file is isolated per test.

    conftest.py already isolates the application user-data directory. Patching
    QUEUE_FILE_PATH here gives each queue test its own file as well.
    """

    queue_file_path = tmp_path / "queue.json"

    monkeypatch.setattr(
        processing_queue_module,
        "QUEUE_FILE_PATH",
        str(queue_file_path),
    )

    return ProcessingQueue(
        task_handlers=TEST_TASK_HANDLERS,
    )


def _add_test_job(
    processing_queue,
    queue_id: str,
    *,
    name: str | None = None,
):
    """Add a valid queue item without starting a processing thread."""

    added_queue_id = processing_queue.add_to_queue(
        tasks="test_task",
        queue_id=queue_id,
        item_type="test",
        task_data={"value": 42},
        device="cpu",
        ping=False,
        name=name or queue_id,
    )

    assert added_queue_id == queue_id

    item = processing_queue.get_item(queue_id)

    assert item is not None

    return item


def test_queue_item_can_be_added_and_retrieved(processing_queue) -> None:
    """Updating a status changes history and emits a neutral event."""

    item = _add_test_job(
        processing_queue,
        "job-1",
        name="Example job",
    )

    assert processing_queue.queue == ["job-1"]

    assert item["queue_id"] == "job-1"
    assert item["name"] == "Example job"
    assert item["status"] == "queued"
    assert item["tasks"] == "test_task"
    assert item["item_type"] == "test"
    assert item["task_data"] == {"value": 42}
    assert item["device"] == "cpu"

    # The task dispatcher should have converted the task name into a callable
    # task queue, but the task itself must not have been executed.
    assert item["task_queue"] == [_run_test_task]


def test_new_queue_item_emits_job_changed_event(
    processing_queue,
) -> None:
    """Adding a new item emits a neutral event for engine clients."""
    received_events = []
    processing_queue.events.subscribe(received_events.append)

    _add_test_job(processing_queue, "job-1")

    assert len(received_events) == 1

    event = received_events[0]
    assert event.type == "job.changed"
    assert event.data == {
        "job_id": "job-1",
        "status": "queued",
        "progress": None,
        "item_type": "test",
    }


def test_queue_items_can_be_filtered_by_status(processing_queue) -> None:
    """The current status and not_status filters select queue-history items."""

    _add_test_job(processing_queue, "job-queued")
    _add_test_job(processing_queue, "job-done")

    processing_queue.update_status(
        queue_id="job-done",
        status="done",
    )

    queued_items = processing_queue.get_all_queue_items(
        status="queued",
    )
    finished_items = processing_queue.get_all_queue_items(
        status=["done", "failed"],
    )
    unfinished_items = processing_queue.get_all_queue_items(
        not_status=["done", "failed", "canceled"],
    )

    assert set(queued_items) == {"job-queued"}
    assert set(finished_items) == {"job-done"}
    assert set(unfinished_items) == {"job-queued"}


def test_queue_item_status_can_be_updated(processing_queue) -> None:
    """
    Updating a status changes history and emits a neutral event.
    """

    _add_test_job(processing_queue, "job-1")

    received_events: list[EngineEvent] = []
    processing_queue.events.subscribe(received_events.append)

    processing_queue.update_status(
        queue_id="job-1",
        status="processing",
    )

    item = processing_queue.get_item("job-1")

    assert item is not None
    assert item["status"] == "processing"
    assert isinstance(item["last_update"], float)

    assert received_events == [
        EngineEvent(
            type="job.changed",
            data={
                "job_id": "job-1",
                "status": "processing",
                "progress": None,
                "item_type": "test",
            },
        )
    ]

    # Event data must not expose queue internals or runtime callables.
    event_data = received_events[0].data
    assert "task_queue" not in event_data
    assert "last_task" not in event_data
    assert "output" not in event_data


def test_pending_queue_item_can_be_canceled(processing_queue) -> None:
    """Cancelling a pending item removes it from the queue and keeps history."""

    _add_test_job(processing_queue, "job-1")

    canceled_item = processing_queue.cancel_item("job-1")

    assert canceled_item is not None
    assert canceled_item["status"] == "canceled"

    assert "job-1" not in processing_queue.queue
    assert processing_queue.get_status("job-1") == "canceled"

    # Cancellation currently keeps the item in queue history so that its
    # final state remains visible to callers.
    assert processing_queue.get_item("job-1") is canceled_item


def test_queued_item_safe_cancellation_is_immediate(
    processing_queue,
) -> None:
    """A queued item is removed from the runnable queue immediately."""
    _add_test_job(processing_queue, "job-1")

    result = processing_queue.set_to_canceled("job-1")

    assert result
    assert "job-1" not in processing_queue.queue
    assert processing_queue.get_status("job-1") == "canceled"


def test_running_item_safe_cancellation_waits_for_current_task(
    processing_queue,
) -> None:
    """A running item enters canceling until its current task finishes."""
    _add_test_job(processing_queue, "job-1")
    processing_queue.update_status(
        queue_id="job-1",
        status="processing",
    )

    # the queue only needs the queue id here
    # the actual thread object is not inspected by is_item_in_thread
    processing_queue.queue_threads["cpu"] = {
        "queue_id": "job-1",
        "thread": object(),
    }

    result = processing_queue.set_to_canceled("job-1")

    assert result
    assert processing_queue.get_status("job-1") == "canceling"
    assert processing_queue.get_progress("job-1") == ""


@pytest.mark.parametrize(
    "status",
    [
        "done",
        "failed",
        "canceled",
    ],
)
def test_finished_item_safe_cancellation_is_rejected(
    processing_queue,
    status: str,
) -> None:
    """Finished and already canceled items keep their existing status."""
    _add_test_job(processing_queue, "job-1")
    processing_queue.update_status(
        queue_id="job-1",
        status=status,
    )

    result = processing_queue.set_to_canceled("job-1")

    assert result is False
    assert processing_queue.get_status("job-1") == status


def test_repeated_running_item_cancellation_is_idempotent(
    processing_queue,
) -> None:
    """A repeated cancellation request for a running item remains valid."""
    _add_test_job(processing_queue, "job-1")
    processing_queue.update_status(
        queue_id="job-1",
        status="canceling",
    )

    processing_queue.queue_threads["cpu"] = {
        "queue_id": "job-1",
        "thread": object(),
    }

    result = processing_queue.set_to_canceled("job-1")

    assert result is True
    assert processing_queue.get_status("job-1") == "canceling"


def test_canceling_item_is_finalized_after_leaving_thread(
    processing_queue,
) -> None:
    """A canceling item becomes canceled after its active task has stopped."""
    _add_test_job(processing_queue, "job-1")
    processing_queue.update_status(
        queue_id="job-1",
        status="canceling",
    )

    result = processing_queue.set_to_canceled("job-1")

    assert result
    assert "job-1" not in processing_queue.queue
    assert processing_queue.get_status("job-1") == "canceled"


def test_unknown_item_safe_cancellation_returns_false(
    processing_queue,
) -> None:
    """An unknown queue id cannot be canceled."""
    result = processing_queue.set_to_canceled("missing-job")

    assert result is False


def test_queue_history_can_be_saved_and_loaded(processing_queue) -> None:
    """
    Queue persistence keeps resumable data and removes runtime-only values.
    """

    _add_test_job(
        processing_queue,
        "job-1",
        name="Persistent job",
    )

    processing_queue.update_queue_item(
        queue_id="job-1",
        save_to_file=False,
        output=["runtime-only output"],
        last_task="runtime-only task",
    )

    assert processing_queue.save_queue_to_file() is True

    reloaded_queue = ProcessingQueue(
        task_handlers=TEST_TASK_HANDLERS,
    )
    loaded_history = reloaded_queue.load_queue_from_file()

    assert len(loaded_history) == 1

    loaded_item = loaded_history[0]

    assert loaded_item["queue_id"] == "job-1"
    assert loaded_item["name"] == "Persistent job"
    assert loaded_item["status"] == "queued"
    assert loaded_item["tasks"] == "test_task"
    assert loaded_item["task_data"] == {"value": 42}
    assert loaded_item["device"] == "cpu"

    # These values contain callables or runtime-only information and are
    # intentionally excluded by the current queue serializer.
    assert "task_queue" not in loaded_item
    assert "last_task" not in loaded_item
    assert "output" not in loaded_item

def test_queue_keeps_only_explicit_task_handlers(
    processing_queue,
) -> None:
    """ProcessingQueue must not retain the complete ToolkitOps object."""

    assert processing_queue.task_handlers == TEST_TASK_HANDLERS
    assert not hasattr(processing_queue, "toolkit_ops_obj")

def test_generated_queue_id_does_not_create_a_queue_item(
    processing_queue,
) -> None:
    """Generating an ID alone must not create phantom queue history."""

    received_events: list[EngineEvent] = []
    processing_queue.events.subscribe(received_events.append)

    queue_id = processing_queue.generate_queue_id(
        name="Example ingest",
    )

    assert processing_queue.get_item(queue_id) is None
    assert processing_queue.queue_history == []
    assert received_events == []


def test_placeholder_is_stored_and_emits_its_real_initial_status(
    processing_queue,
) -> None:
    """A non-runnable ingest placeholder is visible and persisted."""

    received_events: list[EngineEvent] = []
    processing_queue.events.subscribe(received_events.append)

    queue_id = processing_queue.create_placeholder(
        name="Example ingest",
        status="waiting user",
        item_type="ingest",
    )

    assert processing_queue.queue == []
    assert processing_queue.get_item(queue_id) == {
        "queue_id": queue_id,
        "name": "Example ingest",
        "status": "waiting user",
        "item_type": "ingest",
    }
    assert received_events == [
        EngineEvent(
            type="job.changed",
            data={
                "job_id": queue_id,
                "status": "waiting user",
                "progress": None,
                "item_type": "ingest",
            },
        )
    ]

    reloaded_queue = ProcessingQueue(
        task_handlers=TEST_TASK_HANDLERS,
    )
    loaded_history = reloaded_queue.load_queue_from_file()

    assert loaded_history == [{
        "queue_id": queue_id,
        "name": "Example ingest",
        "status": "waiting user",
        "item_type": "ingest",
    }]


def test_placeholder_is_promoted_when_tasks_are_submitted(
    processing_queue,
) -> None:
    """Submitting tasks with a placeholder ID updates the existing history."""

    queue_id = processing_queue.create_placeholder(
        name="Example ingest",
        status="waiting user",
        item_type="ingest",
    )

    added_queue_id = processing_queue.add_to_queue(
        tasks="test_task",
        queue_id=queue_id,
        item_type="test",
        task_data={"value": 42},
        device="cpu",
        ping=False,
        name="Example job",
    )

    assert added_queue_id == queue_id
    assert processing_queue.queue == [queue_id]
    assert len(processing_queue.queue_history) == 1
    assert processing_queue.get_item(queue_id)["status"] == "queued"
    assert processing_queue.get_item(queue_id)["name"] == "Example job"


def test_queue_can_be_reordered_by_queue_id(
    processing_queue,
) -> None:
    """Runnable jobs follow the requested ID order without losing history."""

    placeholder_id = processing_queue.create_placeholder(
        name="Waiting ingest",
        status="waiting user",
        item_type="ingest",
    )
    _add_test_job(processing_queue, "job-1")
    _add_test_job(processing_queue, "job-2")
    _add_test_job(processing_queue, "job-3")

    result = processing_queue.reorder_queue(
        ["job-3", "job-1", "job-2"],
    )

    assert result is True
    assert processing_queue.queue == ["job-3", "job-1", "job-2"]
    assert [
        item["queue_id"]
        for item in processing_queue.queue_history
    ] == [
        placeholder_id,
        "job-3",
        "job-1",
        "job-2",
    ]


@pytest.mark.parametrize(
    "invalid_order",
    [
        ["job-1", "job-1"],
        ["job-1", "missing-job"],
        [{"queue_id": "job-1"}, {"queue_id": "job-2"}],
    ],
)
def test_invalid_queue_order_is_rejected_without_mutation(
    processing_queue,
    invalid_order,
) -> None:
    """Duplicates, unknown IDs and queue dictionaries are rejected."""

    _add_test_job(processing_queue, "job-1")
    _add_test_job(processing_queue, "job-2")

    original_queue = list(processing_queue.queue)
    original_history = list(processing_queue.queue_history)

    result = processing_queue.reorder_queue(invalid_order)

    assert result is False
    assert processing_queue.queue == original_queue
    assert processing_queue.queue_history == original_history

def test_successful_task_emits_explicit_completion_event(
    processing_queue,
    monkeypatch,
) -> None:
    """A completed queue callable publishes structured task information."""

    _add_test_job(
        processing_queue,
        "job-1",
    )

    # The lifecycle test only needs to exercise task execution and events.
    # Thread-pool cleanup and queue scheduling are tested separately.
    monkeypatch.setattr(
        processing_queue,
        "remove_thread_from_queue_threads",
        lambda device: True,
    )
    monkeypatch.setattr(
        processing_queue,
        "ping_queue",
        lambda: True,
    )

    received_events: list[EngineEvent] = []
    processing_queue.events.subscribe(received_events.append)

    result = processing_queue.execute_item_tasks(
        queue_id="job-1",
        task_queue=[_run_test_task],
        device="cpu",
    )

    task_events = [
        event
        for event in received_events
        if event.type == "job.task_completed"
    ]

    assert result is True
    assert task_events == [
        EngineEvent(
            type="job.task_completed",
            data={
                "job_id": "job-1",
                "item_type": "test",
                "task_name": "_run_test_task",
            },
        )
    ]
