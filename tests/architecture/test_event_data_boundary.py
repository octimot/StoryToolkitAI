"""Ensure named engine events contain transport-safe data.

Version 1 events still run in-process, but their payloads deliberately use data
that can later cross a process boundary without carrying live Python objects.
"""

from __future__ import annotations

import ast
from pathlib import Path
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


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSING_ROOTS = (
    PROJECT_ROOT / "storytoolkitai" / "core",
    PROJECT_ROOT / "storytoolkitai" / "integrations",
)
EVENTS_PATH = PROJECT_ROOT / "storytoolkitai" / "core" / "events.py"

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


def _assert_transport_safe(
    value: Any,
    *,
    path: str,
) -> None:
    """Recursively reject values that cannot be represented as JSON data."""

    if isinstance(value, _SIMPLE_EVENT_TYPES):
        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            _assert_transport_safe(
                item,
                path=f"{path}[{index}]",
            )

        return

    if isinstance(value, dict):
        for key, item in value.items():
            assert isinstance(key, str), (
                f"{path} contains a non-string dictionary key: {key!r}"
            )

            _assert_transport_safe(
                item,
                path=f"{path}.{key}",
            )

        return

    raise AssertionError(
        f"{path} contains unsupported event data "
        f"of type {type(value).__name__}: {value!r}"
    )


def test_named_engine_events_contain_transport_safe_data() -> None:
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
        "transport-safety sample. Missing or stale samples: {}".format(
            sorted(set(samples) ^ public_factories)
        )
    )

    for event in samples.values():
        assert isinstance(event.type, str)
        assert event.type

        _assert_transport_safe(
            event.data,
            path=f"{event.type}.data",
        )


def _engine_event_import_names(
    tree: ast.Module,
) -> tuple[set[str], set[str]]:
    """Return direct class names and module aliases for EngineEvent calls."""

    class_names = {"EngineEvent"}
    module_names: set[str] = set()

    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            module_name = node.module or ""

            if not module_name.endswith("core.events"):
                continue

            for alias in node.names:
                if alias.name == "EngineEvent":
                    class_names.add(alias.asname or alias.name)

        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.endswith("core.events"):
                    module_names.add(alias.asname or alias.name)

    return class_names, module_names


def _is_engine_event_call(
    node: ast.Call,
    *,
    class_names: set[str],
    module_names: set[str],
) -> bool:
    """Return whether a call constructs EngineEvent under a known import."""

    if isinstance(node.func, ast.Name):
        return node.func.id in class_names

    return (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "EngineEvent"
        and _dotted_name(node.func.value) in module_names
    )


def _dotted_name(node: ast.AST) -> str | None:
    """Return one dotted attribute path, when statically available."""

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent_name = _dotted_name(node.value)

        if parent_name is not None:
            return "{}.{}".format(parent_name, node.attr)

    return None


def _event_keyword(
    node: ast.Call,
    name: str,
) -> ast.AST | None:
    """Return one explicitly named EngineEvent argument."""

    return next(
        (
            keyword.value
            for keyword in node.keywords
            if keyword.arg == name
        ),
        None,
    )


def _direct_engine_event_violations(
    source: str,
    *,
    source_name: str,
) -> list[str]:
    """Return unsafe direct EngineEvent constructions from one source file."""

    tree = ast.parse(source, filename=source_name)
    class_names, module_names = _engine_event_import_names(tree)
    violations: list[str] = []
    expected_job_changed_keys = {
        "job_id",
        "item_type",
        "progress",
        "status",
    }
    expected_job_changed_sources = {
        "job_id": "queue_id",
        "item_type": "item_type",
        "progress": "progress",
        "status": "status",
    }

    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and _is_engine_event_call(
                node,
                class_names=class_names,
                module_names=module_names,
            )
        ):
            continue

        event_type_node = _event_keyword(node, "type")

        if event_type_node is None and node.args:
            event_type_node = node.args[0]

        if not (
            isinstance(event_type_node, ast.Constant)
            and isinstance(event_type_node.value, str)
            and event_type_node.value
        ):
            violations.append(
                "{}:{} uses a non-literal event type".format(
                    source_name,
                    node.lineno,
                )
            )
            continue

        data_node = _event_keyword(node, "data")

        if data_node is None and len(node.args) >= 2:
            data_node = node.args[1]

        if data_node is None:
            continue

        if not (
            event_type_node.value == "job.changed"
            and isinstance(data_node, ast.Dict)
        ):
            violations.append(
                "{}:{} adds unreviewed direct payload data to {!r}".format(
                    source_name,
                    node.lineno,
                    event_type_node.value,
                )
            )
            continue

        data_keys = {
            key.value
            for key in data_node.keys
            if (
                isinstance(key, ast.Constant)
                and isinstance(key.value, str)
            )
        }

        if (
            len(data_keys) != len(data_node.keys)
            or data_keys != expected_job_changed_keys
        ):
            violations.append(
                "{}:{} changes the reviewed job.changed payload "
                "keys: {}".format(
                    source_name,
                    node.lineno,
                    sorted(data_keys),
                )
            )
            continue

        for key_node, value_node in zip(
            data_node.keys,
            data_node.values,
        ):
            key = key_node.value
            expected_item_key = expected_job_changed_sources[key]

            if not (
                isinstance(value_node, ast.Call)
                and isinstance(value_node.func, ast.Attribute)
                and value_node.func.attr == "get"
                and isinstance(value_node.func.value, ast.Name)
                and value_node.func.value.id == "item"
                and len(value_node.args) == 1
                and isinstance(value_node.args[0], ast.Constant)
                and value_node.args[0].value == expected_item_key
                and not value_node.keywords
            ):
                violations.append(
                    "{}:{} changes the reviewed source of "
                    "job.changed field {!r}".format(
                        source_name,
                        node.lineno,
                        key,
                    )
                )

    return violations


def test_positional_direct_event_payload_is_rejected() -> None:
    """A positional payload must not bypass direct-event review."""

    source = """
from storytoolkitai.core.events import EngineEvent

unsafe_value = object()
event = EngineEvent(
    "unsafe.event",
    {"live_object": unsafe_value},
)
"""

    violations = _direct_engine_event_violations(
        source,
        source_name="positional_event_fixture.py",
    )

    assert violations == [
        "positional_event_fixture.py:5 adds unreviewed direct payload data "
        "to 'unsafe.event'"
    ]


def test_direct_engine_event_producers_use_static_named_payloads() -> None:
    """Direct producers must remain in the reviewed simple-data inventory."""

    violations: list[str] = []

    for checked_root in PROCESSING_ROOTS:
        for path in sorted(checked_root.rglob("*.py")):
            if path == EVENTS_PATH:
                continue

            source = path.read_text(encoding="utf-8")
            violations.extend(
                _direct_engine_event_violations(
                    source,
                    source_name=str(
                        path.relative_to(PROJECT_ROOT)
                    ),
                )
            )

    assert not violations, (
        "Direct EngineEvent producers must use literal names and either no "
        "payload or the reviewed simple job.changed summary. Add a named "
        "factory and transport-safety sample for new payload shapes.\n"
        + "\n".join(violations)
    )
