"""
Small UI-independent event mechanism for StoryToolkitAI.

Processing code uses these events to describe what happened without deciding
how that information should be displayed. A Tk, CLI, TUI, web UI can
subscribe and choose its own presentation.

This is deliberately kept small. It is not intended to be a general-purpose
event framework.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from storytoolkitai.core.logger import logger


@dataclass(frozen=True)
class EngineEvent:
    """
    A simple message describing something that happened in the engine.

    Event data should contain simple values that could later be converted to
    JSON: strings, numbers, booleans, None, lists, and dictionaries.

    The dataclass is frozen so the event's type and data reference cannot be
    replaced after publication. The contents of ``data`` should still be
    treated as read-only by listeners.
    """

    type: str
    data: dict[str, Any] = field(default_factory=dict)


# A listener is simply a function or bound method receiving one event.
EventListener = Callable[[EngineEvent], None]


class EventEmitter:
    """
    Publish engine events to subscribed listeners.

    Processing can emit events from worker threads. The listener collection is
    therefore protected by a small lock.

    Listeners are called synchronously in the thread that emits the event.
    Graphical UIs remain responsible for moving widget updates onto their own
    UI thread, for example with Tk's ``window.after(...)``.
    """

    def __init__(self) -> None:
        self._listeners: list[EventListener] = []
        self._lock = Lock()

    def subscribe(self, listener: EventListener) -> None:
        """
        Subscribe a listener.

        Registering the same listener more than once has no effect.
        """

        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def unsubscribe(self, listener: EventListener) -> None:
        """
        Remove a listener.

        Removing a listener that is not currently subscribed is harmless.
        """

        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    def emit(self, event: EngineEvent) -> None:
        """
        Send an event to all current listeners.

        A snapshot is created before listeners are called. This allows a
        listener to subscribe or unsubscribe while an event is being handled
        without changing the iteration in progress.

        Listener failures are logged but do not interrupt processing or stop
        other listeners from receiving the event.
        """

        with self._lock:
            listeners = tuple(self._listeners)

        for listener in listeners:
            try:
                listener(event)
            except Exception:
                logger.exception(
                    "Engine event listener failed while handling %s.",
                    event.type,
                )
