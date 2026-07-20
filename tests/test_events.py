from __future__ import annotations

from storytoolkitai.core.events import EngineEvent, EventEmitter


def test_subscriber_receives_event() -> None:
    """A subscribed listener receives the emitted event."""

    emitter = EventEmitter()
    received: list[EngineEvent] = []

    emitter.subscribe(received.append)

    event = EngineEvent(
        type="test.event",
        data={"value": 42},
    )
    emitter.emit(event)

    assert received == [event]


def test_multiple_subscribers_receive_event() -> None:
    """All subscribed listeners receive the same event."""

    emitter = EventEmitter()
    first_listener_events: list[EngineEvent] = []
    second_listener_events: list[EngineEvent] = []

    emitter.subscribe(first_listener_events.append)
    emitter.subscribe(second_listener_events.append)

    event = EngineEvent(type="test.event")
    emitter.emit(event)

    assert first_listener_events == [event]
    assert second_listener_events == [event]


def test_duplicate_subscription_is_ignored() -> None:
    """The same listener is not registered more than once."""

    emitter = EventEmitter()
    received: list[EngineEvent] = []

    emitter.subscribe(received.append)
    emitter.subscribe(received.append)

    event = EngineEvent(type="test.event")
    emitter.emit(event)

    assert received == [event]


def test_unsubscribe_stops_event_delivery() -> None:
    """An unsubscribed listener no longer receives events."""

    emitter = EventEmitter()
    received: list[EngineEvent] = []

    emitter.subscribe(received.append)
    emitter.unsubscribe(received.append)

    emitter.emit(EngineEvent(type="test.event"))

    assert received == []


def test_failing_listener_does_not_stop_other_listeners() -> None:
    """One broken listener cannot interrupt processing event delivery."""

    emitter = EventEmitter()
    received: list[EngineEvent] = []

    def failing_listener(event: EngineEvent) -> None:
        raise RuntimeError("Expected listener failure")

    emitter.subscribe(failing_listener)
    emitter.subscribe(received.append)

    event = EngineEvent(type="test.event")
    emitter.emit(event)

    assert received == [event]


def test_listener_can_unsubscribe_during_emit() -> None:
    """Changing subscriptions during emit does not corrupt iteration."""

    emitter = EventEmitter()
    received: list[EngineEvent] = []

    def one_time_listener(event: EngineEvent) -> None:
        received.append(event)
        emitter.unsubscribe(one_time_listener)

    emitter.subscribe(one_time_listener)

    first_event = EngineEvent(type="test.first")
    second_event = EngineEvent(type="test.second")

    emitter.emit(first_event)
    emitter.emit(second_event)

    assert received == [first_event]
