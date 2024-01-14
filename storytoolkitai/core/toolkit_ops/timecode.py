from timecode import Timecode
from storytoolkitai.core.logger import logger


def sec_to_tc(seconds: float, *, fps: float, use_frames=True, add_frame=False) -> Timecode:
    """
    Converts seconds to timecode.

    :param seconds: seconds
    :param fps: frames per second
    :param use_frames: if True,
                       we don't do direct conversion from seconds, but convert to frames first
                       to avoid rounding errors
    :param add_frame: if True, we add 1 frame to the timecode to offset from timestamp to frame representation

    :return: timecode object (IMPORTANT: frame 1 is 00:00:00:00, frame 2 is 00:00:00:01, etc.)
    """

    if not isinstance(seconds, float):
        raise TypeError('seconds must be a float, not {}'.format(type(seconds)))

    if not isinstance(fps, float) and not isinstance(fps, int):
        raise TypeError('fps must be float or int, not {}'.format(type(fps)))

    if fps <= 0:
        raise ValueError('fps must be positive, not fps={}'.format(fps))

    if use_frames:

        # it seems that the rounding of the seconds at non-round frame rates causes issues,
        # so instead of passing seconds to initialize the timecode,
        # we'll calculate the frames here and pass them instead
        frames = seconds * fps

        # the frames then need to be rounded since you can't have a fraction of a frame
        frames = int(round(frames))

        # init the timecode object based on the passed seconds
        return Timecode(fps, frames=frames if frames > 0 else None) + (1 if add_frame else 0)

    # if we're not supposed to use frames,
    # we'll just pass the seconds directly to the timecode object

    logger.warning('sec_to_tc direct to seconds not fully tested yet!')

    return Timecode(round(fps, 3), start_seconds=seconds + 1 / fps + 1e-8)


def tc_to_sec(timecode: str, *, fps: float) -> float:
    """
    Converts timecode to seconds
    :param timecode: timestamp
    :param fps: frames per second
    :return: seconds
    """

    if not isinstance(timecode, str):
        raise TypeError('Timecode must be a string, not {}'.format(type(timecode)))

    if not isinstance(fps, float) and not isinstance(fps, int):
        raise TypeError('fps must be a positive float or int, not {}'.format(type(fps)))

    if fps <= 0:
        raise ValueError('fps must be positive, not fps={}'.format(fps))

    # round to 3 decimal places
    fps = round(fps, 3)

    # we need to subtract the timecode of the first frame by removing the timecode of the first frame
    return round(Timecode(fps, timecode).float - Timecode(fps, '00:00:00:00').float, 5)
