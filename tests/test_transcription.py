import json

from storytoolkitai.core.toolkit_ops.transcription import Transcription

# The transcription object already supports loading segments, 
# preserving unrecognized data, serializing itself, and saving immediately. 
# The transcription is considered valid when it has a segment list 
# containing valid segment data or a video index path.

def make_transcription_file(path) -> dict:
    transcription_data = {
        "name": "Example Interview",
        "task": "transcribe",
        "whisper_model": "small",
        "language": "en",
        "whisper_language": "en",
        "segments": [
            {
                "id": 0,
                "start": 0.0,
                "end": 1.25,
                "text": " Hello.",
            },
            {
                "id": 1,
                "start": 1.25,
                "end": 2.5,
                "text": " World.",
            },
        ],
        "transcript_groups": {},
        "timeline_fps": 24,
        "timeline_start_tc": "01:00:00:00",
        "incomplete": False,
        "fixture_extension": {
            "must_be_preserved": True,
        },
    }

    path.write_text(
        json.dumps(transcription_data),
        encoding="utf-8",
    )

    return transcription_data


def test_transcription_loads_existing_format(tmp_path) -> None:
    transcription_path = (
        tmp_path / "interview.transcription.json"
    )

    original_data = make_transcription_file(
        transcription_path
    )

    transcription = Transcription(
        str(transcription_path),
        force_reload=True,
    )

    assert transcription.exists is True
    assert transcription.is_transcription_file is True
    assert transcription.has_segments is True
    assert transcription.name == "Example Interview"
    assert len(transcription.segments) == 2
    assert transcription.segments[0].start == 0.0
    assert transcription.segments[1].end == 2.5
    assert transcription.text == " Hello. World."

    serialized = transcription.to_dict()

    assert serialized["segments"] == original_data["segments"]
    assert serialized["fixture_extension"] == {
        "must_be_preserved": True
    }


def test_transcription_save_preserves_unknown_data(tmp_path) -> None:
    transcription_path = (
        tmp_path / "interview.transcription.json"
    )

    make_transcription_file(transcription_path)

    transcription = Transcription(
        str(transcription_path),
        force_reload=True,
    )

    transcription.set("language", "de")

    assert transcription.save_soon(sec=0)

    saved_data = json.loads(
        transcription_path.read_text(encoding="utf-8")
    )

    assert saved_data["language"] == "de"
    assert saved_data["fixture_extension"] == {
        "must_be_preserved": True
    }

    # Existing behaviour adds this during save.
    assert "last_modified" in saved_data
