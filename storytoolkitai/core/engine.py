"""
UI-independent entry point for StoryToolkitAI operations.

The engine provides a small public interface between user interfaces and the
existing processing implementation. During the version 1 migration, methods
will be added here one feature at a time.

User interfaces should call this object instead of accessing ToolkitOps,
ProcessingQueue, or other processing internals directly.
"""

from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Any

from storytoolkitai.core.events import EventListener


# These queue fields contain runtime implementation details rather than stable
# job information suitable for a UI.
#
# - task_queue contains Python callables.
# - last_task may contain the callable currently being executed.
# - output can contain temporary processing objects with no stable data shape.
#
# The existing queue serializer excludes the same fields. A future explicit
# result API can expose stable job results when their required shape is known.
_RUNTIME_JOB_FIELDS = frozenset(
    {
        "task_queue",
        "last_task",
        "output",
    }
)


class StoryToolkitEngine:
    """
    Small public facade for UI-independent StoryToolkitAI operations.

    The initial facade exposes only queue inspection and cancellation. More
    operations should be added only when a UI feature is migrated to use them.

    ToolkitOps remains the underlying implementation during the migration, but
    it is intentionally kept private so callers do not depend on its internals.
    """

    def __init__(self, toolkit_ops_obj: Any) -> None:
        """
        Create an engine around the existing ToolkitOps instance.

        Args:
            toolkit_ops_obj:
                Existing ToolkitOps-compatible object. It must provide a
                ``processing_queue`` attribute.

        ``Any`` is intentional here. Importing ToolkitOps would also import the
        current heavyweight processing dependency tree, which is unnecessary
        for this lightweight facade and its tests.
        """

        self._toolkit_ops = toolkit_ops_obj

        # live search processors remain private to the engine
        self._search_sessions: dict[str, dict[str, Any]] = {}

        # search preparation may update session state from a worker thread
        self._search_sessions_lock = Lock()

    def subscribe(self, listener: EventListener) -> None:
        """
        Subscribe to processing events.

        Listeners may be called from a processing worker thread. A graphical
        UI must move widget changes onto its own UI thread.

        Args:
            listener:
                Function or bound method that accepts one EngineEvent.
        """

        self._toolkit_ops.events.subscribe(listener)

    def unsubscribe(self, listener: EventListener) -> None:
        """
        Stop receiving processing events.

        Removing a listener that is not subscribed is harmless.

        Args:
            listener:
                Previously subscribed function or bound method.
        """

        self._toolkit_ops.events.unsubscribe(listener)

    def get_resolve_marker_colors(self) -> dict:
        """
        Return marker colors for the current Resolve timeline
        """

        return deepcopy(
            self._toolkit_ops.get_resolve_marker_colors()
        )

    def copy_resolve_markers(self, source: str) -> dict:
        """
        Copy Resolve markers between timeline and bin clip
        """

        return deepcopy(
            self._toolkit_ops.copy_resolve_markers(
                source=source,
            )
        )

    def render_resolve_markers(
        self,
        *,
        marker_color: str | None,
        target_dir: str,
        starts_with: str | None = None,
        render_stills: bool = False,
    ) -> dict:
        """render selected markers from the current Resolve timeline"""

        return deepcopy(
            self._toolkit_ops.render_resolve_markers(
                marker_color=marker_color,
                target_dir=target_dir,
                starts_with=starts_with,
                render_stills=render_stills,
            )
        )

    def create_ingest_job(
        self,
        name: str | None = None,
    ) -> str:
        """
        Create a queue item for an ingest whose settings are being selected.

        The placeholder makes the ingest visible in the queue before the user
        submits the settings form. Processing owns the queue ID and its status;
        the UI only keeps the returned ID.

        Args:
            name: Optional name used when generating the queue ID.

        Returns:
            The generated queue ID.
        """

        queue_id = self._toolkit_ops.processing_queue.generate_queue_id(
            name=name,
        )

        self._toolkit_ops.processing_queue.update_queue_item(
            queue_id=queue_id,
            name=name or "",
            status="waiting user",
        )

        return queue_id

    def create_timeline_ingest_job(
        self,
        name: str,
    ) -> str:
        """
        Create an ingest queue item for a timeline waiting to be rendered.

        Args:
            name: Name of the timeline render.

        Returns:
            The generated queue ID.
        """

        queue_id = self._toolkit_ops.processing_queue.generate_queue_id(
            name=name,
        )

        self._toolkit_ops.processing_queue.update_queue_item(
            queue_id=queue_id,
            name=name,
            status="waiting for render",
        )

        return queue_id

    def mark_ingest_job_waiting_for_user(
        self,
        job_id: str,
    ) -> bool:
        """
        Mark an ingest job as waiting for its settings to be confirmed.

        This is used both for normal ingest windows and after a Resolve
        timeline has finished rendering.

        Args:
            job_id: Queue ID of the ingest job.

        Returns:
            True when the queue item was updated, otherwise False.
        """

        result = self._toolkit_ops.processing_queue.update_queue_item(
            queue_id=job_id,
            status="waiting user",
        )

        return bool(result)

    def start_ingest(
        self,
        ingest_settings: Any,
    ) -> list[str] | bool:
        """
        Validate the ingest request and add its processing jobs to the queue.

        The current IngestSettings model remains the in-process boundary for
        version 1. A serializable API model can replace it when the version 2
        process boundary is introduced.

        Args:
            ingest_settings: Existing IngestSettings instance created by the UI.

        Returns:
            Queue IDs created for the ingest, or False when nothing was queued.
        """

        result = self._toolkit_ops.add_media_to_queue(
            ingest_settings=ingest_settings,
        )

        return deepcopy(result)

    def _get_search_session(
        self,
        search_id: str,
    ) -> dict[str, Any] | None:
        """
        Return one internal search session.

        The returned dictionary is an engine implementation detail and must
        never be returned directly to a caller.
        """

        with self._search_sessions_lock:
            return self._search_sessions.get(search_id)

    @staticmethod
    def _get_search_status(
        session: dict[str, Any],
    ) -> str:
        """Return the combined public status of one search session."""

        component_statuses = {
            session["text_status"],
            session["video_status"],
        }

        if session.get("error") or "failed" in component_statuses:
            return "failed"

        if component_statuses.issubset({"ready", "not_available"}):
            return "ready"

        if "waiting_for_job" in component_statuses:
            return "waiting_for_job"

        if "preparing" in component_statuses:
            return "preparing"

        return "created"

    def _copy_search_info(
        self,
        session: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Return detached information about one search session.

        Live TextSearch and VideoSearch processors are intentionally excluded.
        """

        text_search_item = session["text_search_item"]
        video_search_item = session["video_search_item"]

        search_info = {
            "search_id": session["search_id"],
            "status": self._get_search_status(session),
            "text_status": session["text_status"],
            "video_status": session["video_status"],
            "text_file_paths": list(text_search_item.search_file_paths or []),
            "video_file_paths": list(video_search_item.search_file_paths or []),
            "text_file_count": text_search_item.search_file_paths_count,
            "video_file_count": video_search_item.search_file_paths_count,
            "model_name": getattr(text_search_item, "model_name", None),
            "text_job_id": session.get("text_job_id"),
            "error": session.get("error"),
        }

        return deepcopy(search_info)

    def create_search(
        self,
        search_file_paths: list[str],
        use_analyzer: bool = False,
    ) -> dict[str, Any]:
        """
        Create or reuse an engine-owned advanced search session.

        Args:
            search_file_paths:
                Files or directories selected by the user.
            use_analyzer:
                Whether text analysis should prepare the text corpus.

        Returns:
            Detached public information about the search session.
        """

        text_search_item, video_search_item = (
            self._toolkit_ops.create_search_items(
                search_file_paths=search_file_paths,
                use_analyzer=use_analyzer,
            )
        )

        # preserve the existing text corpus ID as the search window/session ID
        search_id = text_search_item.search_file_path_id

        with self._search_sessions_lock:
            existing_session = self._search_sessions.get(search_id)

            if existing_session is not None:
                return self._copy_search_info(existing_session)

            session = {
                "search_id": search_id,
                "text_search_item": text_search_item,
                "video_search_item": video_search_item,
                "text_status": (
                    "created"
                    if text_search_item.search_file_paths_count
                    else "not_available"
                ),
                "video_status": (
                    "created"
                    if video_search_item.search_file_paths_count
                    else "not_available"
                ),
                "text_job_id": None,
                "preparation_thread": None,
                "error": None,
            }

            self._search_sessions[search_id] = session

        return self._copy_search_info(session)

    def get_search(
        self,
        search_id: str,
    ) -> dict[str, Any] | None:
        """
        Return detached information about an advanced search session.

        Args:
            search_id: ID returned by ``create_search``.

        Returns:
            Search information, or ``None`` when the session does not exist.
        """

        session = self._get_search_session(search_id)

        if session is None:
            return None

        return self._copy_search_info(session)

    def close_search(
        self,
        search_id: str,
    ) -> bool:
        """
        Remove a search session from the engine registry.

        SearchItem currently keeps its own corpus cache, so closing a session
        does not unload a reusable model or delete an embedding cache.

        Args:
            search_id: ID returned by ``create_search``.

        Returns:
            True when the session existed, otherwise False.
        """

        with self._search_sessions_lock:
            return self._search_sessions.pop(search_id, None) is not None

    @staticmethod
    def _copy_job(item: dict[str, Any]) -> dict[str, Any]:
        """
        Return a detached job dictionary suitable for an engine caller.

        Runtime-only fields are removed before copying. The deep copy prevents
        callers from mutating nested values inside the queue's stored item.
        """

        public_item = {
            key: value
            for key, value in item.items()
            if key not in _RUNTIME_JOB_FIELDS
        }

        return deepcopy(public_item)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        """
        Return public information for one processing job.

        The returned dictionary is detached from the queue's internal state.
        Mutating it will not modify the real queue item.

        Args:
            job_id:
                Queue ID of the requested job.

        Returns:
            A copied public job dictionary, or ``None`` when no job exists.
        """

        item = self._toolkit_ops.processing_queue.get_item(
            queue_id=job_id,
        )

        if not isinstance(item, dict):
            return None

        return self._copy_job(item)

    def list_jobs(
        self,
        status: str | list[str] | None = None,
        not_status: str | list[str] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """
        Return public information for processing jobs.

        The existing queue status filters are forwarded unchanged. Every item
        in the returned dictionary is detached from the queue's internal state.

        Args:
            status:
                Include only jobs with this status or one of these statuses.
            not_status:
                Exclude jobs with this status or one of these statuses.

        Returns:
            A dictionary keyed by job ID.
        """

        items = self._toolkit_ops.processing_queue.get_all_queue_items(
            status=status,
            not_status=not_status,
        )

        if not isinstance(items, dict):
            return {}

        return {
            job_id: self._copy_job(item)
            for job_id, item in items.items()
            if isinstance(item, dict)
        }

    def cancel_job(self, job_id: str) -> bool:
        """
        Request safe cancellation of a processing job.

        A queued job can be canceled immediately. A running job enters the
        ``canceling`` state so its current task can finish before the remaining
        tasks are stopped.

        Args:
            job_id:
                Queue ID of the job to cancel.

        Returns:
            ``True`` when cancellation was accepted, otherwise ``False``.
        """
        result = self._toolkit_ops.processing_queue.set_to_canceled(
            queue_id=job_id,
        )
        return bool(result)

