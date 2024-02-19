import os
import cv2
from moviepy.editor import VideoFileClip, AudioFileClip
import subprocess
import re

from storytoolkitai.core.toolkit_ops.videoanalysis import ClipIndex
from storytoolkitai.core.logger import logger


class MediaItem:
    """
    This handles all the audio/video items that are used in the toolkit.
    """

    def __init__(self, path: str):

        # the path of the media item
        self._path = path

        # the name of the media item is the basename of the path
        self._name = os.path.basename(path)

        self._type = self.get_media_type()

        self._duration = None
        self._metadata = None

    @property
    def path(self):
        """
        Returns the path of the media item.
        """
        return self._path

    @property
    def name(self):
        """
        Returns the name of the media item.
        """
        return self._name

    @property
    def type(self):
        """
        Returns the type of the media item.
        """
        return self._type

    @property
    def duration(self):
        """
        Returns the duration of the media item.
        """
        return self._duration

    @property
    def metadata(self):
        """
        Returns the metadata of the media item.
        """
        return self._metadata

    def get_duration(self):
        """
        Returns the duration of the media item.
        """

        try:
            if self._type == 'video':
                clip = VideoFileClip(self.path)
                self._duration = clip.duration
                return clip.duration

            elif self._type == 'audio':
                clip = AudioFileClip(self.path)
                self._duration = clip.duration
                return clip.duration
        except:
            logger.error('The duration of the media item could not be determined.', exc_info=True)
            return None

    def get_metadata(self):
        """
        Returns the metadata of the media item.
        """
        pass

    def get_transcription(self):
        """
        Returns the transcription of the media item.
        """
        pass

    @staticmethod
    def has_audio(file_path):
        """
        Checks if the file has audio and returns True if it does, otherwise returns False.
        """

        try:
            audio_clip = AudioFileClip(file_path)
            audio_present = audio_clip.duration > 0
        except Exception:
            audio_present = False

        return audio_present

    @staticmethod
    def has_video(file_path):
        """
        Checks if the file has video and returns True if it does, otherwise returns False.
        """

        try:
            clip = VideoFileClip(file_path)
            video_present = clip.reader.nframes > 0
        except Exception:
            video_present = False

        return video_present

    def get_media_type(self):
        """
        Returns the media type of the file depending on the file path.
        """

        if self.path is None:
            logger.error('The file path is not specified.')
            return

        if (self.path.endswith('.mp4') or self.path.endswith('.mov') or self.path.endswith('.avi')
                or self.path.endswith('.mkv') or self.path.endswith('.webm') or self.path.endswith('.wmv')
                or self.path.endswith('.flv') or self.path.endswith('.vob') or self.path.endswith('.ogv')):
            self._type = 'video'
            return 'video'

        elif (self.path.endswith('.mp3') or self.path.endswith('.wav') or self.path.endswith('.ogg')
                or self.path.endswith('.wma') or self.path.endswith('.aac') or self.path.endswith('.flac')):
            self._type = 'audio'
            return 'audio'


class AudioItem(MediaItem):
    """
    This handles all the audio items that are used in the toolkit.
    """

    def __init__(self, path: str):
        super().__init__(path=path)

        self._type = 'audio'


class VideoItem(MediaItem, ClipIndex):
    """
    This handles all the video items that are used in the toolkit.
    """

    def __init__(self, path: str):

        MediaItem.__init__(self, path=path)
        ClipIndex.__init__(self)

        self._type = 'video'

        self.source_path = self.path

        self._timecode_data = None

    def get_timecode_data(self):
        """
        Returns the timecode data of the video item.
        """
        return self._timecode_data

    def extract_timecode_data(self):
        """
        Extracts the timecode data from the file
        """

        # look into the file's metadata and extract the timecode data

    def get_video_frame(self, frame_index: int):
        """
        Returns the video frame at the given frame index.
        """

        cap = cv2.VideoCapture(self.source_path)

        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index - 1)
        ret, frame = cap.read()

        # Return the frame if it was read correctly, otherwise return None
        return frame if ret else None

    ClipIndex = ClipIndex


class MediaUtils:

    @staticmethod
    def get_audio_sample_rate(file):
        """
        This uses ffmpeg to extract the audio sample rate from a video file.
        """

        # Run ffmpeg to extract audio stream information
        cmd = ["ffmpeg", "-i", file, "-hide_banner"]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Use regex to find the sample rate
        match = re.search(r"(\d+) Hz", result.stderr)
        if match:
            return float(match.group(1))
        else:
            return None

    @staticmethod
    def get_fps_and_timecode_from_file(file_path):
        """
        This function extracts specific stream information such as frame rate and timecode
        from a video or audio file using ffmpeg, parsing the stderr output.
        """

        # try to extract the frame rate and timecode from the file using ffmpeg, but only process the first frame
        cmd = ["ffmpeg", "-i", file_path, "-vframes", "1", "-f", "null", "-"]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Initialize an empty dict to hold our extracted information
        stream_info = {}

        # Use regular expressions to find frame rate and timecode
        frame_rate_match = re.search(r", (\d+(?:\.\d+)?) fps,", result.stderr)
        timecode_match = re.search(r"timecode\s*:\s*([0-9:;.]+)", result.stderr)

        if frame_rate_match:
            stream_info['frame_rate'] = frame_rate_match.group(1)

        if timecode_match:
            stream_info['timecode'] = timecode_match.group(1)

        return stream_info
