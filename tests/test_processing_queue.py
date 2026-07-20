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


from storytoolkitai.core.toolkit_ops import processing_queue as processing_queue_module


ProcessingQueue = processing_queue_module.ProcessingQueue


def _run_test_task(**kwargs: Any) -> dict[str, Any]:
    """Harmless queue task used to exercise the existing task dispatcher."""

    return kwargs


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
        toolkit_ops_obj=FakeToolkitOps(),
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
    """Adding an item records it in both the pending queue and its history."""

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

    assert processing_queue.toolkit_ops_obj.notifications == [
        "update_queue",
    ]


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
    """Updating a status changes history and emits the existing notification."""

    _add_test_job(processing_queue, "job-1")

    processing_queue.toolkit_ops_obj.notifications.clear()

    processing_queue.update_status(
        queue_id="job-1",
        status="processing",
    )

    item = processing_queue.get_item("job-1")

    assert item is not None
    assert item["status"] == "processing"
    assert isinstance(item["last_update"], float)

    assert processing_queue.toolkit_ops_obj.notifications == [
        "update_queue_item",
    ]


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
        toolkit_ops_obj=FakeToolkitOps(),
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
