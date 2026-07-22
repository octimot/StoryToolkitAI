from copy import deepcopy

from storytoolkitai.core.engine import StoryToolkitEngine


class FakeToolkitOps:
    """
    Minimal ToolkitOps replacement for engine-facing UI operation tests.
    """

    def __init__(self):
        self.queue_devices = ["cpu", "CUDA"]
        self.languages = ["English", "German"]
        self.calls = []

    def get_whisper_available_languages(self):
        return self.languages

    def add_speaker_detection_to_queue(
        self,
        queue_item_name,
        transcription_file_path,
        time_intervals,
        device_name,
    ):
        self.calls.append(
            (
                "speaker_detection",
                {
                    "queue_item_name": queue_item_name,
                    "transcription_file_path": transcription_file_path,
                    "time_intervals": deepcopy(time_intervals),
                    "device_name": device_name,
                },
            )
        )

        return "speaker-job-1"

    def add_group_questions_to_queue(
        self,
        queue_item_name,
        transcription_file_path,
        group_name,
    ):
        self.calls.append(
            (
                "group_questions",
                {
                    "queue_item_name": queue_item_name,
                    "transcription_file_path": transcription_file_path,
                    "group_name": group_name,
                },
            )
        )

        return "questions-job-1"

    def notify_observers(self, action):
        self.calls.append(
            (
                "notify",
                action,
            )
        )

        return True


def test_get_whisper_available_languages_returns_detached_list():
    toolkit_ops = FakeToolkitOps()
    engine = StoryToolkitEngine(toolkit_ops)

    languages = engine.get_whisper_available_languages()
    languages.append("French")

    assert languages == ["English", "German", "French"]
    assert toolkit_ops.languages == ["English", "German"]


def test_get_processing_devices_returns_detached_list():
    toolkit_ops = FakeToolkitOps()
    engine = StoryToolkitEngine(toolkit_ops)

    devices = engine.get_processing_devices()
    devices.append("mps")

    assert devices == ["cpu", "CUDA", "mps"]
    assert toolkit_ops.queue_devices == ["cpu", "CUDA"]


def test_start_speaker_detection_forwards_named_arguments():
    toolkit_ops = FakeToolkitOps()
    engine = StoryToolkitEngine(toolkit_ops)

    time_intervals = [
        {
            "start": 1.0,
            "end": 2.0,
        }
    ]

    result = engine.start_speaker_detection(
        queue_item_name="Detect speakers",
        transcription_file_path="/tmp/transcription.transcription.json",
        time_intervals=time_intervals,
        device_name="cpu",
    )

    assert result == "speaker-job-1"
    assert toolkit_ops.calls == [
        (
            "speaker_detection",
            {
                "queue_item_name": "Detect speakers",
                "transcription_file_path": (
                    "/tmp/transcription.transcription.json"
                ),
                "time_intervals": [
                    {
                        "start": 1.0,
                        "end": 2.0,
                    }
                ],
                "device_name": "cpu",
            },
        )
    ]


def test_start_group_questions_forwards_named_arguments():
    toolkit_ops = FakeToolkitOps()
    engine = StoryToolkitEngine(toolkit_ops)

    result = engine.start_group_questions(
        queue_item_name="Find questions",
        transcription_file_path="/tmp/transcription.transcription.json",
        group_name="Questions",
    )

    assert result == "questions-job-1"
    assert toolkit_ops.calls == [
        (
            "group_questions",
            {
                "queue_item_name": "Find questions",
                "transcription_file_path": (
                    "/tmp/transcription.transcription.json"
                ),
                "group_name": "Questions",
            },
        )
    ]


def test_publish_transcription_changed_uses_compatibility_event():
    toolkit_ops = FakeToolkitOps()
    engine = StoryToolkitEngine(toolkit_ops)

    assert engine.publish_transcription_changed("abc123") is True
    assert toolkit_ops.calls == [
        (
            "notify",
            "update_transcription_abc123",
        )
    ]


def test_publish_transcription_changed_rejects_empty_id():
    toolkit_ops = FakeToolkitOps()
    engine = StoryToolkitEngine(toolkit_ops)

    assert engine.publish_transcription_changed("") is False
    assert toolkit_ops.calls == []


def test_publish_project_changed_uses_compatibility_event():
    toolkit_ops = FakeToolkitOps()
    engine = StoryToolkitEngine(toolkit_ops)

    assert engine.publish_project_changed() is True
    assert toolkit_ops.calls == [
        (
            "notify",
            "project_changed",
        )
    ]
