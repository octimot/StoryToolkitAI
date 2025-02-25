from pydantic import BaseModel, Field, model_validator
from typing import List, Optional
import re

# validation using Pydantic model
from pydantic import BaseModel
from typing import Optional, Union

# INFO: Most of the code in this file is for type validation purposes.
# The actual ingest process is handled in the toolkit_ops package until further notice.

class FramesPerSecond(float):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, info):
        # If the input is an empty string, return None
        if isinstance(v, str) and v.strip() == "":
            return None
        try:
            return cls(float(v))
        except (ValueError, TypeError):
            raise ValueError("Timeline FPS must be a valid number, please enter a numeric value.")

class TimecodeStr(str):
    """
    This is not to be mistaken with the Timecode class from the timecode module.
    We only use this model for type validation purposes.
    """
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, info):
        # If the input is an empty string, return None
        if isinstance(v, str) and v.strip() == "":
            return None
        # If the input is not a string, raise an error
        if not isinstance(v, str):
            raise ValueError("Invalid timecode value, please enter a valid timecode string.")
        # the timecode string should be in the format "HH:MM:SS:FF"
        if not re.match(r"^\d{2}:\d{2}:\d{2}:\d{2}$", v):
            raise ValueError("Invalid timecode value, please enter a valid timecode string.")
        return v

class MetadataSettings(BaseModel):
    timeline_name: Optional[str] = None
    project_name: Optional[str] = None
    timeline_start_tc: Optional[TimecodeStr] = None
    timeline_fps: Optional[FramesPerSecond] = None

Number = Union[int, float]

class TimeInterval:
    def __init__(self, start: Number, end: Number):
        if start >= end:
            raise ValueError("The first value must be smaller than the second value in a time interval.")
        self.start = start
        self.end = end

    def __iter__(self):
        # This allows instances to be unpacked into lists or tuples if needed
        return iter((self.start, self.end))

    def __repr__(self):
        return f"[{self.start}, {self.end}]"

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, info):
        # Ensure input is a list or tuple
        if not isinstance(v, (list, tuple)):
            raise TypeError("TimeInterval must be provided as a list or tuple.")
        if len(v) != 2:
            raise ValueError("TimeInterval must contain exactly two elements.")
        try:
            start = float(v[0])
            end = float(v[1])
        except (ValueError, TypeError):
            raise ValueError("Both values in TimeInterval must be numeric.")
        if start >= end:
            raise ValueError(f"The first value ({start}) must be smaller than the second value ({end}) in a time interval.")
        return cls(start, end)

class TranscriptionSettings(BaseModel):
    transcription_task: str
    model_name: str
    device: str
    pre_detect_speech: bool
    transcription_speaker_detection: bool
    transcription_speaker_detection_threshold: float = Field(default=0.3, gt=0, le=1)
    max_words_per_segment: Optional[int] = None
    max_chars_per_segment: Optional[int] = None
    split_on_punctuation_marks: Optional[bool] = None
    prevent_short_gaps: Optional[bool] = None
    time_intervals: Optional[List[TimeInterval]] = None
    excluded_time_intervals: Optional[List[TimeInterval]] = None
    keep_whisper_debug_info: Optional[bool] = None
    group_questions: Optional[bool] = None
    whisper_options: dict

class VideoIndexingOptions(BaseModel):
    prefer_sharp: bool = True
    skip_color_blocks: bool = True
    skip_similar_neighbors: bool = True
    patch_divider: float = Field(1.9, ge=1, le=4)

class VideoDetectionOptions(BaseModel):
    content_analysis_every: int = 40 # frames
    jump_every_frames: int = 20 # frames

class VideoIndexingSettings(BaseModel):
    video_file_path: Optional[str] = None
    indexing_options: VideoIndexingOptions
    detection_options: VideoDetectionOptions

class IngestSettings(BaseModel):
    metadata: MetadataSettings
    transcription_settings: Optional[TranscriptionSettings] = None
    video_indexing_settings: Optional[VideoIndexingSettings] = None
    source_file_paths: List[str]
    queue_id: Optional[str] = None
    retranscribe: bool = False
    ingest_delete_render_info_file: Optional[bool] = False
    transcription_file_path: Optional[str] = None

    @model_validator(mode='after')
    def transcription_or_indexing(self):

        # we need to make sure that we have either transcription_settings or video_indexing_settings
        if not self.transcription_settings and not self.video_indexing_settings:
            raise ValueError("Both transcription and video indexing settings are missing.")

        return self