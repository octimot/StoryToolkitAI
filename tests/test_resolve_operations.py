from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


_MISSING = object()

# NOTE
# This amount of test setup is also a strong signal that
# the Resolve methods should eventually move into a lightweight
# Resolve-specific module.


class _Placeholder:
    """stand-in for imports not used by Resolve tests"""

    pass


class _TorchDevice:
    """minimal replacement for torch.device"""

    def __init__(self, device_type: str) -> None:
        self.type = device_type


class _TorchCuda:
    """minimal replacement for torch.cuda"""

    @staticmethod
    def is_available() -> bool:
        return False


class _Timecode:
    """minimal replacement for timecode.Timecode"""

    def __init__(self, *args, **kwargs) -> None:
        pass


def _not_used(*args, **kwargs):
    """stand-in callable for code not used by Resolve tests"""

    return None


def _create_module(
    name: str,
    **attributes: Any,
) -> ModuleType:
    """create a module containing the supplied attributes"""

    module = ModuleType(name)

    for attribute_name, value in attributes.items():
        setattr(
            module,
            attribute_name,
            value,
        )

    return module


def _load_toolkit_ops_for_resolve_tests():
    """load ToolkitOps without importing processing dependencies"""

    saved_modules = {}
    saved_parent_attributes = {}

    def register_module(
        name: str,
        module: ModuleType,
    ) -> None:
        # remember the previous module so it can be restored
        if name not in saved_modules:
            saved_modules[name] = sys.modules.get(
                name,
                _MISSING,
            )

        sys.modules[name] = module

        parent_name, separator, child_name = name.rpartition('.')

        if not separator:
            return

        # expose the child module on its parent package
        parent_module = importlib.import_module(
            parent_name
        )
        parent_key = (
            parent_name,
            child_name,
        )

        if parent_key not in saved_parent_attributes:
            saved_parent_attributes[parent_key] = getattr(
                parent_module,
                child_name,
                _MISSING,
            )

        setattr(
            parent_module,
            child_name,
            module,
        )

    # import the lightweight package parents before adding child stubs
    importlib.import_module(
        'storytoolkitai'
    )
    importlib.import_module(
        'storytoolkitai.core'
    )
    importlib.import_module(
        'storytoolkitai.core.toolkit_ops'
    )
    importlib.import_module(
        'storytoolkitai.integrations'
    )

    private_module_name = (
        'storytoolkitai.core.toolkit_ops.'
        '_resolve_test_toolkit_ops'
    )

    try:
        # stub direct third-party imports from toolkit_ops
        torch_stub = _create_module(
            'torch',
            device=_TorchDevice,
            Tensor=_Placeholder,
            cuda=_TorchCuda(),
        )

        numpy_stub = _create_module(
            'numpy',
            ndarray=_Placeholder,
        )

        whisper_tokenizer_stub = _create_module(
            'whisper.tokenizer',
            LANGUAGES={},
        )

        whisper_audio_stub = _create_module(
            'whisper.audio',
            SAMPLE_RATE=16_000,
            HOP_LENGTH=160,
            N_FRAMES=3_000,
            N_SAMPLES=480_000,
            FRAMES_PER_SECOND=100,
        )

        whisper_stub = _create_module(
            'whisper',
            tokenizer=whisper_tokenizer_stub,
            audio=whisper_audio_stub,
        )
        whisper_stub.__path__ = []

        transformers_stub = _create_module(
            'transformers',
            pipeline=_not_used,
        )

        timecode_stub = _create_module(
            'timecode',
            Timecode=_Timecode,
        )

        register_module(
            'torch',
            torch_stub,
        )
        register_module(
            'numpy',
            numpy_stub,
        )
        register_module(
            'whisper',
            whisper_stub,
        )
        register_module(
            'whisper.tokenizer',
            whisper_tokenizer_stub,
        )
        register_module(
            'whisper.audio',
            whisper_audio_stub,
        )
        register_module(
            'transformers',
            transformers_stub,
        )
        register_module(
            'librosa',
            _create_module('librosa'),
        )
        register_module(
            'soundfile',
            _create_module('soundfile'),
        )
        register_module(
            'tqdm',
            _create_module(
                'tqdm',
                tqdm=_not_used,
            ),
        )
        register_module(
            'yaml',
            _create_module(
                'yaml',
                safe_load=_not_used,
                safe_dump=_not_used,
                load=_not_used,
                dump=_not_used,
            ),
        )
        register_module(
            'timecode',
            timecode_stub,
        )

        # stub custom Whisper before toolkit_ops imports it
        register_module(
            'storytoolkitai.integrations.mots_whisper',
            _create_module(
                'storytoolkitai.integrations.mots_whisper'
            ),
        )

        # stub the Resolve integration class used only during construction
        register_module(
            'storytoolkitai.integrations.mots_resolve',
            _create_module(
                'storytoolkitai.integrations.mots_resolve',
                MotsResolve=_Placeholder,
            ),
        )

        # stub local modules whose dependency trees are irrelevant here
        register_module(
            'storytoolkitai.core.toolkit_ops.projects',
            _create_module(
                'storytoolkitai.core.toolkit_ops.projects',
                Project=_Placeholder,
                ProjectUtils=_Placeholder,
                get_projects_from_path=_not_used,
            ),
        )

        register_module(
            'storytoolkitai.core.toolkit_ops.transcription',
            _create_module(
                'storytoolkitai.core.toolkit_ops.transcription',
                Transcription=_Placeholder,
                TranscriptionSegment=_Placeholder,
                TranscriptionUtils=_Placeholder,
            ),
        )

        register_module(
            'storytoolkitai.core.toolkit_ops.story',
            _create_module(
                'storytoolkitai.core.toolkit_ops.story',
                Story=_Placeholder,
                StoryLine=_Placeholder,
                StoryUtils=_Placeholder,
            ),
        )

        register_module(
            'storytoolkitai.core.toolkit_ops.document',
            _create_module(
                'storytoolkitai.core.toolkit_ops.document',
                Document=_Placeholder,
            ),
        )

        register_module(
            'storytoolkitai.core.toolkit_ops.processing_queue',
            _create_module(
                'storytoolkitai.core.toolkit_ops.processing_queue',
                ProcessingQueue=_Placeholder,
            ),
        )

        register_module(
            'storytoolkitai.core.toolkit_ops.search',
            _create_module(
                'storytoolkitai.core.toolkit_ops.search',
                SearchConfig=_Placeholder,
                ToolkitSearch=_Placeholder,
                SearchItem=_Placeholder,
                TextSearch=_Placeholder,
                VideoSearch=_Placeholder,
                cv2=_create_module('cv2'),
            ),
        )

        register_module(
            'storytoolkitai.core.toolkit_ops.assistant',
            _create_module(
                'storytoolkitai.core.toolkit_ops.assistant',
                ToolkitAssistant=_Placeholder,
                AssistantUtils=_Placeholder,
                DEFAULT_SYSTEM_MESSAGE='',
            ),
        )

        register_module(
            'storytoolkitai.core.toolkit_ops.media',
            _create_module(
                'storytoolkitai.core.toolkit_ops.media',
                MediaUtils=_Placeholder,
                MediaItem=_Placeholder,
                VideoFileClip=_Placeholder,
                AudioFileClip=_Placeholder,
            ),
        )

        register_module(
            'storytoolkitai.core.toolkit_ops.speaker_diarization',
            _create_module(
                'storytoolkitai.core.toolkit_ops.speaker_diarization',
                detect_speaker_changes=_not_used,
            ),
        )

        register_module(
            'storytoolkitai.core.toolkit_ops.timecode',
            _create_module(
                'storytoolkitai.core.toolkit_ops.timecode',
                sec_to_tc=_not_used,
                tc_to_sec=_not_used,
            ),
        )

        register_module(
            'storytoolkitai.core.toolkit_ops.ingest',
            _create_module(
                'storytoolkitai.core.toolkit_ops.ingest',
                IngestSettings=_Placeholder,
                TranscriptionSettings=_Placeholder,
                VideoIndexingSettings=_Placeholder,
            ),
        )

        register_module(
            'storytoolkitai.core.toolkit_ops.monitor',
            _create_module(
                'storytoolkitai.core.toolkit_ops.monitor',
                Monitor=_Placeholder,
            ),
        )

        register_module(
            'storytoolkitai.core.toolkit_ops.videoanalysis',
            _create_module(
                'storytoolkitai.core.toolkit_ops.videoanalysis',
                ClipIndex=_Placeholder,
            ),
        )

        toolkit_ops_path = (
            Path(__file__).resolve().parents[1]
            / 'storytoolkitai'
            / 'core'
            / 'toolkit_ops'
            / 'toolkit_ops.py'
        )

        module_spec = importlib.util.spec_from_file_location(
            private_module_name,
            toolkit_ops_path,
        )

        if (
            module_spec is None
            or module_spec.loader is None
        ):
            raise ImportError(
                'Unable to load toolkit_ops.py'
            )

        toolkit_ops_module = (
            importlib.util.module_from_spec(
                module_spec
            )
        )

        # register the private module while it is being executed
        sys.modules[
            private_module_name
        ] = toolkit_ops_module

        module_spec.loader.exec_module(
            toolkit_ops_module
        )

        return toolkit_ops_module.ToolkitOps

    finally:
        # remove the privately loaded toolkit ops module
        sys.modules.pop(
            private_module_name,
            None,
        )

        # restore parent-package attributes
        for (
            parent_name,
            child_name,
        ), previous_value in reversed(
            list(saved_parent_attributes.items())
        ):
            parent_module = sys.modules.get(
                parent_name
            )

            if parent_module is None:
                continue

            if previous_value is _MISSING:
                try:
                    delattr(
                        parent_module,
                        child_name,
                    )
                except AttributeError:
                    pass
            else:
                setattr(
                    parent_module,
                    child_name,
                    previous_value,
                )

        # restore modules that existed before this test import
        for name, previous_module in reversed(
            list(saved_modules.items())
        ):
            if previous_module is _MISSING:
                sys.modules.pop(
                    name,
                    None,
                )
            else:
                sys.modules[name] = previous_module


