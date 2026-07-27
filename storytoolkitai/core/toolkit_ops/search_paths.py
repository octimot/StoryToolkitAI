"""
Lightweight path handling shared by text and video search.

This module intentionally imports no model, Torch, NumPy or video-processing
dependencies. Path validation and corpus identification must remain usable by
tests and future clients without loading the search-processing stack.
"""

from __future__ import annotations

import hashlib
import os
import time
from collections.abc import Callable


def create_search_file_path_id(
    search_file_paths: list[str] | tuple[str, ...] | None,
) -> str:
    """
    Return the identifier currently used for one set of search paths.

    Path order remains significant for compatibility with the existing
    SearchItem implementation. Normal application searches sort their paths
    before calculating this identifier.
    """

    # empty searches currently receive a unique time-based identifier
    if not search_file_paths:
        empty_search_value = "empty_{}".format(time.time())

        return hashlib.md5(
            empty_search_value.encode("utf-8"),
        ).hexdigest()

    # preserve the existing separator and order-dependent hash behavior
    joined_search_file_paths = "__".join(search_file_paths)

    return hashlib.md5(
        joined_search_file_paths.encode("utf-8"),
    ).hexdigest()


def filter_search_file_paths(
    search_paths: str | list[str] | tuple[str, ...] | None,
    file_validator: Callable[[str], bool],
) -> list[str]:
    """
    Return sorted unique files accepted by ``file_validator``.

    The behavior intentionally matches the existing SearchItem implementation:
    a single file, a list or tuple of files, or one recursively scanned
    directory may be provided.
    """

    filtered_search_file_paths: list[str] = []

    # a single valid file can be returned directly
    if (
        type(search_paths) is str
        and os.path.isfile(search_paths)
        and file_validator(search_paths)
    ):
        filtered_search_file_paths = [search_paths]

    # lists and tuples may contain duplicate or unsupported paths
    elif type(search_paths) is list or type(search_paths) is tuple:
        for search_path in search_paths:
            if (
                os.path.isfile(search_path)
                and file_validator(search_path)
            ):
                filtered_search_file_paths.append(search_path)

    # directories are scanned recursively for supported files
    elif type(search_paths) is str and os.path.isdir(search_paths):
        for root, _directories, files in os.walk(search_paths):
            # preserve the current behavior of ignoring hidden directories
            if os.path.basename(root).startswith("."):
                continue

            for file_name in files:
                if file_validator(file_name):
                    filtered_search_file_paths.append(
                        os.path.join(root, file_name),
                    )

    # search processing expects stable sorted paths without duplicates
    return sorted(set(filtered_search_file_paths))


def calculate_search_file_paths_size(
    search_file_paths: list[str] | tuple[str, ...] | None,
) -> int:
    """Return the combined byte size of the selected search files."""

    if not search_file_paths:
        return 0

    return sum(
        os.path.getsize(file_path)
        for file_path in search_file_paths
    )


def is_text_search_file(file_path: str) -> bool:
    """Return whether the path is accepted by the current text search."""

    return file_path.endswith(
        (
            ".transcription.json",
            ".txt",
            "project.json",
        )
    )


def is_video_search_file(file_path: str) -> bool:
    """
    Return whether the path can point to a transcription video index.

    VideoSearch currently begins from a transcription file and resolves its
    associated video-index path from the transcription metadata.
    """

    return file_path.endswith(".transcription.json")
