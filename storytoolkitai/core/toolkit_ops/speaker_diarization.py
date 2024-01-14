from pyannote.audio.pipelines.speaker_verification import PretrainedSpeakerEmbedding
from pyannote.audio import Audio
from pyannote.core import Segment
import torch
import copy
import os
import librosa
import numpy as np

from scipy.spatial.distance import cosine

from storytoolkitai.core.logger import logger
from .media import VideoFileClip, AudioFileClip, MediaUtils


def find_closest_speaker(embedding, speaker_embeddings, threshold=0.3):
    """
    Find the closest speaker to the current segment.
    :param: embedding: the embedding of the current segment
    :param: speaker_embeddings: a dictionary of speaker embeddings {"speaker_id": speaker_embedding, ...}
    :param: threshold: the threshold for the cosine similarity
    """

    for speaker_id, speaker_embedding in speaker_embeddings.items():
        similarity = 1 - cosine(embedding.flatten(), speaker_embedding.flatten())
        if similarity > threshold:
            return speaker_id
    return None


def speaker_changed(segment1_embedding, segment2_embedding, threshold=0.3):
    """
    Compare the embeddings of two segments to see if the speaker has changed.
    :param: segment1_embedding: the embedding of the previous segment
    :param: segment2_embedding: the embedding of the current segment
    :param: threshold: the threshold for the cosine similarity
            - anything below this is considered a speaker change (default: 0.3)

    """

    # if one of the embeddings is None, we can't compare them
    if segment1_embedding is None or segment2_embedding is None:
        return False

    # compare the embeddings
    similarity = 1 - cosine(segment1_embedding.flatten(), segment2_embedding.flatten())

    return similarity < threshold


