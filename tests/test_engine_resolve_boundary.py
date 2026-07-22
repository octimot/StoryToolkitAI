from copy import deepcopy

from storytoolkitai.core.engine import StoryToolkitEngine


class FakeToolkitOps:
    """
    Minimal Resolve-compatible processing object for engine tests.
    """

    def __init__(self):
        self.resolve_state = {
            "enabled": True,
            "connected": True,
            "current_project": "Test Project",
            "current_timeline": {
                "name": "Timeline 1",
                "markers": {
                    24: {
                        "name": "Marker",
                        "color": "Blue",
                        "duration": 12,
                    }
                },
            },
            "current_timeline_fps": 24,
            "current_tc": "01:00:00:00",
            "current_start_tc": "01:00:00:00",
            "polling_suspended": False,
        }

        self.palette = {
            "Blue": "#0000ff",
        }

        self.calls = []
        self.connected = True

    def is_resolve_connected(self):
        return self.connected

    def get_resolve_state(self):
        return self.resolve_state

    def get_resolve_marker_color_palette(self):
        return self.palette

    def set_resolve_polling_suspended(self, suspended):
        self.resolve_state["polling_suspended"] = suspended
        self.calls.append(
            (
                "suspend_polling",
                suspended,
            )
        )
        return suspended

    def start_resolve_render_and_monitor(
        self,
        monitor_callback=None,
        **render_options,
    ):
        monitor = object()

        self.calls.append(
            (
                "render_and_monitor",
                {
                    "monitor_callback": monitor_callback,
                    "render_options": deepcopy(render_options),
                },
            )
        )

        return monitor, ["/tmp/render.wav"]

    def import_resolve_media(self, file_path):
        self.calls.append(
            (
                "import_media",
                file_path,
            )
        )
        return True

    def add_resolve_timeline_markers(
        self,
        timeline_name,
        markers,
        delete_existing=False,
    ):
        self.calls.append(
            (
                "add_markers",
                {
                    "timeline_name": timeline_name,
                    "markers": deepcopy(markers),
                    "delete_existing": delete_existing,
                },
            )
        )

        return True

    def calculate_sec_to_resolve_timecode(self, seconds):
        return "timecode:{}".format(seconds)

    def calculate_resolve_timecode_to_sec(self):
        return 42.5

    def go_to_time(self, seconds, fps=None):
        self.calls.append(
            (
                "go_to_time",
                {
                    "seconds": seconds,
                    "fps": fps,
                },
            )
        )
        return True

    def resolve_disable(self):
        self.connected = False


def test_resolve_state_is_detached():
    toolkit_ops = FakeToolkitOps()
    engine = StoryToolkitEngine(toolkit_ops)

    state = engine.get_resolve_state()
    state["current_timeline"]["markers"][24]["name"] = "Changed"

    assert (
        toolkit_ops.resolve_state[
            "current_timeline"
        ]["markers"][24]["name"]
        == "Marker"
    )


def test_resolve_marker_palette_is_detached():
    toolkit_ops = FakeToolkitOps()
    engine = StoryToolkitEngine(toolkit_ops)

    palette = engine.get_resolve_marker_color_palette()
    palette["Blue"] = "changed"

    assert toolkit_ops.palette["Blue"] == "#0000ff"


def test_resolve_polling_state_is_delegated():
    toolkit_ops = FakeToolkitOps()
    engine = StoryToolkitEngine(toolkit_ops)

    assert engine.set_resolve_polling_suspended(True) is True
    assert toolkit_ops.calls == [
        (
            "suspend_polling",
            True,
        )
    ]


def test_resolve_render_monitor_keeps_monitor_private_to_runtime():
    toolkit_ops = FakeToolkitOps()
    engine = StoryToolkitEngine(toolkit_ops)

    result = engine.start_resolve_render_and_monitor(
        target_dir="/tmp",
        file_name="timeline",
    )

    assert result is not None

    monitor, paths = result

    assert monitor is not None
    assert paths == ["/tmp/render.wav"]

def test_resolve_render_monitor_returns_none_when_processing_fails():
    class FailingToolkitOps(FakeToolkitOps):
        def start_resolve_render_and_monitor(
            self,
            monitor_callback=None,
            **render_options,
        ):
            return False

    toolkit_ops = FailingToolkitOps()
    engine = StoryToolkitEngine(toolkit_ops)

    result = engine.start_resolve_render_and_monitor(
        target_dir="/tmp",
        file_name="timeline",
    )

    assert result is None


def test_import_resolve_media_is_delegated():
    toolkit_ops = FakeToolkitOps()
    engine = StoryToolkitEngine(toolkit_ops)

    assert engine.import_resolve_media("/tmp/subtitles.srt") is True
    assert toolkit_ops.calls == [
        (
            "import_media",
            "/tmp/subtitles.srt",
        )
    ]


def test_add_resolve_markers_copies_input():
    toolkit_ops = FakeToolkitOps()
    engine = StoryToolkitEngine(toolkit_ops)

    markers = {
        10: {
            "name": "Test",
            "color": "Blue",
        }
    }

    assert engine.add_resolve_timeline_markers(
        timeline_name="Timeline 1",
        markers=markers,
    ) is True

    markers[10]["name"] = "Changed"

    assert toolkit_ops.calls == [
        (
            "add_markers",
            {
                "timeline_name": "Timeline 1",
                "markers": {
                    10: {
                        "name": "Test",
                        "color": "Blue",
                    }
                },
                "delete_existing": False,
            },
        )
    ]

def test_add_resolve_markers_can_replace_existing_markers():
    toolkit_ops = FakeToolkitOps()
    engine = StoryToolkitEngine(toolkit_ops)

    markers = {
        10: {
            "name": "Test",
            "color": "Blue",
        }
    }

    assert engine.add_resolve_timeline_markers(
        timeline_name="Timeline 1",
        markers=markers,
        delete_existing=True,
    ) is True

    assert toolkit_ops.calls == [
        (
            "add_markers",
            {
                "timeline_name": "Timeline 1",
                "markers": {
                    10: {
                        "name": "Test",
                        "color": "Blue",
                    }
                },
                "delete_existing": True,
            },
        )
    ]


def test_resolve_timecode_operations_are_delegated():
    toolkit_ops = FakeToolkitOps()
    engine = StoryToolkitEngine(toolkit_ops)

    assert (
        engine.resolve_seconds_to_timecode(12.5)
        == "timecode:12.5"
    )

    assert engine.get_resolve_playhead_seconds() == 42.5

    assert engine.move_resolve_playhead(
        seconds=12.5,
        fps=24,
    ) is True

    assert toolkit_ops.calls == [
        (
            "go_to_time",
            {
                "seconds": 12.5,
                "fps": 24,
            },
        )
    ]


def test_disable_resolve_connection_reports_disconnected_state():
    toolkit_ops = FakeToolkitOps()
    engine = StoryToolkitEngine(toolkit_ops)

    assert engine.disable_resolve_connection() is True
    assert toolkit_ops.connected is False
