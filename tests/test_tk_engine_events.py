from __future__ import annotations

import ast
from pathlib import Path
from queue import Empty, SimpleQueue
from threading import Thread
from types import SimpleNamespace

from storytoolkitai.core.events import EngineEvent


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLKIT_UI_PATH = (
    PROJECT_ROOT
    / "storytoolkitai"
    / "ui"
    / "toolkit_ui.py"
)
TESTED_METHODS = {
    "_handle_engine_event",
    "_notify_window_observers",
    "_poll_engine_events",
    "_refresh_queue",
    "_run_window_observer",
    "_stop_engine_event_polling",
    "receive_engine_event",
    "remove_observer_from_window",
    "request_queue_refresh",
}


class FakeTclError(Exception):
    """Stand-in for tkinter.TclError in the dependency-light test harness."""


def _load_tested_ui_methods():
    """
    Load selected toolkit_UI methods without importing the full Tk UI module.

    The production UI imports optional media and model dependencies that are
    deliberately absent from the fast test environment. Compiling the actual
    method definitions keeps these tests behavioral while avoiding a display
    server and heavyweight dependency stubs.
    """

    source = TOOLKIT_UI_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(TOOLKIT_UI_PATH))
    toolkit_ui_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "toolkit_UI"
    )
    methods = [
        node
        for node in toolkit_ui_class.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in TESTED_METHODS
    ]

    assert {method.name for method in methods} == TESTED_METHODS

    test_class = ast.ClassDef(
        name="TestedTkEventMethods",
        bases=[],
        keywords=[],
        body=methods,
        decorator_list=[],
    )
    module = ast.fix_missing_locations(
        ast.Module(body=[test_class], type_ignores=[])
    )
    namespace = {
        "Empty": Empty,
        "EngineEvent": EngineEvent,
        "RuntimeError": RuntimeError,
        "logger": SimpleNamespace(exception=lambda *args: None),
        "tk": SimpleNamespace(TclError=FakeTclError),
    }
    exec(
        compile(module, str(TOOLKIT_UI_PATH), "exec"),
        namespace,
    )
    return namespace["TestedTkEventMethods"]


TestedTkEventMethods = _load_tested_ui_methods()


class FakeTkRoot:
    """Record Tk scheduling calls and run them deterministically in tests."""

    def __init__(self):
        self._next_id = 0
        self.after_calls = []
        self.idle_calls = []
        self.cancelled = []

    def _new_id(self, prefix):
        self._next_id += 1
        return "{}-{}".format(prefix, self._next_id)

    def after(self, delay_ms, callback):
        after_id = self._new_id("after")
        self.after_calls.append(
            {
                "id": after_id,
                "delay_ms": delay_ms,
                "callback": callback,
            }
        )
        return after_id

    def after_idle(self, callback):
        after_id = self._new_id("idle")
        self.idle_calls.append(
            {
                "id": after_id,
                "callback": callback,
            }
        )
        return after_id

    def after_cancel(self, after_id):
        self.cancelled.append(after_id)
        self.after_calls = [
            call
            for call in self.after_calls
            if call["id"] != after_id
        ]
        self.idle_calls = [
            call
            for call in self.idle_calls
            if call["id"] != after_id
        ]

    def run_next_after(self):
        scheduled = self.after_calls.pop(0)
        scheduled["callback"]()

    def run_next_idle(self):
        scheduled = self.idle_calls.pop(0)
        scheduled["callback"]()


class FakeWindow:
    def __init__(self):
        self.exists = True

    def winfo_exists(self):
        if not self.exists:
            raise FakeTclError("window was destroyed")
        return True


class TkEventHarness(TestedTkEventMethods):
    def __init__(self):
        self.root = FakeTkRoot()
        self._accept_engine_events = True
        self._engine_events = SimpleQueue()
        self._engine_event_poll_id = None
        self._queue_refresh_pending = False
        self.windows = {}
        self.windows_observers = {}
        self.notifications = []
        self.queue_refreshes = 0

    def get_window_by_id(self, window_id):
        return self.windows.get(window_id)

    def update_queue_window(self):
        self.queue_refreshes += 1

    def notify_via_os(
        self,
        title,
        text,
        debug_message=None,
    ):
        self.notifications.append((title, text, debug_message))


def test_worker_engine_event_only_enters_thread_safe_queue():
    ui = TkEventHarness()
    event = EngineEvent(
        type="transcription.started",
        data={"name": "Interview"},
    )

    def emit_from_worker():
        assert ui.receive_engine_event(event) is True

    worker = Thread(target=emit_from_worker)
    worker.start()
    worker.join()

    assert ui.notifications == []
    assert ui.root.after_calls == []

    assert ui._poll_engine_events() is True

    assert ui.notifications == [
        (
            "Starting Transcription",
            "Transcribing Interview",
            None,
        )
    ]
    assert len(ui.root.after_calls) == 1
    assert ui.root.after_calls[0]["delay_ms"] == 25


