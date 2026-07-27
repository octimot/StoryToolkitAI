from __future__ import annotations

import sys
from threading import Event, Thread
from types import ModuleType

# ProcessingQueue only needs torch.device for an isinstance check in these
# tests. Keep this regression test runnable in the lightweight test setup.
try:
    import torch as _torch  # noqa: F401
except ModuleNotFoundError:
    torch_stub = ModuleType("torch")

    class _TorchDevice:
        def __init__(self, device_type: str) -> None:
            self.type = device_type

    torch_stub.device = _TorchDevice
    sys.modules["torch"] = torch_stub

from storytoolkitai.core.toolkit_ops import processing_queue as processing_queue_module


ProcessingQueue = processing_queue_module.ProcessingQueue


def test_job_changed_event_is_emitted_after_queue_lock_is_released(
    tmp_path,
    monkeypatch,
) -> None:
    """An event listener must be able to read the queue from another thread."""
    monkeypatch.setattr(
        processing_queue_module,
        "QUEUE_FILE_PATH",
        str(tmp_path / "queue.json"),
    )

    queue = ProcessingQueue()
    reader_finished = Event()
    listener_results: list[bool] = []
    reader_threads: list[Thread] = []

    def read_queue_snapshot() -> None:
        queue.get_all_queue_items_snapshot()
        reader_finished.set()

    def receive_event(event) -> None:
        if event.type != "job.changed":
            return

        reader = Thread(target=read_queue_snapshot)
        reader_threads.append(reader)
        reader.start()

        # Before the deadlock fix, job.changed was emitted while _state_lock
        # was held. The reader could not complete until this listener returned.
        listener_results.append(reader_finished.wait(timeout=1.0))

    queue.events.subscribe(receive_event)

    queue_id = queue.create_placeholder(
        name="Queue lock regression",
        status="waiting user",
        item_type="ingest",
    )

    for reader in reader_threads:
        reader.join(timeout=1.0)
        assert not reader.is_alive()

    assert queue_id
    assert listener_results == [True]
