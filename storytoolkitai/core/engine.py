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
        Request cancellation of a processing job.

        Args:
            job_id:
                Queue ID of the job to cancel.

        Returns:
            ``True`` when the queue found and updated the job, otherwise
            ``False``.
        """

        result = self._toolkit_ops.processing_queue.cancel_item(
            queue_id=job_id,
        )

        return bool(result)