ToolkitOps = _load_toolkit_ops_for_resolve_tests()

class FakeResolveApi:
    def __init__(self, resolve_data):
        self.resolve_data = resolve_data
        self.copy_call = None
        self.render_call = None
        self.add_markers_call = None

    def get_resolve_data(self):
        return self.resolve_data

    def copy_markers(
        self,
        source,
        destination,
        source_name,
        destination_name,
        delete_destination_markers,
    ):
        self.copy_call = (
            source,
            destination,
            source_name,
            destination_name,
            delete_destination_markers,
        )

        return True

    def add_timeline_markers(
        self,
        timeline_name,
        markers,
        delete_timeline_markers,
    ):
        """
        Record a timeline-marker request using the real Resolve signature.
        """

        self.add_markers_call = (
            timeline_name,
            markers,
            delete_timeline_markers,
        )

        return True

    def render_markers(
        self,
        marker_color,
        target_dir,
        add_timestamp,
        stills,
        render,
        render_preset,
        *,
        starts_with=None,
    ):
        self.render_call = (
            marker_color,
            target_dir,
            add_timestamp,
            stills,
            render,
            render_preset,
            starts_with,
        )

        return None


def create_toolkit_ops(resolve_data):
    toolkit_ops = ToolkitOps.__new__(ToolkitOps)
    toolkit_ops.resolve_api = FakeResolveApi(resolve_data)

    return toolkit_ops


