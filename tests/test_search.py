"""Characterization tests for lightweight search path handling."""

from __future__ import annotations

from pathlib import Path

import pytest

from storytoolkitai.core.toolkit_ops.search_paths import (
    calculate_search_file_paths_size,
    create_search_file_path_id,
    filter_search_file_paths,
    is_text_search_file,
    is_video_search_file,
)


def test_search_file_path_id_is_stable_for_the_same_paths() -> None:
    """The same ordered paths must identify the same search corpus."""

    search_file_paths = [
        "/tmp/interview.transcription.json",
        "/tmp/notes.txt",
    ]

    first_id = create_search_file_path_id(search_file_paths)
    second_id = create_search_file_path_id(search_file_paths)

    assert first_id == second_id


def test_search_file_path_id_depends_on_path_order() -> None:
    """
    Record that the current corpus ID depends on path order.

    Normal application searches sort their paths before generating the ID.
    This test protects the existing hash behavior during the refactor.
    """

    first_id = create_search_file_path_id(
        [
            "/tmp/a.txt",
            "/tmp/b.txt",
        ]
    )
    second_id = create_search_file_path_id(
        [
            "/tmp/b.txt",
            "/tmp/a.txt",
        ]
    )

    assert first_id != second_id


def test_filter_file_paths_returns_sorted_unique_files(
    tmp_path: Path,
) -> None:
    """Search path filtering removes duplicates and sorts the result."""

    second_file = tmp_path / "b.txt"
    first_file = tmp_path / "a.txt"
    ignored_file = tmp_path / "ignored.md"

    second_file.write_text("second", encoding="utf-8")
    first_file.write_text("first", encoding="utf-8")
    ignored_file.write_text("ignored", encoding="utf-8")

    filtered_paths = filter_search_file_paths(
        search_paths=[
            str(second_file),
            str(first_file),
            str(first_file),
            str(ignored_file),
        ],
        file_validator=is_text_search_file,
    )

    assert filtered_paths == [
        str(first_file),
        str(second_file),
    ]


def test_filter_file_paths_recursively_reads_directories(
    tmp_path: Path,
) -> None:
    """Directory filtering retains the current recursive behavior."""

    nested_directory = tmp_path / "nested"
    nested_directory.mkdir()

    root_file = tmp_path / "root.txt"
    nested_file = nested_directory / "nested.transcription.json"
    ignored_file = nested_directory / "ignored.md"

    root_file.write_text("root", encoding="utf-8")
    nested_file.write_text("{}", encoding="utf-8")
    ignored_file.write_text("ignored", encoding="utf-8")

    filtered_paths = filter_search_file_paths(
        search_paths=str(tmp_path),
        file_validator=is_text_search_file,
    )

    assert filtered_paths == sorted(
        [
            str(root_file),
            str(nested_file),
        ]
    )


def test_filter_file_paths_ignores_hidden_directories(
    tmp_path: Path,
) -> None:
    """Files below hidden directories remain excluded from search."""

    visible_file = tmp_path / "visible.txt"
    visible_file.write_text("visible", encoding="utf-8")

    hidden_directory = tmp_path / ".hidden"
    hidden_directory.mkdir()

    hidden_file = hidden_directory / "hidden.txt"
    hidden_file.write_text("hidden", encoding="utf-8")

    filtered_paths = filter_search_file_paths(
        search_paths=str(tmp_path),
        file_validator=is_text_search_file,
    )

    assert filtered_paths == [str(visible_file)]


def test_search_file_sizes_are_combined(tmp_path: Path) -> None:
    """Corpus size is the total byte size of its selected files."""

    first_file = tmp_path / "first.txt"
    second_file = tmp_path / "second.txt"

    first_file.write_bytes(b"1234")
    second_file.write_bytes(b"123456")

    assert calculate_search_file_paths_size(
        [
            str(first_file),
            str(second_file),
        ]
    ) == 10


def test_empty_search_file_list_has_zero_size() -> None:
    """An empty search corpus has no file size."""

    assert calculate_search_file_paths_size([]) == 0
    assert calculate_search_file_paths_size(None) == 0


@pytest.mark.parametrize(
    ("file_path", "expected"),
    [
        ("interview.transcription.json", True),
        ("notes.txt", True),
        ("project.json", True),
        ("timeline.json", False),
        ("video.mov", False),
    ],
)
def test_text_search_supported_files(
    file_path: str,
    expected: bool,
) -> None:
    """Record the file types currently accepted by text search."""

    assert is_text_search_file(file_path) is expected


@pytest.mark.parametrize(
    ("file_path", "expected"),
    [
        ("interview.transcription.json", True),
        ("notes.txt", False),
        ("project.json", False),
        ("video.mov", False),
    ],
)
def test_video_search_supported_files(
    file_path: str,
    expected: bool,
) -> None:
    """Record the file types currently accepted by video search."""

    assert is_video_search_file(file_path) is expected
