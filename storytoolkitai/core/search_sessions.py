"""
Engine-owned advanced search sessions.

The manager keeps live text and video search processors outside user
interfaces while StoryToolkitEngine retains the public search API.
"""

from __future__ import annotations

from copy import deepcopy
from threading import Lock, Thread
from copy import deepcopy
from threading import Lock, Thread
from typing import (
    Any,
    Callable,
    Literal,
    TypeAlias,
    TypedDict,
)

from storytoolkitai.core.logger import logger


# Queue statuses that indicate a text-search indexing job is still active.
#
# ``pending`` exists briefly while a queue ID is being initialized.
# ``queued`` waits for a processing device.
# ``processing`` is assigned before each queue task runs.
# ``reading files`` and ``indexing`` are the progress states reported by
# ToolkitOps.index_text().
# ``canceling`` means the worker is finishing its current task before the
# queue finalizes the job as canceled.
_SEARCH_ACTIVE_JOB_STATUSES = frozenset(
    {
        "pending",
        "queued",
        "processing",
        "reading files",
        "indexing",
        "canceling",
    }
)

# Queue statuses that mean a text-search indexing attempt cannot be reused.
#
# ``cancelled`` is retained as a defensive spelling variant even though the
# current ProcessingQueue implementation writes ``canceled``.
_SEARCH_FAILED_JOB_STATUSES = frozenset(
    {
        "failed",
        "canceled",
        "cancelled",
    }
)

# Successful queue completion is kept separate because it makes the associated
# search session immediately ready.
_SEARCH_DONE_JOB_STATUSES = frozenset(
    {
        "done",
    }
)


# These aliases document the existing Version 1 in-process search API.
# They keep the public dictionary and tuple shapes reviewable without adding
# runtime wrapper classes. Version 2 may replace them with serializable API
# models when search crosses a process boundary.
SearchComponentStatus: TypeAlias = Literal[
    "created",
    "preparing",
    "waiting_for_job",
    "ready",
    "failed",
    "not_available",
]
SearchStatus: TypeAlias = Literal[
    "created",
    "preparing",
    "waiting_for_job",
    "ready",
    "failed",
]


class SearchInfo(TypedDict):
    """Detached public state for one engine-owned search session."""

    search_id: str
    status: SearchStatus
    text_status: SearchComponentStatus
    video_status: SearchComponentStatus
    text_file_paths: list[str]
    video_file_paths: list[str]
    text_file_count: int
    video_file_count: int
    model_name: str | None
    text_job_id: str | None
    error: str | None


# Individual search results keep their existing open dictionary shape because
# text and video processors attach different metadata. The surrounding tuple
# is stable: detached result items followed by the effective result limit.
SearchResults: TypeAlias = tuple[list[dict[str, Any]], int]


