"""Ensure named public event factories produce simple data."""

from __future__ import annotations

from typing import Any

import storytoolkitai.core.events as events_module
from storytoolkitai.core.events import (
    EngineEvent,
    create_job_task_completed_event,
    create_project_changed_event,
    create_transcription_changed_event,
    create_transcription_completed_event,
    create_transcription_groups_changed_event,
    create_transcription_started_event,
)


_SIMPLE_EVENT_TYPES = (
    str,
    int,
    float,
    bool,
    type(None),
)


def _named_event_samples() -> dict[str, EngineEvent]:
    """Create one representative value from every public event factory."""

    return {
        "create_transcription_started_event": (
            create_transcription_started_event(
                job_id="job-1",
                name="interview.wav",
                audio_file_path="/media/interview.wav",
                task="transcribe",
                time_intervals=[
                    (1, 2),
                    [3.5, 4.75],
                ],
            )
        ),
        "create_transcription_completed_event": (
            create_transcription_completed_event(
                job_id="job-1",
                name="interview.wav",
                audio_file_path="/media/interview.wav",
                transcription_file_path=(
                    "/media/interview.transcription.json"
                ),
                task="transcribe",
                elapsed_seconds=42,
            )
        ),
        "create_job_task_completed_event": (
            create_job_task_completed_event(
                job_id="job-1",
                item_type="transcription",
                task_name="speaker_detection",
            )
        ),
        "create_project_changed_event": create_project_changed_event(),
        "create_transcription_changed_event": (
            create_transcription_changed_event(
                transcription_id="transcription-1",
            )
        ),
        "create_transcription_groups_changed_event": (
            create_transcription_groups_changed_event(
                transcription_id="transcription-1",
            )
        ),
    }


def _assert_simple_event_data(
    value: Any,
    *,
    path: str,
) -> None:
    """Recursively reject values that cannot be represented as JSON data."""

    if isinstance(value, _SIMPLE_EVENT_TYPES):
        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            _assert_simple_event_data(
                item,
                path=f"{path}[{index}]",
            )

        return

    if isinstance(value, dict):
        for key, item in value.items():
            assert isinstance(key, str), (
                f"{path} contains a non-string dictionary key: {key!r}"
            )

            _assert_simple_event_data(
                item,
                path=f"{path}.{key}",
            )

        return

    raise AssertionError(
        f"{path} contains unsupported event data "
        f"of type {type(value).__name__}: {value!r}"
    )


def test_named_event_factories_produce_simple_data() -> None:
    """All named event factories must return simple detached payload data."""

    samples = _named_event_samples()
    public_factories = {
        name
        for name, value in vars(events_module).items()
        if (
            name.startswith("create_")
            and name.endswith("_event")
            and callable(value)
        )
    }

    assert set(samples) == public_factories, (
        "Every public named event factory needs a representative "
        "simple-data sample. Missing or stale samples: {}".format(
            sorted(set(samples) ^ public_factories)
        )
    )

    for event in samples.values():
        assert isinstance(event.type, str)
        assert event.type

        _assert_simple_event_data(
            event.data,
            path=f"{event.type}.data",
        )
