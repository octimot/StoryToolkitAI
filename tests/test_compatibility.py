from __future__ import annotations

import json
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from storytoolkitai.core.toolkit_ops.projects import Project
from storytoolkitai.core.toolkit_ops.transcription import (
    Transcription,
    TranscriptionUtils,
)

FIXTURE_ROOT = (
    Path(__file__).parent
    / "fixtures"
    / "compatibility"
    / "v0.25.1"
)
SUBPROCESS_RUNNER = (
    Path(__file__).parent
    / "support"
    / "compatibility_subprocess.py"
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_fixture(name: str, destination: Path) -> Path:
    shutil.copy2(FIXTURE_ROOT / name, destination)
    return destination


def _run_isolated_scenario(
    scenario: str,
    *paths: Path,
) -> None:
    """Run stub-dependent compatibility code outside the pytest process."""

    result = subprocess.run(
        [
            sys.executable,
            str(SUBPROCESS_RUNNER),
            scenario,
            *(str(path) for path in paths),
        ],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, (
        "Compatibility subprocess failed.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


def _assert_only_expected_round_trip_changes(
    original: dict[str, Any],
    saved: dict[str, Any],
    *,
    changed_values: dict[str, Any],
) -> None:
    """Require the existing schema and all unrelated values to survive."""

    assert set(saved) == set(original)

    expected = deepcopy(original)
    expected.update(changed_values)

    # Saving intentionally refreshes this existing metadata value.
    assert saved["last_modified"].isdigit()
    expected["last_modified"] = saved["last_modified"]

    assert saved == expected


def test_v0251_project_loads_and_exports_without_schema_changes(
    tmp_path: Path,
) -> None:
    """Load a sanitized stable project and preserve its archived JSON."""

    project_path = tmp_path / "compatibility-project"
    project_path.mkdir()
    original_path = _copy_fixture(
        "project.json",
        project_path / "project.json",
    )
    (project_path / "cache").mkdir()

    original = _read_json(original_path)
    project = Project(
        project_path=str(project_path),
        force_reload=True,
    )

    assert project.exists is True
    assert project.to_dict() == original

    export_base = tmp_path / "exports" / "compatibility-project"
    assert project.export(str(export_base)) is True

    with ZipFile(export_base.with_suffix(".zip")) as archive:
        assert set(archive.namelist()) == {"project.json", "cache/"}
        archived_project = json.loads(
            archive.read("project.json").decode("utf-8")
        )

    assert archived_project == original


def test_v0251_transcription_round_trip_preserves_schema_and_extensions(
    tmp_path: Path,
) -> None:
    """A stable transcription keeps known and unrecognized nested data."""

    transcription_path = _copy_fixture(
        "interview.transcription.json",
        tmp_path / "interview.transcription.json",
    )
    original = _read_json(transcription_path)

    transcription = Transcription(
        str(transcription_path),
        force_reload=True,
    )

    assert transcription.exists is True
    assert transcription.is_transcription_file is True
    assert transcription.to_dict() == original

    transcription.set("language", "de")
    assert transcription.save_soon(sec=0)

    saved = _read_json(transcription_path)
    _assert_only_expected_round_trip_changes(
        original,
        saved,
        changed_values={"language": "de"},
    )


def test_v0251_story_round_trip_preserves_schema_and_extensions(
    tmp_path: Path,
) -> None:
    """A stable story keeps story-line and top-level extension values."""

    story_path = _copy_fixture(
        "assembly.story.json",
        tmp_path / "assembly.story.json",
    )
    original = _read_json(story_path)

    _run_isolated_scenario(
        "story_round_trip",
        story_path,
    )

    saved = _read_json(story_path)
    _assert_only_expected_round_trip_changes(
        original,
        saved,
        changed_values={"language": "de"},
    )


def test_v0251_representative_text_exports_remain_compatible(
    tmp_path: Path,
) -> None:
    """Pin deterministic SRT, transcription text, and story text exports."""

    transcription_path = _copy_fixture(
        "interview.transcription.json",
        tmp_path / "interview.transcription.json",
    )
    story_path = _copy_fixture(
        "assembly.story.json",
        tmp_path / "assembly.story.json",
    )
    transcription = Transcription(
        str(transcription_path),
        force_reload=True,
    )

    srt_path = tmp_path / "interview.srt"
    transcript_text_path = tmp_path / "interview.txt"
    story_text_path = tmp_path / "assembly.txt"

    TranscriptionUtils.write_srt(transcription.segments, srt_path)
    TranscriptionUtils.write_txt(
        transcription.segments,
        transcript_text_path,
    )
    _run_isolated_scenario(
        "story_text_export",
        story_path,
        story_text_path,
    )

    for actual, expected_name in (
        (srt_path, "interview.srt"),
        (transcript_text_path, "interview.txt"),
        (story_text_path, "assembly.txt"),
    ):
        expected = (
            FIXTURE_ROOT / expected_name
        ).read_text(encoding="utf-8")

        # The SRT writer terminates each cue with a blank separator line,
        # including the final cue. Keep the fixture diff-clean while pinning
        # that final newline explicitly.
        if expected_name == "interview.srt":
            expected += "\n"

        assert actual.read_text(encoding="utf-8") == expected


def test_v0251_queue_recovery_dependencies_cancellation_and_snapshots(
    tmp_path: Path,
) -> None:
    """
    Restore stable queue data without executing tasks, then exercise state.

    Task callables and queue scheduling are mocked. Persistence, dependency
    decisions, cancellation, and public engine snapshots use production code.
    """

    queue_path = _copy_fixture(
        "queue.json",
        tmp_path / "queue.json",
    )
    _run_isolated_scenario(
        "queue_recovery",
        queue_path,
    )