class SearchSessionManager:
    """
    Own live advanced-search processors and their preparation state.

    StoryToolkitEngine delegates its public search methods to this manager.
    Search processor objects, worker threads, and mutable session dictionaries
    remain private implementation details.
    """

    def __init__(
        self,
        toolkit_ops_obj: Any,
        get_job: Callable[[str], dict[str, Any] | None],
        list_jobs: Callable[[], dict[str, dict[str, Any]]],
    ) -> None:
        """
        Create a manager around the existing processing implementation.

        Args:
            toolkit_ops_obj:
                ToolkitOps-compatible object that creates and prepares search
                processors.
            get_job:
                Callback returning detached public information for one queue
                job.
            list_jobs:
                Callback returning detached public information for all queue
                jobs.

        ``Any`` is intentional for the processing object. Importing ToolkitOps
        here would load the current heavyweight processing dependency tree.
        """

        self._toolkit_ops = toolkit_ops_obj
        self._get_job = get_job
        self._list_jobs = list_jobs

        # live search processors remain private to the manager
        self._sessions: dict[str, dict[str, Any]] = {}

        # search preparation may update session state from a worker thread
        self._sessions_lock = Lock()

    def _get_session(
        self,
        search_id: str,
    ) -> dict[str, Any] | None:
        """
        Return one internal search session.

        The returned dictionary is a manager implementation detail and must
        never be returned directly to a caller.
        """

        with self._sessions_lock:
            return self._sessions.get(search_id)

    @staticmethod
    def _get_status(
        session: dict[str, Any],
    ) -> SearchStatus:
        """Return the combined public status of one search session."""
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

    def _copy_info(
        self,
        session: dict[str, Any],
    ) -> SearchInfo:
        """
        Return detached public information about one search session.

        Live TextSearch and VideoSearch processors are intentionally excluded.
        The returned dictionary follows the stable ``SearchInfo`` shape.
        """

        text_search_item = session["text_search_item"]
        video_search_item = session["video_search_item"]

        search_info: SearchInfo = {
            "search_id": session["search_id"],
            "status": self._get_status(session),
            "text_status": session["text_status"],
            "video_status": session["video_status"],
            "text_file_paths": list(
                text_search_item.search_file_paths or []
            ),
            "video_file_paths": list(
                video_search_item.search_file_paths or []
            ),
            "text_file_count": text_search_item.search_file_paths_count,
            "video_file_count": video_search_item.search_file_paths_count,
            "model_name": getattr(
                text_search_item,
                "model_name",
                None,
            ),
            "text_job_id": session.get("text_job_id"),
            "error": session.get("error"),
        }

        return deepcopy(search_info)

    def create_search(
        self,
        search_file_paths: str | list[str] | tuple[str, ...],
        use_analyzer: bool = False,
    ) -> SearchInfo:
        """
        Create or reuse an engine-owned advanced search session.

        Args:
            search_file_paths:
                Files or directories selected by the user.
            use_analyzer:
                Whether text analysis should prepare the text corpus.

        Returns:
            A detached SearchInfo snapshot.
        """

        text_search_item, video_search_item = (
            self._toolkit_ops.create_search_items(
                search_file_paths=search_file_paths,
                use_analyzer=use_analyzer,
            )
        )

        # preserve the existing text corpus ID as the search window/session ID
        search_id = text_search_item.search_file_path_id

        with self._sessions_lock:
            existing_session = self._sessions.get(search_id)

            if existing_session is not None:
                return self._copy_info(existing_session)

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

            self._sessions[search_id] = session

        return self._copy_info(session)

    def _refresh_job_status(
        self,
        session: dict[str, Any],
    ) -> None:
        """
        Update a search session that depends on a processing-queue job.

        Queue statuses are converted into the smaller set of states exposed by
        the engine search interface. Known active and successful states clear
        stale errors left by an earlier queue state.
        """

        text_job_id = session.get("text_job_id")

        if not text_job_id:
            return

        job = self._get_job(text_job_id)

        if job is None:
            session["text_status"] = "failed"
            session["error"] = (
                "The text indexing job is no longer available."
            )
            return

        job_status = job.get("status")

        if job_status in _SEARCH_DONE_JOB_STATUSES:
            session["text_status"] = "ready"
            session["error"] = None
            return

        if job_status in _SEARCH_FAILED_JOB_STATUSES:
            session["text_status"] = "failed"
            session["error"] = (
                job.get("fail_error")
                or job.get("error")
                or "The text indexing job did not complete."
            )
            return

        if job_status in _SEARCH_ACTIVE_JOB_STATUSES:
            session["text_status"] = "waiting_for_job"
            session["error"] = None
            return

        # Keep an unknown queue state visible instead of treating it as
        # successful preparation. This also exposes newly introduced queue
        # states during development instead of silently hiding them.
        session["text_status"] = "waiting_for_job"
        session["error"] = (
            "The text indexing job reported an unknown status: {!r}.".format(
                job_status
            )
        )

    def get_search(
        self,
        search_id: str,
    ) -> SearchInfo | None:
        """
        Return detached information about an advanced search session.

        Waiting text-index jobs are checked before the public status is copied.

        Args:
            search_id: ID returned by ``create_search``.

        Returns:
            A detached ``SearchInfo`` snapshot, or ``None`` when the session
            does not exist.
        """

        session = self._get_session(search_id)

        if session is None:
            return None

        self._refresh_job_status(session)

        return self._copy_info(session)

    def _find_text_index_job(
        self,
        search_file_paths: list[str],
    ) -> tuple[str, dict[str, Any]] | None:
        """Return the newest queue item for the same text search paths."""

        matching_job = None

        for job_id, job in self._list_jobs().items():
            if job.get("item_type") != "search":
                continue

            if job.get("search_file_paths") != search_file_paths:
                continue

            # queue dictionaries retain insertion order, so keeping the last
            # match selects the newest known job for this corpus
            matching_job = job_id, job

        return matching_job

    def _prepare_worker(
        self,
        search_id: str,
        queue_item_name: str | None,
    ) -> None:
        """Prepare text and video search processors outside the UI thread."""

        session = self._get_session(search_id)

        if session is None:
            return

        text_search_item = session["text_search_item"]
        video_search_item = session["video_search_item"]

        try:
            # TEXT SEARCH
            if text_search_item.search_file_paths_count:
                session["text_status"] = "preparing"

                # corpus preparation is needed both for direct indexing and for
                # deciding which cache belongs to this set of source files
                text_search_item.prepare_search_corpus()

                existing_job = self._find_text_index_job(
                    list(text_search_item.search_file_paths),
                )

                if existing_job is not None:
                    existing_job_id, existing_job_info = existing_job
                    existing_status = existing_job_info.get("status")

                    if existing_status in _SEARCH_DONE_JOB_STATUSES:
                        session["text_job_id"] = existing_job_id
                        session["text_status"] = "ready"

                    elif existing_status in _SEARCH_ACTIVE_JOB_STATUSES:
                        session["text_job_id"] = existing_job_id
                        session["text_status"] = "waiting_for_job"

                    # failed and canceled jobs do not prevent a new attempt
                    elif existing_status in _SEARCH_FAILED_JOB_STATUSES:
                        existing_job = None

                    # unknown historical states cannot be reused safely
                    else:
                        logger.warning(
                            f"Ignoring text indexing job {existing_job_id} "
                            f"with unknown status {existing_status}."
                        )
                        existing_job = None

                # large corpora without a cache continue to use the persistent
                # processing queue so indexing survives the search window
                if (
                    existing_job is None
                    and text_search_item.search_file_paths_size > 300000
                    and not text_search_item.cache_exists
                ):
                    text_job_id = (
                        self._toolkit_ops.add_index_text_to_queue(
                            queue_item_name=(
                                queue_item_name
                                or "Preparing text search"
                            ),
                            search_file_paths=list(
                                text_search_item.search_file_paths
                            ),
                            use_analyzer=text_search_item.use_analyzer,
                        )
                    )

                    if not text_job_id:
                        session["text_status"] = "failed"
                        session["error"] = (
                            "The text search could not be added to the "
                            "processing queue."
                        )
                    else:
                        session["text_job_id"] = text_job_id
                        session["text_status"] = "waiting_for_job"

                elif existing_job is None:
                    # small corpora and existing caches can be prepared in the
                    # engine-owned worker without creating another queue item
                    self._toolkit_ops.index_text(
                        search_file_paths=list(
                            text_search_item.search_file_paths
                        ),
                        use_analyzer=text_search_item.use_analyzer,
                    )
                    session["text_status"] = "ready"

            # VIDEO SEARCH
            if video_search_item.search_file_paths_count:
                session["video_status"] = "preparing"

                video_search_item.load_index_paths()
                video_search_item.load_model()

                session["video_status"] = "ready"

        except Exception as exc:
            session["error"] = str(exc)

            if session["text_status"] == "preparing":
                session["text_status"] = "failed"

            if session["video_status"] == "preparing":
                session["video_status"] = "failed"

    def prepare_search(
        self,
        search_id: str,
        queue_item_name: str | None = None,
    ) -> SearchInfo | None:
        """
        Begin preparing an advanced search in an engine-owned worker.

        Calling this method again while preparation is active is harmless.

        Args:
            search_id:
                ID returned by ``create_search``.
            queue_item_name:
                Optional name for a persistent text-index queue item.

        Returns:
            The current detached ``SearchInfo`` snapshot, or ``None`` when the
            session does not exist.
        """

        session = self._get_session(search_id)

        if session is None:
            return None

        preparation_thread = session.get("preparation_thread")

        if (
            preparation_thread is not None
            and preparation_thread.is_alive()
        ):
            return self._copy_info(session)

        if self._get_status(session) in {"ready", "failed"}:
            return self._copy_info(session)

        preparation_thread = Thread(
            target=self._prepare_worker,
            kwargs={
                "search_id": search_id,
                "queue_item_name": queue_item_name,
            },
            name="search-preparation-{}".format(search_id[:8]),
            daemon=True,
        )

        session["preparation_thread"] = preparation_thread
        preparation_thread.start()

        return self._copy_info(session)

    def load_search_model(
        self,
        search_id: str,
        model_name: str,
    ) -> str | None:
        """
        Load a semantic model for one engine-owned text search.

        Returns the selected model name, or ``None`` when the search does not
        exist or has no text processor.
        """

        session = self._get_session(search_id)

        if session is None:
            return None

        text_search_item = session["text_search_item"]

        if not text_search_item.search_file_paths_count:
            return None

        text_search_item.load_model(
            model_name=model_name,
        )

        return getattr(
            text_search_item,
            "model_name",
            model_name,
        )

    def search_text(
        self,
        search_id: str,
        query: str,
        max_results: int = 5,
    ) -> SearchResults:
        """
        Run a text search and return detached result data.

        Args:
            search_id: ID returned by ``create_search``.
            query: Search query entered by the user.
            max_results: Default maximum number of results.

        Returns:
            A ``SearchResults`` tuple containing a detached result list and
            the effective maximum result count.
        """

        session = self._get_session(search_id)

        if session is None:
            return [], max_results

        self._refresh_job_status(session)

        if session["text_status"] != "ready":
            return [], max_results

        result = session["text_search_item"].search(
            query=query,
            max_results=max_results,
        )

        if not isinstance(result, tuple) or len(result) != 2:
            return [], max_results

        search_results, effective_max_results = result

        if not isinstance(search_results, list):
            search_results = []

        return deepcopy(search_results), int(effective_max_results)

    def search_video(
        self,
        search_id: str,
        query: str,
        max_results: int = 5,
        threshold: int = 35,
        combine_patches: bool = True,
    ) -> SearchResults:
        """
        Run a video search and return detached result data.

        VideoSearch returns both the matching frames and the effective result
        count after parsing any result limit included in the query.

        Returns:
            A ``SearchResults`` tuple containing a detached result list and
            the effective maximum result count.
        """
        session = self._get_session(search_id)

        if session is None or session["video_status"] != "ready":
            return [], max_results

        result = session["video_search_item"].search(
            query=query,
            max_results=max_results,
            threshold=threshold,
            combine_patches=combine_patches,
        )

        if not isinstance(result, tuple) or len(result) != 2:
            return [], max_results

        search_results, effective_max_results = result

        if not isinstance(search_results, list):
            search_results = []

        return deepcopy(search_results), int(effective_max_results)

    def get_search_video_frame(
        self,
        search_id: str,
        full_path: str,
        frame: int,
    ) -> Any:
        """
        Return one frame used to render a video-search result.

        Returning the existing image array is an accepted version 1 in-process
        bridge. Version 2 must replace it with bytes or an artifact reference
        before search crosses the service boundary.
        """

        session = self._get_session(search_id)

        if session is None:
            return None

        return session["video_search_item"].video_frame(
            full_path,
            frame,
        )

    def close_search(
        self,
        search_id: str,
    ) -> bool:
        """
        Remove a search session from the manager registry.

        SearchItem currently keeps its own corpus cache, so closing a session
        does not unload a reusable model or delete an embedding cache.

        Args:
            search_id: ID returned by ``create_search``.

        Returns:
            True when the session existed, otherwise False.
        """

        with self._sessions_lock:
            return self._sessions.pop(
                search_id,
                None,
            ) is not None