def test_resolve_marker_colors_are_unique_and_sorted() -> None:
    toolkit_ops = create_toolkit_ops(
        {
            'currentTimeline': {
                'name': 'Timeline 1',
                'markers': {
                    '1': {
                        'color': 'Red',
                    },
                    '2': {
                        'color': 'Blue',
                    },
                    '3': {
                        'color': 'Red',
                    },
                },
            },
            'binClips': [],
        }
    )

    result = toolkit_ops.get_resolve_marker_colors()

    assert result == {
        'ok': True,
        'data': {
            'marker_colors': [
                'Blue',
                'Red',
            ],
        },
    }


def test_resolve_marker_colors_require_timeline() -> None:
    toolkit_ops = create_toolkit_ops(
        {
            'currentTimeline': None,
            'binClips': [],
        }
    )

    result = toolkit_ops.get_resolve_marker_colors()

    assert result['ok'] is False
    assert result['code'] == 'timeline_unavailable'


def test_copy_resolve_markers_uses_current_timeline() -> None:
    toolkit_ops = create_toolkit_ops(
        {
            'currentTimeline': {
                'name': 'Timeline 1',
                'markers': {},
            },
            'binClips': [
                {
                    'name': 'Timeline 1',
                },
            ],
        }
    )

    result = toolkit_ops.copy_resolve_markers(
        source='timeline',
    )

    assert result['ok'] is True
    assert toolkit_ops.resolve_api.copy_call == (
        'timeline',
        'clip',
        'Timeline 1',
        'Timeline 1',
        True,
    )