def test_event_received_before_polling_is_not_lost():
    ui = TkEventHarness()

    ui.receive_engine_event(
        EngineEvent(
            type="transcription.started",
            data={"name": "Interview"},
        )
    )

    assert ui.notifications == []

    ui._poll_engine_events()

    assert len(ui.notifications) == 1


def test_poll_batch_is_bounded_and_remaining_events_run_next_cycle():
    ui = TkEventHarness()
    handled = []
    ui._handle_engine_event = handled.append

    for event_number in range(101):
        ui.receive_engine_event(
            EngineEvent(
                type="test.event",
                data={"event_number": event_number},
            )
        )

    ui._poll_engine_events()

    assert len(handled) == 100

    ui.root.run_next_after()

    assert len(handled) == 101


def test_one_handler_failure_does_not_stop_polling():
    ui = TkEventHarness()
    handled = []

    def handle(event):
        if event.type == "test.broken":
            raise RuntimeError("broken handler")
        handled.append(event.type)

    ui._handle_engine_event = handle
    ui.receive_engine_event(EngineEvent(type="test.broken"))
    ui.receive_engine_event(EngineEvent(type="test.working"))

    ui._poll_engine_events()

    assert handled == ["test.working"]
    assert len(ui.root.after_calls) == 1


def test_repeated_job_events_share_one_pending_queue_refresh():
    ui = TkEventHarness()
    ui.windows["queue"] = FakeWindow()
    event = EngineEvent(type="job.changed")

    ui.receive_engine_event(event)
    ui.receive_engine_event(event)
    ui.receive_engine_event(event)
    ui._poll_engine_events()

    assert ui._queue_refresh_pending is True
    assert len(ui.root.idle_calls) == 1
    assert ui.queue_refreshes == 0

    ui.root.run_next_idle()

    assert ui._queue_refresh_pending is False
    assert ui.queue_refreshes == 1

    ui.receive_engine_event(event)
    ui.root.run_next_after()

    assert ui._queue_refresh_pending is True
    assert len(ui.root.idle_calls) == 1


def test_closed_queue_window_is_skipped_and_pending_flag_is_cleared():
    ui = TkEventHarness()
    ui.windows["queue"] = FakeWindow()

    ui.receive_engine_event(EngineEvent(type="job.changed"))
    ui._poll_engine_events()
    del ui.windows["queue"]

    ui.root.run_next_idle()

    assert ui._queue_refresh_pending is False
    assert ui.queue_refreshes == 0


def test_observer_callback_is_skipped_after_its_window_is_destroyed():
    ui = TkEventHarness()
    callback_calls = []
    window = FakeWindow()
    ui.windows["main"] = window
    ui.windows_observers = {
        "main": {
            "project_changed": {
                "callback": lambda: callback_calls.append("called"),
                "dettach_after_call": False,
            }
        }
    }

    ui.receive_engine_event(EngineEvent(type="project.changed"))
    ui._poll_engine_events()

    assert ui.root.after_calls[0]["delay_ms"] == 1

    window.exists = False
    ui.root.run_next_after()

    assert callback_calls == []
    assert "main" not in ui.windows_observers


def test_one_time_observer_is_removed_after_it_runs():
    ui = TkEventHarness()
    callback_calls = []
    ui.windows["main"] = FakeWindow()
    ui.windows_observers = {
        "main": {
            "project_changed": {
                "callback": lambda: callback_calls.append("called"),
                "dettach_after_call": True,
            }
        }
    }

    ui.receive_engine_event(EngineEvent(type="project.changed"))
    ui._poll_engine_events()
    ui.root.run_next_after()

    assert callback_calls == ["called"]
    assert "main" not in ui.windows_observers


def test_polling_stops_and_queued_events_are_ignored_during_shutdown():
    ui = TkEventHarness()
    event = EngineEvent(
        type="transcription.started",
        data={"name": "Interview"},
    )

    assert ui.receive_engine_event(event) is True
    ui._accept_engine_events = False

    assert ui.receive_engine_event(event) is False
    assert ui._poll_engine_events() is False

    assert ui.notifications == []
    assert ui.root.after_calls == []


def test_stop_cancels_the_scheduled_poll():
    ui = TkEventHarness()
    poll_id = ui.root.after(25, ui._poll_engine_events)
    ui._engine_event_poll_id = poll_id

    assert ui._stop_engine_event_polling() is True

    assert ui._accept_engine_events is False
    assert ui._engine_event_poll_id is None
    assert poll_id in ui.root.cancelled
    assert ui.root.after_calls == []


def test_scheduled_observer_is_skipped_during_shutdown():
    ui = TkEventHarness()
    callback_calls = []
    ui.windows["main"] = FakeWindow()
    ui.windows_observers = {
        "main": {
            "project_changed": {
                "callback": lambda: callback_calls.append("called"),
                "dettach_after_call": False,
            }
        }
    }

    ui.receive_engine_event(EngineEvent(type="project.changed"))
    ui._poll_engine_events()
    ui._stop_engine_event_polling()
    ui.root.run_next_after()

    assert callback_calls == []
