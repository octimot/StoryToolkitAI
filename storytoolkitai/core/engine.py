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
from threading import Lock, Thread
from typing import Any

from storytoolkitai.core.logger import logger
from storytoolkitai.core.events import (
    EventListener,
    create_project_changed_event,
    create_transcription_changed_event,
)


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


class AssistantSession:
    """
    Public in-process handle for one engine-owned assistant.

    The Tk interface keeps this lightweight handle, while the real assistant
    implementation and its ToolkitOps dependency remain private inside
    StoryToolkitEngine.

    This is intentionally an in-process Version 1 API. A future process-based
    API will replace it with serializable commands and events.
    """

    def __init__(
        self,
        engine: "StoryToolkitEngine",
        session_id: str,
    ) -> None:
        self._engine = engine
        self._session_id = session_id

    @property
    def session_id(self) -> str:
        """
        Return the stable engine session ID.
        """

        return self._session_id

    def _item(self):
        """
        Resolve the current private assistant implementation.

        The implementation may change when the user switches models while the
        public session handle and session ID remain stable.
        """

        return self._engine._get_assistant_item(
            self._session_id,
        )

    @property
    def model_provider(self) -> str:
        return self._item().model_provider

    @property
    def model_name(self) -> str:
        return self._item().model_name

    @property
    def model_description(self) -> str:
        return self._item().model_description

    @property
    def available_models(self) -> dict:
        return deepcopy(
            self._item().available_models
        )

    @property
    def tokens_used(self) -> dict:
        return deepcopy(
            self._item().tokens_used
        )

    @property
    def context(self):
        return deepcopy(
            self._item().context
        )

    @property
    def last_assistant_message_idx(self):
        return self._item().last_assistant_message_idx

    @property
    def assistant_id(self) -> str:
        """
        Return the implementation-specific assistant ID.

        UI code should use ``session_id`` for lifecycle operations. This
        property remains available for existing presentation behaviour.
        """

        return self._item().assistant_id

    @property
    def chat_history_length(self) -> int:
        """
        Return the number of private assistant-history entries.
        """

        return len(
            self._item().chat_history
        )

    def insert_chat_history(
        self,
        *,
        index: int,
        item: dict,
    ) -> bool:
        """
        Insert one detached item into the private assistant history.
        """

        self._item().chat_history.insert(
            index,
            deepcopy(item),
        )

        return True

    def pop_chat_history(
        self,
        *,
        index: int,
    ):
        """
        Remove and return one private assistant-history item.
        """

        return self._item().chat_history.pop(
            index
        )

    def add_context(
        self,
        context: str,
    ):
        return self._item().add_context(
            context=context,
        )

    def set_system(
        self,
        system_message: str,
    ):
        return self._item().set_system(
            system_message=system_message,
        )

    def calculate_history_tokens(self):
        return self._item().calculate_history_tokens()

    def reset(self):
        return self._item().reset()

    def send_query(
        self,
        *args: Any,
        **kwargs: Any,
    ):
        """
        Send a query using the private assistant implementation.

        The flexible signature intentionally preserves the existing assistant
        implementations during the Version 1 boundary migration.
        """

        return self._item().send_query(
            *args,
            **kwargs,
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


        # keep live assistant implementations inside the engine
        self._assistant_sessions = {}
        self._assistant_sessions_lock = Lock()

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
            listener: Previously subscribed function or bound method.
        """

        self._toolkit_ops.events.unsubscribe(listener)

    # ASSISTANT SESSIONS

    def _get_assistant_item(
        self,
        session_id: str,
    ):
        """
        Return the private assistant implementation for one session.

        This method is used only by AssistantSession and engine lifecycle
        operations. Interfaces must not call or receive the returned object.
        """

        with self._assistant_sessions_lock:
            assistant_item = self._assistant_sessions.get(
                session_id
            )

        if assistant_item is None:
            raise KeyError(
                "Assistant session not found: {}".format(
                    session_id
                )
            )

        return assistant_item

    def get_assistant_default_system_message(self) -> str:
        """
        Return the default assistant system prompt.
        """

        return str(
            self._toolkit_ops.get_assistant_default_system_message()
        )

    def get_assistant_providers(self) -> list:
        """
        Return configured assistant model providers.
        """

        providers = self._toolkit_ops.get_assistant_providers()

        if not providers:
            return []

        return deepcopy(
            list(providers)
        )

    def get_assistant_models(
        self,
        *,
        provider: str | None = None,
        refresh_provider: bool = False,
    ) -> list:
        """
        Return available model names for one assistant provider.
        """

        models = self._toolkit_ops.get_assistant_models(
            provider=provider,
            refresh_provider=refresh_provider,
        )

        if not models:
            return []

        return deepcopy(
            list(models)
        )

    def create_assistant(
        self,
        *,
        model_provider: str,
        model_name: str,
        **assistant_options: Any,
    ) -> AssistantSession | None:
        """
        Create and register one engine-owned assistant session.

        Returns:
            A public AssistantSession handle, or None when the configured
            provider or model could not create an assistant.
        """

        assistant_item = self._toolkit_ops.create_assistant(
            model_provider=model_provider,
            model_name=model_name,
            **assistant_options,
        )

        if assistant_item is None:
            return None

        session_id = str(
            assistant_item.assistant_id
        )

        with self._assistant_sessions_lock:
            self._assistant_sessions[session_id] = (
                assistant_item
            )

        return AssistantSession(
            engine=self,
            session_id=session_id,
        )

    def replace_assistant(
        self,
        *,
        session_id: str,
        model_provider: str,
        model_name: str,
        **assistant_options: Any,
    ) -> AssistantSession | None:
        """
        Replace an assistant implementation while preserving its session.

        Existing context, conversation history and token usage are copied using
        the same behaviour as the previous Tk-owned model-switch workflow.
        """

        try:
            current_assistant = self._get_assistant_item(
                session_id
            )

        except KeyError:
            logger.error(
                "Cannot replace unknown assistant session %s.",
                session_id,
            )
            return None

        new_assistant = self._toolkit_ops.create_assistant(
            model_provider=model_provider,
            model_name=model_name,
            **assistant_options,
        )

        if new_assistant is None:
            return None

        if not self._toolkit_ops.copy_assistant_context_and_chat(
            source_assistant=current_assistant,
            target_assistant=new_assistant,
        ):
            logger.error(
                "Cannot copy assistant conversation state."
            )
            return None

        # replace only the private implementation; callers retain the same
        # public AssistantSession and stable session ID
        with self._assistant_sessions_lock:
            if session_id not in self._assistant_sessions:
                logger.error(
                    "Assistant session %s was closed while changing models.",
                    session_id,
                )
                return None

            self._assistant_sessions[session_id] = (
                new_assistant
            )

        return AssistantSession(
            engine=self,
            session_id=session_id,
        )

    def close_assistant(
        self,
        session_id: str,
    ) -> bool:
        """
        Remove one assistant implementation from the engine registry.
        """

        if not session_id:
            return False

        with self._assistant_sessions_lock:
            assistant_item = self._assistant_sessions.pop(
                session_id,
                None,
            )

        return assistant_item is not None

    def parse_assistant_response(
        self,
        assistant_response: str,
    ) -> dict | None:
        """
        Parse a structured assistant response through processing.
        """

        if not isinstance(assistant_response, str):
            return None

        parsed_response = (
            self._toolkit_ops.parse_assistant_response(
                assistant_response
            )
        )

        return deepcopy(
            parsed_response
        )

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

    def is_resolve_connected(self) -> bool:
        """
        Return whether processing currently has an active Resolve connection.
        """

        return bool(
            self._toolkit_ops.is_resolve_connected()
        )

    def get_resolve_state(self) -> dict:
        """
        Return detached Resolve state needed for presentation decisions.
        """

        return deepcopy(
            self._toolkit_ops.get_resolve_state()
        )

    def get_resolve_marker_color_palette(self) -> dict:
        """
        Return the fixed Resolve marker-color palette.
        """

        return deepcopy(
            self._toolkit_ops.get_resolve_marker_color_palette()
        )

    def set_resolve_polling_suspended(
        self,
        suspended: bool,
    ) -> bool:
        """
        Suspend or resume Resolve polling around a busy Resolve operation.
        """

        return bool(
            self._toolkit_ops.set_resolve_polling_suspended(
                suspended=suspended,
            )
        )

    def ensure_resolve_connection(
        self,
        *,
        timeout_seconds: float = 5.0,
        poll_interval: float = 0.05,
    ) -> dict:
        """
        Enable Resolve when needed and wait briefly for a connection.

        The engine returns plain copied result data. Callers do not receive
        access to the Resolve API wrapper or its polling state.
        """

        return deepcopy(
            self._toolkit_ops.ensure_resolve_connection(
                timeout_seconds=timeout_seconds,
                poll_interval=poll_interval,
            )
        )

    def render_resolve_timeline(
        self,
        *,
        target_dir: str,
        render_options: dict,
    ) -> dict:
        """
        Render the current Resolve timeline.
        """

        return deepcopy(
            self._toolkit_ops.render_resolve_timeline(
                target_dir=target_dir,
                render_options=render_options,
            )
        )

    def render_resolve_job(
        self,
        *,
        job_id: str,
        render_data: dict | None = None,
    ) -> dict:
        """
        Render one existing job from the Resolve render queue.
        """

        return deepcopy(
            self._toolkit_ops.render_resolve_job(
                job_id=job_id,
                render_data=render_data,
            )
        )

    def start_resolve_render_and_monitor(
        self,
        *,
        monitor_callback: Any = None,
        **render_options: Any,
    ) -> tuple[Any, list[str]] | None:
        """
        Start the legacy Resolve render monitor.

        The Monitor instance remains an accepted version 1 in-process bridge.
        It must be replaced by job events before the version 2 process
        boundary is introduced.

        Returns:
            A monitor and detached render-path list, or None when processing
            could not start a valid render monitor.
        """

        result = (
            self._toolkit_ops.start_resolve_render_and_monitor(
                monitor_callback=monitor_callback,
                **render_options,
            )
        )

        if result is None or result is False:
            return None

        if not isinstance(result, tuple) or len(result) != 2:
            logger.error(
                "Resolve render monitor returned an invalid result."
            )
            return None

        monitor, render_file_paths = result

        if monitor is None:
            logger.error(
                "Resolve render monitor did not return a monitor instance."
            )
            return None

        if not isinstance(render_file_paths, (list, tuple)):
            logger.error(
                "Resolve render monitor did not return a render-path list."
            )
            return None

        detached_render_file_paths = [
            str(file_path)
            for file_path in render_file_paths
            if file_path
        ]

        if not detached_render_file_paths:
            logger.error(
                "Resolve render monitor did not return any render paths."
            )
            return None

        return monitor, detached_render_file_paths

    def import_resolve_media(
        self,
        file_path: str,
    ) -> bool:
        """
        Import one file into the current Resolve project.
        """

        return bool(
            self._toolkit_ops.import_resolve_media(
                file_path=file_path,
            )
        )

    def add_resolve_timeline_markers(
        self,
        *,
        timeline_name: str,
        markers: dict,
        delete_existing: bool = False,
    ) -> bool:
        """
        Add detached marker data to one Resolve timeline.

        Existing timeline markers are preserved unless ``delete_existing`` is
        explicitly enabled.
        """

        return bool(
            self._toolkit_ops.add_resolve_timeline_markers(
                timeline_name=timeline_name,
                markers=deepcopy(markers),
                delete_existing=delete_existing,
            )
        )

    def resolve_seconds_to_timecode(
        self,
        seconds: float,
    ) -> Any:
        """
        Convert seconds to a timecode on the current Resolve timeline.

        The existing Timecode value remains an accepted version 1 in-process
        result.
        """

        return (
            self._toolkit_ops.calculate_sec_to_resolve_timecode(
                seconds
            )
        )

    def get_resolve_playhead_seconds(self) -> float | None:
        """
        Return the current Resolve playhead position in seconds.
        """

        return (
            self._toolkit_ops.calculate_resolve_timecode_to_sec()
        )

    def move_resolve_playhead(
        self,
        *,
        seconds: float,
        fps: float | None = None,
    ) -> Any:
        """
        Move the Resolve playhead to a position expressed in seconds.
        """

        if fps is None:
            return self._toolkit_ops.go_to_time(
                seconds=seconds,
            )

        return self._toolkit_ops.go_to_time(
            seconds=seconds,
            fps=fps,
        )

    def disable_resolve_connection(self) -> bool:
        """
        Disable Resolve integration for the current runtime.
        """

        self._toolkit_ops.resolve_disable()

        return not self.is_resolve_connected()

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

    def get_whisper_available_languages(self) -> list[str]:
        """
        Return the Whisper languages available to ingest forms.

        The returned list is detached from processing state so callers may
        sort or otherwise modify it without affecting ToolkitOps.
        """

        languages = (
            self._toolkit_ops.get_whisper_available_languages()
        )

        if not languages:
            return []

        return deepcopy(list(languages))

    def get_processing_devices(self) -> list[str]:
        """
        Return processing-device names suitable for UI selectors.

        ``auto`` is a presentation choice and is intentionally not added here.
        Each caller can decide whether an automatic-device option is useful.
        """

        devices = getattr(
            self._toolkit_ops,
            "queue_devices",
            None,
        )

        if not devices:
            return []

        return deepcopy(list(devices))

    def start_speaker_detection(
        self,
        *,
        queue_item_name: str,
        transcription_file_path: str,
        time_intervals: list,
        device_name: str,
    ) -> str | bool:
        """
        Add speaker detection for one transcription to the processing queue.

        Returns:
            The queue ID created by processing, or False when the operation
            could not be queued.
        """

        result = (
            self._toolkit_ops.add_speaker_detection_to_queue(
                queue_item_name=queue_item_name,
                transcription_file_path=transcription_file_path,
                time_intervals=time_intervals,
                device_name=device_name,
            )
        )

        return deepcopy(result)

    def start_group_questions(
        self,
        *,
        queue_item_name: str,
        transcription_file_path: str,
        group_name: str,
    ) -> str | bool:
        """
        Add automatic question grouping to the processing queue.

        Returns:
            The queue ID created by processing, or False when the operation
            could not be queued.
        """

        result = (
            self._toolkit_ops.add_group_questions_to_queue(
                queue_item_name=queue_item_name,
                transcription_file_path=transcription_file_path,
                group_name=group_name,
            )
        )

        return deepcopy(result)

    def publish_transcription_changed(
        self,
        transcription_id: str,
    ) -> bool:
        """
        Publish an event after one saved transcription changes.

        The event contains a transcription identifier rather than a Tk
        callback name. Each interface decides how to refresh its own views.
        """

        if not transcription_id:
            return False

        self._toolkit_ops.events.emit(
            create_transcription_changed_event(
                transcription_id=transcription_id,
            )
        )

        return True

    def publish_project_changed(self) -> bool:
        """
        Publish an event after the active project changes.
        """

        self._toolkit_ops.events.emit(
            create_project_changed_event()
        )

        return True

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
        search_file_paths: str | list[str] | tuple[str, ...],
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

    def _refresh_search_job_status(
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

        job = self.get_job(text_job_id)

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
    ) -> dict[str, Any] | None:
        """
        Return detached information about an advanced search session.

        Waiting text-index jobs are checked before the public status is copied.

        Args:
            search_id: ID returned by ``create_search``.

        Returns:
            Search information, or ``None`` when the session does not exist.
        """

        session = self._get_search_session(search_id)

        if session is None:
            return None

        self._refresh_search_job_status(session)

        return self._copy_search_info(session)

    def _find_text_index_job(
        self,
        search_file_paths: list[str],
    ) -> tuple[str, dict[str, Any]] | None:
        """Return the newest queue item for the same text search paths."""

        matching_job = None

        for job_id, job in self.list_jobs().items():
            if job.get("item_type") != "search":
                continue

            if job.get("search_file_paths") != search_file_paths:
                continue

            # queue dictionaries retain insertion order, so keeping the last
            # match selects the newest known job for this corpus
            matching_job = job_id, job

        return matching_job

    def _prepare_search_worker(
        self,
        search_id: str,
        queue_item_name: str | None,
    ) -> None:
        """Prepare text and video search processors outside the UI thread."""

        session = self._get_search_session(search_id)

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

                    # failed and canceled jobs do not prevent a new indexing attempt
                    elif existing_status in _SEARCH_FAILED_JOB_STATUSES:
                        existing_job = None

                    # an unknown historical status should not be treated as a reusable job
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
    ) -> dict[str, Any] | None:
        """
        Begin preparing an advanced search in an engine-owned worker.

        Calling this method again while preparation is active is harmless.

        Args:
            search_id:
                ID returned by ``create_search``.
            queue_item_name:
                Optional name for a persistent text-index queue item.

        Returns:
            Current detached search information, or ``None`` if it is unknown.
        """

        session = self._get_search_session(search_id)

        if session is None:
            return None

        preparation_thread = session.get("preparation_thread")

        if (
            preparation_thread is not None
            and preparation_thread.is_alive()
        ):
            return self._copy_search_info(session)

        if self._get_search_status(session) in {"ready", "failed"}:
            return self._copy_search_info(session)

        preparation_thread = Thread(
            target=self._prepare_search_worker,
            kwargs={
                "search_id": search_id,
                "queue_item_name": queue_item_name,
            },
            name="search-preparation-{}".format(search_id[:8]),
            daemon=True,
        )

        session["preparation_thread"] = preparation_thread
        preparation_thread.start()

        return self._copy_search_info(session)

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

        session = self._get_search_session(search_id)

        if session is None:
            return None

        text_search_item = session["text_search_item"]

        if not text_search_item.search_file_paths_count:
            return None

        text_search_item.load_model(
            model_name=model_name,
        )

        return getattr(text_search_item, "model_name", model_name)

    def search_text(
        self,
        search_id: str,
        query: str,
        max_results: int = 5,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Run a text search and return detached result data.

        Args:
            search_id: ID returned by ``create_search``.
            query: Search query entered by the user.
            max_results: Default maximum number of results.

        Returns:
            A copied result list and the effective maximum result count.
        """

        session = self._get_search_session(search_id)

        if session is None:
            return [], max_results

        self._refresh_search_job_status(session)

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
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Run a video search and return detached result data.

        VideoSearch returns both the matching frames and the effective result
        count after parsing any result limit included in the query.
        """

        session = self._get_search_session(search_id)

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

        session = self._get_search_session(search_id)

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