def detect_speaker_changes(
        segments, audio_file_path, threshold=0.3, device_name=None, time_intervals=None, speaker_id_offset=0,
        step_by_step=False):
    """
    Detect speaker changes in a list of segments and adds the speaker_id to the segments.

    :param: segments: a list of segments (for e.g. [{"start": 0.0, "end": 1.0, "text": "Hello world"}, ...])
    :param: audio_file_path: the path to the source audio file
    :param: threshold: the threshold for the cosine similarity
            - anything below this is considered a speaker change (default: 0.3)
    :param: device_name: the device to use for speaker verification: 'cuda' or 'cpu' (default: None)
            - if None, the device will be automatically selected based on the availability of CUDA
    :param: time_intervals: a list of time intervals to use for speaker verification (format: [[start, end], ...])
            - if None, the entire audio file will be used
    :param: speaker_id_offset: the offset to use for the speaker IDs (default: 0)
    :param: step_by_step: if True, the function will yield the segments and speaker embeddings after each iteration
    """

    if segments is None or not isinstance(segments, list) or len(segments) == 0:
        logger.error("Cannot detect speaker changes - No segments provided.")
        return segments, None

    # if the threshold is None, let's use the default
    if threshold is None:
        threshold = 0.3

    # if the threshold is not a float raise an error
    if not isinstance(threshold, float):
        raise ValueError("threshold must be a float")

    # if speaker_id_offset is not an integer raise an error
    if not isinstance(speaker_id_offset, int):
        raise ValueError("speaker_id_offset must be an integer")

    # use a deep copy of the segments so that we don't modify the original due to mutability
    resulting_segments = copy.deepcopy(segments)

    if not device_name:
        torch_device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    else:
        torch_device = torch.device(device_name if device_name in ['cuda', 'cpu'] else 'cpu')

    # go to cpu if cuda is not available
    if torch_device == 'cuda' and not torch.cuda.is_available():
        logger.warning('CUDA is not available for Speaker Changes Detection, switching to CPU')
        torch_device = torch.device('cpu')

    logger.debug('Using device "{}" for Speaker Changes Detection'.format(torch_device))

    # load the speaker verification model
    model = PretrainedSpeakerEmbedding("speechbrain/spkrec-ecapa-voxceleb", device=torch.device(torch_device))
    audio = Audio(sample_rate=16000, mono="downmix")

    # try to see if we can handle the audio file natively
    # for that, we just perform a test crop of a second
    try:
        audio.crop(audio_file_path, Segment(0, 1))
        audio_file = audio_file_path
    except:

        logger.debug('Falling back to Librosa for {} due to audio format.'
                     .format(os.path.basename(audio_file_path)))

        # load audio file as array using librosa
        # this should work for most audio formats
        try:
            audio_array, sr = librosa.load(audio_file_path, sr=16_000)

        # if the above fails, try this:
        except:

            logger.debug('Librosa failed. Falling back to moviepy for {} due to audio format.'
                         .format(os.path.basename(audio_file_path)))

            # we need to determine the raw sample rate of the audio first
            raw_sr = MediaUtils.get_audio_sample_rate(audio_file_path)

            if raw_sr is None:
                logger.warning('Falling back to 48000Hz for {} due to audio format, '
                               'but this might provide inaccurate results. '
                               'Please use a recommended file format to avoid falling back to this default.'
                               .format(os.path.basename(audio_file_path)))

                raw_sr = 48000

            sr = 16000

            # if this is a video file, extract the audio from it
            try:
                video = VideoFileClip(audio_file_path)
                raw_audio_array = video.audio.to_soundarray(fps=raw_sr)
            except:
                # last chance, if this is audio-only, try to load it with AudioFileClip

                audio = AudioFileClip(audio_file_path)
                raw_audio_array = audio.to_soundarray(fps=raw_sr)

            audio_array = librosa.core.resample(np.asfortranarray(raw_audio_array.T), orig_sr=raw_sr, target_sr=sr)
            audio_array = librosa.core.to_mono(audio_array)

            # change to float32
            audio_array = np.asarray(audio_array, dtype=np.float32)

        # Convert numpy array to a PyTorch tensor and reshape it to (channel, time)
        audio_tensor = torch.tensor(audio_array).unsqueeze(0)  # adds a channel dimension

        audio_file = {"waveform": audio_tensor, "sample_rate": sr}

    # we're storing the embeddings for each speaker in a dictionary
    # so that we can compare them once a speaker change is detected
    # this helps us attempt to identify the speaker
    speaker_embeddings = {}

    # we always compare the current segment to the previous segment
    # so let's use this to store the previous segment's embedding
    previous_segment_embedding = None

    current_speaker_id = 1

    for idx, segment in enumerate(resulting_segments):

        # convert the start and end times to floats or None in a safe way
        start = segment.get('start', None)
        start = float(start) if start is not None else None

        end = segment.get('end', None)
        end = float(end) if end is not None else None

        if time_intervals is not None and isinstance(time_intervals, list) and len(time_intervals) > 0:
            # are we in the time interval?
            if not any(start >= interval[0] and end <= interval[1]
                       for interval in time_intervals):
                continue

        if not isinstance(start, float) or not isinstance(end, float):
            logger.debug("Cannot detect speaker changes on segment - start or end time are missing or not floats: {}"
                         .format(segment))
            continue

        # skip segments that are 0 seconds long
        if start >= end:
            logger.debug("Cannot detect speaker changes on segment - end time should be greater than start time: {}"
                         .format(segment))
            continue

        # crop the audio to the segment
        segment_speaker = Segment(start, end)
        segment_audio, sample_rate = audio.crop(audio_file, segment_speaker)

        # get the embedding for the segment
        segment_embedding = model(segment_audio[None])

        # has the speaker changed compared to the previous segment?
        if speaker_changed(
                segment1_embedding=previous_segment_embedding,
                segment2_embedding=segment_embedding,
                threshold=threshold
        ):

            # if so, let's find the closest speaker
            closest_speaker_id = find_closest_speaker(segment_embedding, speaker_embeddings, threshold=threshold)

            # if we haven't seen this speaker before, let's assign them a new ID
            if closest_speaker_id is None:
                speaker_id_to_assign = current_speaker_id
                current_speaker_id += 1

            else:
                speaker_id_to_assign = closest_speaker_id

        else:
            # if the speaker hasn't changed, let's keep the same ID
            speaker_id_to_assign = current_speaker_id

        # add the speaker ID to the segment
        resulting_segments[idx]['speaker_id'] = speaker_id_to_assign + speaker_id_offset

        # update the previous segment embedding
        previous_segment_embedding = segment_embedding

        # let's add the current speaker to the dictionary
        # or update the speaker's embedding if we've seen them before
        #  - we're more likely to have a better match for this speaker in the future
        #    since we're assuming the recording conditions are sequential
        #    and the speaker might "sound" more similar between closer segments
        speaker_embeddings[current_speaker_id] = segment_embedding

        if step_by_step:
            yield resulting_segments, speaker_embeddings

    return resulting_segments, speaker_embeddings
