"""Tests for engine-owned advanced search session state."""

from __future__ import annotations

from typing import Any

import pytest

from storytoolkitai.core.search_sessions import SearchSessionManager


@pytest.fixture
def jobs() -> dict[str, dict[str, Any]]:
    """Return mutable fake queue data for search-status tests."""

    return {}


@pytest.fixture
def manager(
    jobs: dict[str, dict[str, Any]],
) -> SearchSessionManager:
    """Return a manager using small queue lookup callbacks."""

    return SearchSessionManager(
        toolkit_ops_obj=object(),
        get_job=jobs.get,
        list_jobs=lambda: jobs,
    )


def _make_search_job_session(
    *,
    job_id: str | None,
    text_status: str = "waiting_for_job",
    error: str | None = None,
) -> dict[str, Any]:
    """
    Return the smallest search-session state needed for job-status tests.

    These tests exercise the private transition helper intentionally. The
    helper owns the conversion from processing-queue states into public search
    states.
    """

    return {
        "text_job_id": job_id,
        "text_status": text_status,
        "error": error,
    }


def test_refresh_job_status_without_job_id_is_noop(
    manager: SearchSessionManager,
) -> None:
    """A search without a queue job keeps its existing state."""

    session = _make_search_job_session(
        job_id=None,
        text_status="created",
        error="Existing session message.",
    )

    manager._refresh_job_status(session)

    assert session == {
        "text_job_id": None,
        "text_status": "created",
        "error": "Existing session message.",
    }


def test_refresh_job_status_marks_missing_job_as_failed(
    manager: SearchSessionManager,
) -> None:
    """A removed queue job becomes an explicit failed search state."""

    session = _make_search_job_session(
        job_id="missing-search-job",
    )

    manager._refresh_job_status(session)

    assert session["text_status"] == "failed"
    assert session["error"] == (
        "The text indexing job is no longer available."
    )


@pytest.mark.parametrize(
    "job_status",
    [
        "pending",
        "queued",
        "processing",
        "reading files",
        "indexing",
        "canceling",
    ],
)
def test_refresh_job_status_keeps_active_job_waiting(
    manager: SearchSessionManager,
    jobs: dict[str, dict[str, Any]],
    job_status: str,
) -> None:
    """Every active queue state maps to a waiting search state."""

    jobs["job-search"] = {
        "queue_id": "job-search",
        "status": job_status,
    }
    session = _make_search_job_session(
        job_id="job-search",
        error="Stale error from an earlier status.",
    )

    manager._refresh_job_status(session)

    assert session["text_status"] == "waiting_for_job"
    assert session["error"] is None


def test_refresh_job_status_marks_done_job_as_ready(
    manager: SearchSessionManager,
    jobs: dict[str, dict[str, Any]],
) -> None:
    """A completed indexing job clears errors and makes search ready."""

    jobs["job-search"] = {
        "queue_id": "job-search",
        "status": "done",
    }
    session = _make_search_job_session(
        job_id="job-search",
        error="Stale error from an earlier status.",
    )

    manager._refresh_job_status(session)

    assert session["text_status"] == "ready"
    assert session["error"] is None


@pytest.mark.parametrize(
    ("job_data", "expected_error"),
    [
        (
            {
                "status": "failed",
                "fail_error": "Text indexing raised an exception.",
                "error": "Less specific error.",
            },
            "Text indexing raised an exception.",
        ),
        (
            {
                "status": "failed",
                "error": "Text indexing failed.",
            },
            "Text indexing failed.",
        ),
        (
            {
                "status": "failed",
            },
            "The text indexing job did not complete.",
        ),
        (
            {
                "status": "canceled",
            },
            "The text indexing job did not complete.",
        ),
        (
            {
                "status": "cancelled",
            },
            "The text indexing job did not complete.",
        ),
    ],
)
def test_refresh_job_status_marks_unsuccessful_job_as_failed(
    manager: SearchSessionManager,
    jobs: dict[str, dict[str, Any]],
    job_data: dict[str, Any],
    expected_error: str,
) -> None:
    """Failed and canceled queue states expose a useful search error."""

    jobs["job-search"] = {
        "queue_id": "job-search",
        **job_data,
    }
    session = _make_search_job_session(
        job_id="job-search",
    )

    manager._refresh_job_status(session)

    assert session["text_status"] == "failed"
    assert session["error"] == expected_error


def test_refresh_job_status_exposes_unknown_queue_state(
    manager: SearchSessionManager,
    jobs: dict[str, dict[str, Any]],
) -> None:
    """An unknown queue state remains visible during development."""

    jobs["job-search"] = {
        "queue_id": "job-search",
        "status": "paused",
    }
    session = _make_search_job_session(
        job_id="job-search",
    )

    manager._refresh_job_status(session)

    assert session["text_status"] == "waiting_for_job"
    assert session["error"] == (
        "The text indexing job reported an unknown status: 'paused'."
    )