def test_add_resolve_timeline_markers_preserves_existing_by_default() -> None:
    """
    The UI marker workflow must not erase existing Resolve markers by default.
    """

    toolkit_ops = create_toolkit_ops(
        {
            "currentTimeline": {
                "name": "Timeline 1",
                "markers": {},
            },
            "binClips": [],
        }
    )

    markers = {
        24: {
            "color": "Blue",
            "name": "Test marker",
            "note": "",
            "duration": 12,
            "customData": "",
        }
    }

    result = toolkit_ops.add_resolve_timeline_markers(
        timeline_name="Timeline 1",
        markers=markers,
    )

    assert result is True
    assert toolkit_ops.resolve_api.add_markers_call == (
        "Timeline 1",
        markers,
        False,
    )


def test_add_resolve_timeline_markers_can_delete_existing() -> None:
    """
    Callers may explicitly replace all existing Resolve timeline markers.
    """

    toolkit_ops = create_toolkit_ops(
        {
            "currentTimeline": {
                "name": "Timeline 1",
                "markers": {},
            },
            "binClips": [],
        }
    )

    markers = {
        24: {
            "color": "Blue",
            "name": "Replacement marker",
            "note": "",
            "duration": 12,
            "customData": "",
        }
    }

    result = toolkit_ops.add_resolve_timeline_markers(
        timeline_name="Timeline 1",
        markers=markers,
        delete_existing=True,
    )

    assert result is True
    assert toolkit_ops.resolve_api.add_markers_call == (
        "Timeline 1",
        markers,
        True,
    )


def test_render_resolve_markers_passes_selected_options() -> None:
    toolkit_ops = create_toolkit_ops(
        {
            'currentTimeline': {
                'name': 'Timeline 1',
                'markers': {
                    '1': {
                        'color': 'Blue',
                    },
                },
            },
            'binClips': [],
        }
    )

    result = toolkit_ops.render_resolve_markers(
        marker_color='Blue',
        target_dir='/tmp/render',
        starts_with='Interview',
        render_stills=True,
    )

    assert result['ok'] is True
    assert toolkit_ops.resolve_api.render_call == (
        'Blue',
        '/tmp/render',
        False,
        True,
        True,
        'Still_TIFF',
        'Interview',
    )


def test_render_resolve_markers_rejects_unknown_color() -> None:
    toolkit_ops = create_toolkit_ops(
        {
            'currentTimeline': {
                'name': 'Timeline 1',
                'markers': {
                    '1': {
                        'color': 'Blue',
                    },
                },
            },
            'binClips': [],
        }
    )

    result = toolkit_ops.render_resolve_markers(
        marker_color='Red',
        target_dir='/tmp/render',
    )

    assert result['ok'] is False
    assert result['code'] == 'marker_color_invalid'
