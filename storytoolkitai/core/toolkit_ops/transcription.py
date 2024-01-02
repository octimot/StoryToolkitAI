import copy
import os
import codecs
import json
import hashlib
import random
import string
import shutil
import time
from datetime import datetime
import re
from threading import Timer

from timecode import Timecode

from storytoolkitai.core.logger import logger


class Transcription:

    _instances = {}

    def __new__(cls, *args, **kwargs):
        """
        This checks if the current transcription file path isn't already loaded in an instance
        and returns that instance if it is.
        """

        # we use the transcription file path as the id for the instance
        transcription_path_id = cls.get_transcription_path_id(
            transcription_file_path=kwargs.get('transcription_file_path', None) or args[0]
        )

        # if the transcription file path is already loaded in an instance, we return that instance
        if transcription_path_id in cls._instances:

            return cls._instances[transcription_path_id]

        # otherwise we create a new instance
        instance = super().__new__(cls)

        # and we store it in the instances dict
        cls._instances[transcription_path_id] = instance

        # then we return the instance
        return instance

    def __init__(self, transcription_file_path, force_reload=False):

        # prevent initializing the instance more than once if it was found in the instances dict
        # but only if we're not supposed to force a reload
        if hasattr(self, '_initialized') and self._initialized and not force_reload:
            return

        self._transcription_path_id = None
        self.__transcription_file_path = None

        # this is used to check if the file has changed
        # it will be updated only when the file is loaded and saved
        self._last_hash = None

        self._name = None

        self._segments = []
        self._segment_ids = {}

        self._text = None

        # the transcript groups are used to group segments together by time intervals
        self._transcript_groups = {}

        # these are the paths to other files that are associated with the transcription file
        # we call them auxiliary files
        self._srt_file_path = None
        self._txt_file_path = None

        # this is the path to the audio file that is associated with the transcription file
        self._audio_file_path = None

        # the path to the video index path
        self._video_index_path = None

        # timecode data variables
        self._timeline_fps = None
        self._timeline_start_tc = None

        # project info variables
        self._timeline_name = None
        self._project_name = None

        self._language = None
        self._whisper_language = None
        self._whisper_model = None

        # this is usually given by the queue
        self.transcription_id = None

        # if we detect word level timings in the transcription file, we set this to true
        self._word_precision = False

        # this is set to false if the file wasn't found
        self._exists = False

        # for a file to qualify as a transcription file,
        # it needs to have segments or a segments attribute
        self._is_transcription_file = False

        # this is set to true if the transcription file has segments (len > 0)
        self._has_segments = False

        # here we store all the other data that is not part of the known attributes
        # but was found in the transcription file
        self._other_data = {}

        # where we store the transcription data from the file
        # this will be empty once the data is loaded into attributes
        self._data = None

        # use the passed transcription file path
        self.load_from_file(file_path=transcription_file_path)

        # we use this to keep track if we updated, deleted, added, or changed anything
        self._dirty = False

        # this is used to keep track if the transcription is complete or not
        self._incomplete = None

        # this is used to keep track of the last time the transcription was saved
        self._last_save_time = None

        # with this we can set a timer to save the transcription after a certain amount of time
        # this way, we don't create another timer if one is already running and the save_soon method is called again
        self._save_timer = None

        # if we're saving very often, we can throttle the save timer
        # the throttle is a ratio used to multiply the save timer interval
        # the more often we save, the longer the interval between saves
        # but then this is reset to 1 when we're not saving often
        self._save_timer_throttle = 1

        # add this to know that we already initialized this instance
        self._initialized = True

    def __del__(self):
        """
        Make sure we remove this from the instances dict when it's deleted
        """

        # if we're deleting the instance that is stored in the instances dict
        # we remove it from the dict, so we don't have a reference to a deleted object
        if self.__class__._instances[self.transcription_path_id] == self:
            del self.__class__._instances[self.transcription_path_id]

    @property
    def language(self):
        return self._language

    @property
    def transcription_file_path(self):
        return self.__transcription_file_path

    @property
    def has_segments(self):
        return self._has_segments

    @property
    def is_transcription_file(self):
        return self._is_transcription_file

    @property
    def transcription_path_id(self):
        return self._transcription_path_id

    @property
    def segments(self):
        return self._segments

    @property
    def segment_ids(self):
        return self._segment_ids

    @property
    def name(self):
        return self._name

    @property
    def text(self):
        return self._text

    def __str__(self):
        return self.text

    def __dict__(self):
        return self.to_dict()

    @property
    def word_precision(self):
        return self._word_precision

    @property
    def transcript_groups(self):
        return self._transcript_groups

    @property
    def srt_file_path(self):
        return self._srt_file_path

    @property
    def txt_file_path(self):
        return self._txt_file_path

    @property
    def audio_file_path(self):

        # if the path is not absolute, make it absolute using the transcription file path
        if self._audio_file_path is not None and not os.path.isabs(self._audio_file_path):
            return os.path.join(os.path.dirname(self.transcription_file_path), self._audio_file_path)

        return self._audio_file_path

    @property
    def video_index_path(self):

        # if the path is not absolute, make it absolute using the transcription file path
        if self._video_index_path is not None and not os.path.isabs(self._video_index_path):
            return os.path.join(os.path.dirname(self.transcription_file_path), self._video_index_path)

        return self._video_index_path

    @property
    def exists(self):
        return self._exists

    @exists.setter
    def exists(self, value):
        self._exists = value

    @property
    def timeline_fps(self):
        return self._timeline_fps

    @property
    def timeline_start_tc(self):
        return self._timeline_start_tc

    @property
    def timeline_name(self):
        return self._timeline_name

    @property
    def project_name(self):
        return self._project_name

    @property
    def other_data(self):
        return self._other_data

    @property
    def incomplete(self):
        return self._incomplete

    @property
    def last_save_time(self):
        return self._last_save_time

    @property
    def last_hash(self):
        return self._last_hash

    @property
    def dirty(self):
        return self._dirty

    def is_dirty(self):
        return self._dirty

    def set_dirty(self, value=True):
        self._dirty = value

    def set(self, key: str or dict, value=None):
        """
        We use this to set some of the attributes of the transcription.
        If the attribute was changed, we set the dirty flag to true.
        """

        # everything that is "known"
        allowed_attributes = copy.deepcopy(self.__known_attributes)

        # but without the segments attribute
        allowed_attributes.remove('segments')

        # if we're setting a dictionary of attributes
        if isinstance(key, dict):

            # we iterate through the dictionary
            for k, v in key.items():

                # and set each attribute
                self.set(k, v)

            return True

        # if the key is a string and is allowed, do this:
        if key in allowed_attributes:

            # if the attribute is different than the current value,
            if getattr(self, '_' + key) != value:

                # set the attribute
                setattr(self, '_' + key, value)

                # set the dirty flag
                self.set_dirty()

            return True

        # throw an error if the key is not valid
        else:
            raise AttributeError('Cannot set the attribute {} for Transcription, '
                                 'only {} can be set.'.format(key, allowed_attributes))

    def reload_from_file(self, save_first=False):
        """
        This reloads the transcription file from disk and sets the attributes
        :param save_first: if True, we save the transcription first and then reload it
        """

        # if there's a save timer running, we save the transcription first
        if save_first and self._save_timer is not None:

            # cancel timer
            self._save_timer.cancel()

            # save transcription now
            self._save()

        # load the transcription file from disk
        self.load_from_file(file_path=self.__transcription_file_path)

    def load_from_file(self, file_path):
        """
        This changes the transcription_file_path
        and loads the transcription file from disk and sets the attributes
        """
        self.__transcription_file_path = file_path

        # when we set the transcription file_path, we also check if the file exists
        # but only if the file_path is a string
        self._exists = os.path.isfile(self.__transcription_file_path) if isinstance(file_path, str) else False

        # load the json found in the file into attributes
        self._load_json_into_attributes()

    __known_attributes = [
        'name', 'task', 'whisper_model', 'segments', 'transcript_groups',
        'srt_file_path', 'audio_file_path', 'txt_file_path',
        'language',
        'whisper_language',
        'timeline_fps', 'timeline_start_tc',
        'timeline_name', 'project_name',
        'transcription_id', 'incomplete',
        'video_index_path'
    ]

    def copy_transcription(self, source_transcription, include_groups=False, include_segments=False):
        """
        This copies the known attributes from the source transcription into this transcription,
        Some attributes are not copied, like srt_file_path, txt_file_path, incomplete, transcription_id etc.
        While others are modified to keep them unique, like transcription_id, etc.
        It does not copy segments.
        """

        # first, the known attributes
        # read all the attributes from the source transcription
        for attribute in self.__known_attributes:

            # if the attribute is srt_file_path or txt_file_path
            # skip it
            if attribute in ['srt_file_path', 'txt_file_path', 'incomplete']:
                continue

            # if this is the transcription id, generate a new one
            if attribute == 'transcription_id':
                setattr(self, '_'+attribute, self.generate_id())
                continue

            # get the attribute value from the source transcription
            attribute_value = getattr(source_transcription, '_' + attribute)

            # set the attribute value for this transcription
            setattr(self, '_' + attribute, attribute_value)

        # if we're supposed to copy the transcript groups
        if include_groups:
            # get the transcript groups from the source transcription
            self._transcript_groups = getattr(source_transcription, '_transcript_groups')

        # if we're supposed to copy the segments
        if include_segments:
            # copy both the segments and the has_segments attribute
            self._segments = getattr(source_transcription, '_segments')
            self._has_segments = getattr(source_transcription, '_has_segments')

        # set the dirty flag
        self.set_dirty()

    @staticmethod
    def get_transcription_path_id(transcription_file_path):
        return hashlib.md5(transcription_file_path.encode('utf-8')).hexdigest()

    def generate_id(self):
        """
        This uses a scrambled version of the transcription_file_path and the current time to generate a unique id
        """

        # use the transcription_file_path and the current time to generate a more unique id
        if self.__transcription_file_path is None:
            scrambled_path = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

        # otherwise scramble the transcription_file_path
        else:
            transcription_file_path = self.__transcription_file_path
            char_list = list(transcription_file_path)
            random.shuffle(char_list)
            scrambled_path = ''.join(char_list)

        return hashlib.md5((scrambled_path + str(time.time())).encode('utf-8')).hexdigest()

    def _load_json_into_attributes(self):

        # calculate the new path id
        self._transcription_path_id = self.get_transcription_path_id(self.__transcription_file_path) \
            if self.__transcription_file_path else None

        if self._exists:
            # get the contents of the transcription file
            try:

                logger.debug("Loading transcription file {}".format(self.__transcription_file_path))

                with codecs.open(self.__transcription_file_path, 'r', 'utf-8-sig') as json_file:
                    self._data = json.load(json_file)

                    # let's make a deep copy of the data
                    # so that we can manipulate it without changing the original data
                    self._data = copy.deepcopy(self._data)

            # in case we get JSONDecodeError, we assume that the file is not a valid JSON file
            except json.decoder.JSONDecodeError:
                self._data = {}

            # if we have a file that is not a valid JSON file, we assume that it is not a transcription file
            except:
                logger.error("Transcription file {} is invalid".format(self.__transcription_file_path, exc_info=True))
                self._data = {}

        else:
            self._data = {}

        # set the attributes
        for attribute in self.__known_attributes:

            # if the known attribute is in the json, set the attribute
            if attribute in self._data:

                # process the value for the attribute
                attribute_value = self._process_attribute(attribute, copy.deepcopy(self._data[attribute]))

                # if there's nothing left to set, continue
                if attribute_value is None:
                    continue

                # set the attribute, but also process it
                setattr(self, '_'+attribute, attribute_value)

                # and remove it from the data
                del self._data[attribute]

            # if the known attribute is not in the json,
            # set the attribute to None so we can still access it
            else:
                setattr(self, '_'+attribute, None)

        # other data is everything else
        self._other_data = {k: v for k, v in self._data.items() if k not in self.__known_attributes}

        # check if the transcription file contains word timings
        if isinstance(self._segments, list) and len(self._segments) > 0 and self._segments[0].words:
            self._word_precision = True
        else:
            self._word_precision = False

        # calculate the hash of the transcription data

        # calculate the hash of the transcription data
        self._get_transcription_hash()

        # check if this is a valid transcription
        self._is_valid_transcription_data()

    def to_dict(self):
        """
        This returns the transcription data as a dict.
        It doesn't include all the attributes, only the known ones and the other data.
        """

        # create a copy of the data
        transcription_dict = dict()

        # add the known attributes to the data
        for attribute in self.__known_attributes:

            # if the attribute is set, add it to the dict
            if hasattr(self, '_'+attribute) and getattr(self, '_'+attribute) is not None:

                # if the attribute is segments, we need to convert the segments to dicts too
                if attribute == 'segments':
                    transcription_dict[attribute] = [segment.to_dict() for segment in getattr(self, '_'+attribute)]

                # otherwise, we just add the attribute
                else:
                    transcription_dict[attribute] = getattr(self, '_'+attribute)

        # merge the other data with the transcription data
        transcription_dict.update(self._other_data)

        return transcription_dict

    def _is_valid_transcription_data(self):
        """
        This checks if the transcription is valid by looking at the segments in the data
        """

        # for transcription data to be valid
        # it needs to have segments which are a list
        # and either the list needs to be empty or the first item in the list needs to be a valid segment
        # or
        # it should have a video video_index_path
        if (isinstance(self._segments, list) \
                and (len(self._segments) == 0
                     or (isinstance(self._segments[0], TranscriptionSegment) and self._segments[0].is_valid)
                     or TranscriptionSegment(self._segments[0]).is_valid))\
                or self._video_index_path:
            self._is_transcription_file = True
        else:
            self._is_transcription_file = False

    def _process_attribute(self, attribute_name, value):
        """
        This processes the attributes of the transcription file
        """

        if attribute_name == 'name':

            # if there is no name, we use the file name without the extension
            if not value or value == '':
                value = os.path.splitext(os.path.basename(self.__transcription_file_path))[0]

        # for other file paths, do this
        elif attribute_name == 'srt_file_path' \
                or attribute_name == 'audio_file_path' \
                or attribute_name == 'txt_file_path':

            # use the absolute path to check if the file exists
            abs_value = value

            # if not we're dealing with an absolute path
            if not os.path.isabs(abs_value):

                # assume that the srt is in the same directory as the transcription
                abs_value = os.path.join(os.path.dirname(self.__transcription_file_path), value)

            # if the file doesn't exist, set the value to None
            if not os.path.isfile(abs_value):
                logger.warning("File {} referenced in {} does not exist.".format(value, self.__transcription_file_path))
            #    value = None

        # the segments
        elif attribute_name == 'segments':

            # set the segments
            self._set_segments(segments=value)

            # return None since we already set the attributes in the method
            return None

        return value

    def _set_segments(self, segments: list = None):
        """
        This method sets the _segments attribute (if segments is not None),
        checks if all the segments are TranscriptionSegments
        then re-calculates the _has_segments and _segment_ids attributes
        """

        # if segments were passed, set them
        if segments is not None:
            self._segments = segments

        # if we have segments, make sure that they're all objects
        for index, segment in enumerate(self._segments):

            # if the segment is not an object, make it an object
            if not isinstance(segment, TranscriptionSegment):

                # turn this into a segment object
                self._segments[index] = TranscriptionSegment(segment, parent_transcription=self)

            # take the text from all the segments and put it in the transcription ._text attribute
            self._text = (self._text + self._segments[index].text) \
                if isinstance(self._text, str) else self._segments[index].text

        # sort all the segments by their start time
        self._segments = sorted(self._segments, key=lambda x: x.start)

        # re-calculate the self._has_segments attribute
        self._has_segments = len(self._segments) > 0

        # re-generate the self._segment_ids attribute
        self._segment_ids = {i: segment.id for i, segment in enumerate(self._segments)}

        # re-calculate if it's valid
        self._is_valid_transcription_data()

    def get_segments(self):
        """
        This returns the segments in the transcription
        """

        # if we have segments, return them
        return self._segments if self._has_segments else self._segments

    def get_segment(self, segment_index: int = None, segment_id=None):
        """
        This returns a specific segment object by its id or index in the segments list
        :param segment_id: the id of the segment
        :param segment_index: the index of the segment in the segments list
        """

        if segment_id is None and segment_index is None:
            logger.error('Cannot get segment id "{}", index "{}".'.format(segment_id, segment_index))
            return None

        # if we have segments
        if self._has_segments:

            # if we're using the segment id but we don't have the index
            if segment_id is not None and segment_index is None:

                # match the segment id to the segment using the self._segment_ids attribute
                for index, item_id in self._segment_ids.items():
                    if item_id == segment_id:
                        return self._segments[index]
                else:
                    logger.error('Cannot find segment with id "{}".'.format(segment_id))
                    return None

            # if we know the index
            elif segment_index is not None:

                # if the index is valid
                if 0 <= segment_index < len(self._segments):

                    # if the segment is not a TranscriptionSegment object, make it one
                    if not isinstance(self._segments[segment_index], TranscriptionSegment):
                        self._segments[segment_index] = TranscriptionSegment(self._segments[segment_index])

                    # if we also have a segment id, check if it matches
                    if segment_id is not None:
                        if self._segments[segment_index].id == segment_id:
                            return self._segments[segment_index]
                        else:
                            logger.error('Segment at index "{}" with id "{}", doesn\'t match the requested id "{}".'
                                         .format(segment_index, segment_id, self._segments[segment_index].id))
                            return None

                    return self._segments[segment_index]
                else:
                    logger.error('Cannot get segment with index "{}".'.format(segment_index))
                    return None

    def get_num_segments(self):
        """
        This returns the total number of segments in the transcription
        """

        # if we have segments, return the number of segments
        if self._has_segments:
            return len(self._segments)

        # otherwise return 0
        return 0

    def get_num_lines(self):
        """
        This returns the total number of lines in the transcription
        - soon it will look if the segments are meta or not
        """
        return self.get_num_segments()

    def __len__(self):
        """
        This returns the total number of segments in the transcription
        """
        return self.get_num_segments()

    def delete_segment(self, segment_index: int, reset_segments: bool = True):
        """
        This removes a segment from the transcription and then re-sets the segments
        """

        # if the index is valid
        if segment_index is not None and 0 <= segment_index < len(self._segments):

            # remove the segment
            self._segments.pop(segment_index)

            # reset the segments if not mentioned otherwise
            if reset_segments:
                self._set_segments()

        # set the dirty flag anyway
        self.set_dirty()

    def delete_segments_between(self, start: float, end: float, reset_segments: bool = True):
        """
        This removes all the segments that are between the specified time interval
        """

        if not self._has_segments:
            return None

        # create new segments list that doesn't contain the segments that start or end between the specified interval
        self._segments = \
            [segment for segment in self._segments
             if not (start <= segment.start <= end or start <= segment.end <= end)]

        # reset the segments if not mentioned otherwise
        if reset_segments:
            self._set_segments()

        # set the dirty flag anyway
        self.set_dirty()

        return True

    def add_segments(self, segments: list, overwrite=False):
        """
        This adds a list of segments to the transcription and then re-sets the segments
        :param segments: a list of segments
        :param overwrite: if True, in case a segment we add overlaps with the time range of an existing segment,
                          we remove the existing segment and add the new one.
        """

        # if we have to overwrite existing segments:
        if overwrite:
            # go through all the segments and check if they overlap with any of the existing segments
            for segment in segments:

                # if the segment_data is a dict or list, turn it into a TranscriptionSegment object
                segment = \
                    TranscriptionSegment(segment, parent_transcription=self) \
                        if isinstance(segment, dict) or isinstance(segment, list) else segment

                # remove overlapping segments
                self.delete_segments_between(segment.start, segment.end, reset_segments=False)

            # set the segments here after we removed all the overlapping segments
            self._set_segments()

        for segment in segments:
            self.add_segment(segment, skip_reset=True)

        # reset the segments here after we added all the segments
        self._set_segments()

    def add_segment(self, segment: dict or object, segment_index: int = None, skip_reset=False):
        """
        This adds a segment to the transcription and then re-sets the segments.
        If a segment_index is passed, the segment will be added at that index, and the rest of the segments will be
        shifted to the right. If no segment_index is passed, the segment will be added to the end of the segments list.
        :param segment: a segment object or a dict that can be turned into a segment object
        :param segment_index: the index at which to add the segment.
        :param skip_reset: if True, the segments will not be re-set (only use if you're doing _set_segments manually!)
        """

        # make sure we have a segments list
        if not self._has_segments:
            self._segments = []

        # if the segment_data is a dict or list, turn it into a TranscriptionSegment object
        segment = \
            TranscriptionSegment(segment, parent_transcription=self) \
            if isinstance(segment, dict) or isinstance(segment, list) else segment

        # we need to add the transcription as a parent of the segment
        segment.parent_transcription = self

        # if the segment's id is none or if it collides with another segment's id
        if segment.id is None or segment.id in self._segment_ids.values():

            # get a new id for the segment
            segment.id = self.generate_new_segment_id()

        # if we're adding a segment at a specific index
        # and the index is valid
        if segment_index is not None and 0 <= segment_index < len(self._segments):

            # add the segment at the index
            self._segments.insert(segment_index, segment)
            self._has_segments = True

        # otherwise, add the segment to the end of the list
        else:
            self._segments.append(segment)
            self._has_segments = True
            segment_index = len(self._segments) - 1

        # make sure that we have the segment id in the segment_ids dict
        self._segment_ids[segment_index] = segment.id

        # reset the segments
        if not skip_reset:
            self._set_segments()

        # set the dirty flag
        self.set_dirty()

    def generate_new_segment_id(self):
        """
        This looks through all the segment ids and returns the next highest id
        """

        # if we don't have segments, return 0
        if not self._has_segments:
            return 0

        # go through all the ids and calculate the highest
        return int(max(self._segment_ids.values())) + 1

    def merge_segments(self, segment_index_list: list):
        """
        This merges multiple segments of said segment_indexes into the first segment of the list
        """

        # if the transcription has segments, and the segment_index_list is at least 2 items long
        if not self._has_segments or not segment_index_list or len(segment_index_list) < 2:
            return None

        # check if all the indexes are consecutive and valid
        for i, segment_index in enumerate(segment_index_list[:-1]):

            # if the indexes are not consecutive
            if segment_index_list[i + 1] - segment_index_list[i] != 1:
                logger.error("Cannot merge segments. The segment indexes are not consecutive.")
                return False

            # if the index is not within the range of the segments
            if not 0 <= segment_index < len(self._segments):
                logger.error("Cannot merge segments. The segment index {} is within the segment index range."
                             .format(segment_index))
                return False

        # get the first segment
        first_segment = self.get_segment(segment_index_list[0])

        # we'll use this to keep track of the offset of the segments after their indexes decrease
        segment_offset = 0

        # go through all the segments and merge them into the first segment
        for segment_index in segment_index_list[1:]:

            # get the segment
            segment = self.get_segment(segment_index)

            # merge the segment into the first segment
            first_segment += segment

            # delete the segment that was merged into the first segment
            self.delete_segment(segment_index - segment_offset, reset_segments=False)

            # increase the offset
            segment_offset += 1

        # reset the segments
        self._set_segments()

        # set the dirty flag
        self.set_dirty()

    def save_soon(self, force=False, backup: bool or float = False, auxiliaries=True, sec=1, **kwargs):
        """
        This saves the transcription to the file,
        but keeping track of the last time it was saved, and only saving
        if it's been a while since the last save
        :param force: bool, whether to force save the transcription even if it's not dirty
        :param backup: bool, whether to backup the transcription file before saving, if an integer is passed,
                             it will be used to determine the time in hours between backups
        :param auxiliaries: bool, whether to save the auxiliaries
        :param sec: int, how soon in seconds to save the transcription, if 0, save immediately
                    (0 seconds also means waiting for the execution to finish before returning from the function)
        """

        # if the transcription is not dirty
        # or if this is not a forced save
        # don't save it
        if not self.is_dirty() and not force:
            logger.debug("Transcription is unchanged. Not saving.")
            return False

        # if there's no waiting time set, save immediately
        if sec == 0:

            # but first cancel the save timer if it's running
            if self._save_timer is not None:
                self._save_timer.cancel()
                self._save_timer = None

            return self._save(backup=backup, auxiliaries=auxiliaries)

        # if we're calling this function again before the last save was done
        # it means that we're calling this function more often so many changes might follow in our Transcript,
        # so throttle the save timer for the next time to increase the time between saves
        # also, because the last save didn't executed, we don't have to start another save timer
        # since all changes will be saved when the existing save timer executes
        if self._save_timer is not None:
            # only increase the throttle if it's not already at the max
            if self._save_timer_throttle < 3:
                self._save_timer_throttle *= 1.05
            return
        else:
            self._save_timer_throttle = 1

        # calculate the throttled time
        throttled_sec = sec * self._save_timer_throttle

        kwargs = {**{'backup': backup}, **kwargs}

        self._save_timer = Timer(throttled_sec, self._save, kwargs=kwargs)
        self._save_timer.start()

    def _save(self, backup: bool or float = False, auxiliaries=True,
              if_successful: callable = None, if_failed: callable = None, if_none: callable = None, **kwargs):
        """
        This saves the transcription to the file
        :param backup: bool, whether to backup the transcription file before saving, if an integer is passed,
                                it will be used to determine the time in hours between backups
        :param auxiliaries: bool, whether to save the auxiliaries
        :param if_successful: callable, a function to call if the transcription was saved successfully
        :param if_failed: callable, a function to call if the transcription failed to save
        :param if_none: callable, a function to call if the transcription was not saved because it was not dirty
        """

        # create the transcription data dict
        transcription_data = self.to_dict()

        # add 'modified' to the transcription json
        transcription_data['last_modified'] = str(time.time()).split('.')[0]

        # use the transcription utils function to write the transcription to the file
        save_result = TranscriptionUtils.write_to_transcription_file(
            transcription_data=transcription_data,
            transcription_file_path=self.__transcription_file_path,
            backup=backup
        )

        # set the exists flag to True
        self._exists = True

        if save_result:
            # set the last save time
            self._last_save_time = time.time()

            # recalculate transcription hash
            self._get_transcription_hash()

            # reset the save timer
            self._save_timer = None

            # reset the dirty flag back to False
            self.set_dirty(False)

            # save the auxiliaries
            if auxiliaries:
                self._save_auxiliaries()

        # if we're supposed to call a function when the transcription is saved
        if save_result and if_successful is not None:

            # call the function
            if_successful()

        # if we're supposed to call a function when the save failed
        elif not save_result and if_failed is not None:
            if_failed()

        return save_result

    def _save_auxiliaries(self):
        """
        This saves the srt and txt files next to the transcription file
        and then updates the transcription file with the paths to the srt and txt files
        """

        # if the srt or txt file paths are not set
        if self._srt_file_path is None or self._txt_file_path is None:

            # for the filename use the basename of the transcription file,
            # without the .transcription.json extension
            if self.__transcription_file_path.endswith(".transcription.json"):
                file_name = self.__transcription_file_path[:-len(".transcription.json")]

            # if the transcription file extension is different (it shouldn't...),
            # remove the extension after the last dot using os splitext
            else:
                file_name = os.path.splitext(self.__transcription_file_path)[0]

            # if the srt file path is not set
            if self._srt_file_path is None and self.has_segments:
                # set the srt file path
                self._srt_file_path = file_name + '.srt'

            # if the txt file path is not set
            if self._txt_file_path is None and self.has_segments:
                # set the txt file path
                self._txt_file_path = file_name + '.txt'

            # make sure that the srt and txt file paths are not absolute
            if self._srt_file_path is not None:
                self._srt_file_path = os.path.basename(self._srt_file_path)

            if self._txt_file_path is not None:
                self._txt_file_path = os.path.basename(self._txt_file_path)

            # save the transcription to file to add the new paths
            # but don't save the auxiliaries again, or we might get into an endless recursion
            if self._save(auxiliaries=False):
                logger.debug('Updated auxiliaries paths in transcription file {}.'
                             .format(self.__transcription_file_path))

        # update srt file
        if self._srt_file_path is not None:

            # save the srt file next to the transcription file
            full_srt_file_path = os.path.join(os.path.dirname(self.__transcription_file_path), self._srt_file_path)

            TranscriptionUtils.write_srt(self._segments, full_srt_file_path)

        # update txt file
        if self._txt_file_path is not None:

            # save the txt file next to the transcription file
            full_txt_file_path = os.path.join(os.path.dirname(self.__transcription_file_path), self._txt_file_path)

            TranscriptionUtils.write_txt(self._segments, full_txt_file_path)

    def _get_transcription_hash(self):
        """
        This calculates the hash of a dict version of the transcription
        (the actual things that are written to the file)
        and then calculates the hash.
        """

        # get the dict version of the transcription
        transcription_dict = self.to_dict()

        # calculate the hash (also sort the keys to make sure the hash is consistent)
        self._last_hash = hashlib.md5(json.dumps(transcription_dict, sort_keys=True).encode('utf-8')).hexdigest()

        return self._last_hash

    def get_timecode_data(self):
        """
        Returns the timeline_fps and timeline_start_tc attribute values
        """

        # if both values exist return them in a tuple
        if self._timeline_fps is not None and self._timeline_start_tc is not None:
            return self._timeline_fps, self._timeline_start_tc

        # otherwise return False
        return False

    def set_timecode_data(self, timeline_fps, timeline_start_tc):
        """
        Sets the timeline_fps and timeline_start_tc attribute values
        Then it also sets the dirty flag and saves the transcription
        """
        self._timeline_fps = timeline_fps
        self._timeline_start_tc = timeline_start_tc

        self._dirty = True
        self.save_soon(sec=0, auxiliaries=False)

    @staticmethod
    def seconds_to_timecode(seconds, fps, start_tc_offset: str or Timecode = None, return_timecode_data=False):

        # use try for the timecode conversion,
        # in case the framerate or timeline_start_tc are invalid
        try:

            # since we can't have a timecode with 0 frames,
            # if the seconds are 0, we set the timecode to 00:00:00:00 as a string
            if float(seconds) == 0:
                timecode = '00:00:00:00'

            else:
                # convert the seconds to timecode
                timecode = Timecode(fps, start_seconds=float(seconds))

            # if we need to offset the timecode with the transcription file's start_tc
            if start_tc_offset and start_tc_offset != '00:00:00:00':

                # get the start timecode
                start_tc = Timecode(fps, start_tc_offset)

                # add the start_tc to the final timecode, but only if the timecode is not 00:00:00:00
                if timecode == '00:00:00:00' or timecode is None or not isinstance(timecode, Timecode):
                    timecode = start_tc
                else:
                    timecode = start_tc + timecode

            else:
                start_tc = '00:00:00:00'

            # if we need to return the timecode data as well
            if return_timecode_data:
                return timecode, fps, start_tc

            return timecode

        except:
            logger.debug('Cannot convert seconds to timecode - something went wrong:', exc_info=True)
            return None

    @staticmethod
    def timecode_to_seconds(timecode: str or Timecode,
                            fps, start_tc_offset: str or Timecode, return_timecode_data=False):
        """
        Converts a timecode to seconds
        """

        seconds = None
        timeline_start_tc = '00:00:00:00'

        # use try for the timecode conversion,
        # in case the framerate or timeline_start_tc are invalid
        try:

            # initialize the timecode object
            timecode = Timecode(fps, timecode)

            # if we need to offset the timecode with the transcription file's start_tc
            if start_tc_offset and start_tc_offset != '00:00:00:00':

                # initialize the timecode object for the start tc
                timeline_start_tc = Timecode(fps, start_tc_offset)

                # if the timecode is the same as the start timecode, return 0.0 to avoid errors
                if timeline_start_tc == timecode:
                    seconds = 0

                # only offset if timecode is different than 00:00:00:00
                if timeline_start_tc != '00:00:00:00' and seconds is None:
                    # calculate the new timecode
                    timecode = timecode - timeline_start_tc

            # convert the timecode to seconds by dividing the frames by the framerate
            # if it hasn't been calculated yet
            if seconds is None:
                seconds = float(timecode.frames) / float(fps)

            # if we need to return the timecode data as well
            if return_timecode_data:
                return seconds, fps, timeline_start_tc

            return seconds

        except AttributeError:
            logger.warning('Cannot convert timecode to seconds - invalid timecode')
            return None

        except ValueError:
            logger.warning('Cannot convert timecode to seconds - invalid timecode')
            return None

        except:
            logger.error('Cannot convert timecode to seconds - something went wrong:', exc_info=True)
            return None

    def time_intervals_to_transcript_segments(self, time_intervals: list) -> list or None:
        '''
        This function converts a list of time intervals to a list of transcript segments

        :param time_intervals: a list of time intervals
        :return: a list of transcript segments
        '''

        # if the time intervals or segments are empty or not a list/dict, return None
        if time_intervals is None or type(time_intervals) is not list and self._has_segments:
            return None

        # if the time intervals are empty, return None
        if len(time_intervals) == 0:
            return []

        # take all time intervals and check if they overlap with any of the segments
        # if they do, add the segment to the list of segments to return
        segments_to_return = []

        # first sort the time intervals by start time
        time_intervals = sorted(time_intervals, key=lambda x: x['start'])

        # then sort the segments by start time
        segments = sorted(self._segments, key=lambda x: x.start)

        # now take all the time intervals and check if they overlap with any of the segments
        for current_time_interval in time_intervals:

            current_time_interval['start'] = float(current_time_interval['start'])
            current_time_interval['end'] = float(current_time_interval['end'])

            # test this time interval against all segments
            for current_segment in segments:

                # if the current time interval overlaps with the current segment, add it to the list of segments
                if current_segment.start >= current_time_interval['start'] \
                        and current_segment.end <= current_time_interval['end']:

                    segments_to_return.append(current_segment)

                # otherwise, if the current segment is after the current time interval, break
                # this only works if the segments and time intervals have been sorted
                elif current_segment.end > current_time_interval['end']:
                    break

        return segments_to_return

    @staticmethod
    def transcript_segments_to_time_intervals(segments: list) -> list or None:
        '''
        This function takes a list of transcript segments and returns the continuous time intervals resulting from them

        :param segments:
        :return: the list of time intervals
        '''

        # if the segments are not empty or not a list, return None
        if segments is None or type(segments) is not list or len(segments) == 0:
            logger.debug('Could not convert transcript segments to time intervals '
                         'because the segments are empty or not a list')
            return None

        # these are the group time intervals that we'll return eventually
        # this group will consist of multiple time intervals taken from transcript segments that
        # are next to each other (end_time of previous segment matches the start_time of current segment)
        time_intervals = [{}]

        time_interval_num = 0

        # remove duplicates from segments
        # this is important because if there are duplicates, the time intervals might repeat
        segments_unique = []
        [segments_unique.append(x) for x in segments if x not in segments_unique]

        # place the unique segments back into the original list
        segments = segments_unique

        # sort the segments by start time
        segments = sorted(segments, key=lambda x: x.start)

        # loop through the segments
        for current_segment in segments:

            # if the current time interval doesn't have a start time, add it
            # (i.e. this segment is the first in this time interval)
            if 'start' not in time_intervals[time_interval_num]:
                time_intervals[time_interval_num]['start'] = current_segment.start

            # if the end time of the current time_interval matches the start time of the current segment,
            # it means that there's no gap between the current time_interval and the current segment,
            # so add the current segment to the current time interval, by simply updating the end time
            # this extends the time interval to include the current segment too
            if 'end' not in time_intervals[time_interval_num] or \
                    time_intervals[time_interval_num]['end'] == current_segment.start:

                time_intervals[time_interval_num]['end'] = current_segment.end

            # otherwise, it means that the current segment is not next to the current time interval,
            # so start a new time interval containing the current segment
            else:
                time_interval_num += 1
                time_intervals.append({
                    'start': current_segment.start,
                    'end': current_segment.end
                })

        return time_intervals

    # ######################## #
    # TRANSCRIPT GROUP METHODS #
    # ######################## #

    def get_all_transcript_groups(self) \
            -> dict or None:
        '''
        This function returns a dict of transcript groups of this transcription.
        Each dict element contains the transcript group id as key and the transcript group as value.

        :return: a dict of transcript groups or None if the transcription file doesn't exist
        '''

        # return all the transcript groups of this transcription
        return self._transcript_groups if self._transcript_groups else {}

    def get_transcript_group(self, transcript_group_id: str) -> dict or None:
        '''
        Get a transcript group by its name.

        The groups are stored in a list in the transcription file.

        :param transcript_group_id:
        :return: the dictionary of the transcript group in the format {transcript_group_id: transcript_group}
                 an empty dict if the transcript group was not found, but others exist
                 None if there are no transcript groups for this transcription
        '''

        # if there are no transcript groups, return None
        if self._transcript_groups is None:
            return None

        # loop through the transcript groups
        # the groups are stored in a list, and each group is a dict, with the group name as the key
        for transcript_group in self._transcript_groups:

            # if the transcript group name matches the one we're looking for, return it
            if transcript_group_id in transcript_group:
                return transcript_group[transcript_group_id]

        # if we get here, the transcript group was not found
        # but returning an empty dict signals that there are other transcript groups
        # so return an empty dict
        return {}

    def set_transcript_groups(self, transcript_groups: dict, group_id: str = None) -> dict or bool or None:
        """
        This function sets the transcript_groups attribute for this transcription and sets the _dirty flag up.

        It will overwrite any existing transcript groups, unless a group_id is passed, in which case it will
        only overwrite the transcript group with that group_id.

        :param transcript_groups: a dict of transcript groups
        :param group_id: If this is passed, we will only save the transcript group with this group id
        :return: The group dict if the groups were saved successfully, False otherwise
                or None if there were other problems transcription file
        """

        # if the transcript groups are not a dict, return None
        if not isinstance(transcript_groups, dict):
            return None

        # if no group id was passed, overwrite all transcript groups
        if group_id is None:

            # overwrite the transcript groups with the passed transcript_groups
            self._transcript_groups = transcript_groups

        # otherwise, only focus on the passed group id
        else:

            if group_id not in transcript_groups:
                return None

            # if the group with the group_id exists, remove it
            if isinstance(self._transcript_groups, dict) and group_id in self._transcript_groups:
                del self._transcript_groups[group_id]

            # if the transcript groups are not a dict, create a new dict
            if not isinstance(self._transcript_groups, dict):
                self._transcript_groups = {}

            # now add the transcript group to the transcript groups
            self._transcript_groups[group_id] = transcript_groups[group_id]

        # set the dirty flag
        self.set_dirty()

        return True

    def group_id_from_name(self, group_name):
        """
        This function generates a group id using a group name, but also looks into the existing groups

        For now, we're simply stripping, lowercasing and adding a timestamp to the group name.

        :param group_name:
        :return: the group id
        """
        for i in range(100):
            group_id = "{}{}".format(group_name.strip().lower().replace(' ', ''),
                                     datetime.now().strftime('%Y%m%d%H%M%S%f'))

            if not self._transcript_groups or group_id not in self._transcript_groups:
                return group_id

        # throw an exception if we couldn't generate a unique group id after 100 tries
        raise Exception("Couldn't generate a unique group id for group name {}".format(group_name))

    def prepare_transcript_group(self, group_name: str, time_intervals: list,
                                 group_id: str = None, group_notes: str = '',
                                 existing_transcript_groups: list = None,
                                 overwrite_existing: bool = False) -> dict:
        """
        This function prepares a transcript group dict.

        Each group is a dict with the following keys: name, notes, time_intervals

        The purpose is to be able to group together segments of a transcription, although the start and end times
        of the groups are not necessarily always the same as the start and end times of the segments.

        :param group_name:
        :param time_intervals:
        :param group_id:
        :param group_notes:
        :param existing_transcript_groups: if a transcript group is being updated, pass its contents here
        :param overwrite_existing: if the same group_id is found in the existing transcript groups, overwrite it
        :return: the transcript group dict or None if something went wrong
        """

        # trim the group name and group notes
        group_name = group_name.strip()
        group_notes = group_notes.strip() if group_notes else ''

        # if the group id is not provided, use the group name to generate one
        if group_id is None:
            # generate a group id
            group_id = self.group_id_from_name(str(group_name))

        # if we're not overwriting an existing group, see if the group id already exists in existing groups
        if not overwrite_existing \
                and existing_transcript_groups is not None \
                and type(existing_transcript_groups) is list \
                and len(existing_transcript_groups) > 0:

            # keep coming up with group id suffixes until we find one that doesn't exist
            group_name_suffix = 1
            while True:

                # first try the group name as is
                if group_name_suffix != 1:
                    # but after the first iteration, add a suffix (should start at 2)
                    group_id = self.group_id_from_name(group_name + '_' + str(group_name_suffix))

                # if the group id doesn't exist in the existing groups, break out of the loop
                # (convert all to lowercase for comparison to avoid any sort of case sensitivity issues)
                if str(group_id).lower() not in list(map(str.lower, existing_transcript_groups)):
                    break

                # if the group id already exists, increment the suffix and try again
                group_name_suffix += 1

        # return the prepared transcript group
        return {
            group_id: {
                'name': group_name,
                'notes': group_notes,
                'time_intervals': time_intervals
            }
        }

    def segments_to_groups(self, segments: list, group_name: str, group_id: str = None,
                           group_notes: str = '', existing_transcript_groups: list = None,
                           overwrite_existing: bool = False) -> dict or None:
        '''
        This function converts a list of transcript segments to a transcript group

        :param segments: a list of transcript segments
        :param group_name: the name of the transcript group
        :param group_id: the id of the transcript group
        :param group_notes: the notes of the transcript group
        :param existing_transcript_groups: if a transcript group is being updated, pass its contents here
        :param overwrite_existing: if the same group_id is found in the existing transcript groups, overwrite it
        :return: the transcript group dict or None if something went wrong
        '''

        # first, get the time intervals from the segments
        group_time_intervals = []

        # if the segments are empty or not a list, return None
        if segments is None or type(segments) is not list:
            return None

        # get a proper list of time intervals based on the segments
        group_time_intervals = self.transcript_segments_to_time_intervals(segments=segments)

        if group_time_intervals is None:
            return None

        # if the time intervals are empty, return None
        if len(group_time_intervals) == 0:
            return None

        # prepare the transcript group
        transcript_group = \
            self.prepare_transcript_group(
                group_name=group_name,
                time_intervals=group_time_intervals,
                group_id=group_id,
                group_notes=group_notes,
                existing_transcript_groups=existing_transcript_groups,
                overwrite_existing=overwrite_existing)

        return transcript_group


class TranscriptionSegment:
    """
    This class represents a segment in a transcription file
    """

    def __init__(self, segment_data: dict, parent_transcription: Transcription = None):

        # for the segment to be valid,
        # it needs to have start and end times
        self._is_valid = False

        self._id = None
        self._start = None
        self._end = None
        self._words = None
        self._text = None

        self.tokens = None

        # this tells us if the segment is the result of merging other segments
        # once it's flagged as merged, we no longer know which segments it was made from
        self.merged = None

        self.seek = None
        self.temperature = None
        self.avg_logprob = None
        self.compression_ratio = None
        self.no_speech_prob = None

        self._other_data = {}

        # use this in case we need to communicate with the parent
        self._parent_transcription = parent_transcription

        # if the segment data is a list, turn it into a dict first
        if isinstance(segment_data, list):
            segment_data = self.dict_from_list(segment_data)

        self._load_dict_into_attributes(segment_data)

    @property
    def is_valid(self):
        return self._is_valid

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    @property
    def parent_transcription(self):
        return self._parent_transcription

    @parent_transcription.setter
    def parent_transcription(self, value):
        self._parent_transcription = value

    @property
    def start(self):
        return float(self._start)

    @property
    def end(self):
        return float(self._end)

    @property
    def words(self):
        return self._words

    @property
    def text(self):
        return self._text

    def __str__(self):
        return self.text

    @property
    def other_data(self):
        return self._other_data

    def set(self, key: str, value):
        """
        We use this to set some of the attributes of the segment.
        If the segment has a parent, it flags it as dirty.
        """

        allowed_attributes = ['start', 'end', 'text', 'words']

        if key in allowed_attributes:
            setattr(self, '_'+key, value)

            # if the segment has a parent, flag it as dirty
            if self.parent_transcription:
                self.parent_transcription.set_dirty()

            return True

        # throw an error if the key is not valid
        else:
            raise AttributeError('Cannot set the attribute {} for TranscriptSegments, '
                                 'only {} can be set.'.format(key, allowed_attributes))

    def update(self, segment_data: dict or object):
        """
        This updates the segment with new segment_data
        """

        self._load_dict_into_attributes(segment_data)

    # set the known attributes
    __known_attributes = ['id', 'start', 'end', 'words', 'text', 'tokens', 'merged',
                        'seek', 'temperature', 'avg_logprob', 'compression_ratio', 'no_speech_prob']

    __simplified_attributes = ['start', 'end', 'text']

    def _load_dict_into_attributes(self, segment_dict):

        # we need to make a copy of the segment data
        # to make sure that we don't change the original data
        segment_dict = copy.deepcopy(segment_dict)

        # if the segment is not a dictionary, it is not valid
        if not isinstance(segment_dict, dict):
            self._is_valid = False

        # set the attributes
        for attribute in self.__known_attributes:

            # if the known attribute is in the json, set the attribute
            if isinstance(segment_dict, dict) and attribute in segment_dict:

                # convert the start and end times to floats
                if attribute == 'start' or attribute == 'end':
                    segment_dict[attribute] = float(segment_dict[attribute])

                setattr(self, '_'+attribute, segment_dict[attribute])

            # if the known attribute is not in the json,
            # set the attribute to None so we can still access it
            else:
                setattr(self, '_'+attribute, None)

        # other data is everything else
        if segment_dict:
            self._other_data = {k: v for k, v in segment_dict.items() if k not in self.__known_attributes}
        else:
            self._other_data = {}

        # for a segment to be valid,
        # it needs to have start and end times
        if self._start is None or self._end is None:
            self._is_valid = False
        else:
            self._is_valid = True

    def __add__(self, segment: 'TranscriptionSegment'):
        return self.merge(segment=segment)

    def merge(self, segment: 'TranscriptionSegment'):
        """
        This merges the current segment with the segment passed as argument
        """

        # if the segment is not valid, we cannot merge it
        if not segment.is_valid:
            logger.error("Cannot merge segments - second segment is not valid")
            return False

        # if the current segment is not valid, we cannot merge it
        if not self.is_valid:
            logger.error("Cannot merge segments - current segment is not valid")
            return False

        # if the segments are not from the same transcription, we cannot merge them
        if self.parent_transcription != segment.parent_transcription:
            logger.error("Cannot merge segments - segments are not from the same transcription")
            return False

        # if the segments are not consecutive, we cannot merge them
        if self.end > segment.start:
            logger.error("Cannot merge segments "
                         "- current segment's end time is larger than second segment's start time")
            return False

        # merge the words
        self._words = (self._words + segment.words) if self._words is not None else segment.words

        # merge the text
        self._text += segment.text.lstrip()

        # merge the tokens
        self.tokens = (self.tokens + segment.tokens) if self.tokens is not None else segment.tokens

        # merge the other data
        self.other_data.update(segment.other_data)

        # update the end time
        self._end = segment.end

        # keep the seek of the first segment
        # self.seek = self.seek

        # calculate average logprob
        # self.avg_logprob = (self.avg_logprob + segment.avg_logprob) / 2

        # calculate compression ratio
        # self.compression_ratio = (self.compression_ratio + segment.compression_ratio) / 2

        # calculate no speech prob
        # self.no_speech_prob = (self.no_speech_prob + segment.no_speech_prob) / 2

        # calculate temperature
        # self.temperature = (self.temperature + segment.temperature) / 2

        # flag the segment as merged
        self.merged = True

        return self

    def to_dict(self, simplify=False):
        """
        This returns the segment data as a dict, but it only converts the attributes that are __known_attributes
        (or __simplified_attributes if simplify is True)
        """

        # create a copy of the data
        segment_dict = dict()

        attributes_to_use = self.__known_attributes if not simplify else self.__simplified_attributes

        # add the known attributes to the data
        for attribute in attributes_to_use:

            if hasattr(self, '_'+attribute) and getattr(self, '_'+attribute) is not None:
                segment_dict[attribute] = getattr(self, '_'+attribute)

        # merge the other data with the transcription data
        segment_dict.update(self._other_data)

        return segment_dict

    def to_list(self):
        """
        This returns the segment data as a dict, but it only converts the attributes that are __known_attributes
        (or __simplified_attributes if simplify is True)
        """

        # create a copy of the data
        segment_list = []

        # add the known attributes to the data
        # important: the order of the __simple_attributes list is important (start, end, text for eg.)
        for attribute in self.__simplified_attributes:

            if hasattr(self, '_'+attribute) and getattr(self, '_'+attribute) is not None:
                segment_list.append(getattr(self, '_'+attribute))

        # merge the other data with the transcription data
        segment_list.extend(self._other_data)

        return segment_list

    @staticmethod
    def dict_from_list(segment_list):
        """
        This returns the segment data as a dict, but it only converts the attributes
        that are __known_attributes or __simplified_attributes, depending on the list length
        """

        # create a copy of the data
        segment_dict = dict()

        # add the known attributes to the data
        # important: the order of the __simple_attributes list is important (start, end, text for eg.)
        if len(segment_list) == len(TranscriptionSegment.__simplified_attributes):
            for i, attribute in enumerate(TranscriptionSegment.__simplified_attributes):
                segment_dict[attribute] = segment_list[i]

        elif len(segment_list) == len(TranscriptionSegment.__known_attributes):
            for i, attribute in enumerate(TranscriptionSegment.__known_attributes):
                segment_dict[attribute] = segment_list[i]

        else:
            raise Exception('The segment list length does not fit either '
                            '__simplified_attributes nor __known_atttributs lengths.')

        # merge the other data with the transcription data
        segment_dict.update(segment_list[i+1:])

        return segment_dict

    def get_index(self):
        """
        This returns the index of the segment in the parent transcription
        """

        # if the segment has a parent, return its index
        if self.parent_transcription:

            # try to see if the segment is in the parent's segments list
            try:
                segment_index = self.parent_transcription.segments.index(self)

            # it might be that the object was already cleared from the parent's segments list
            except ValueError:
                segment_index = None

            return segment_index

        # if the segment does not have a parent, return None
        else:
            return None

    def __del__(self):
        """
        This deletes the segment from the parent transcription, if it has one, otherwise it just deletes the segment
        """

        # if the segment has a parent, remove it from the parent
        if self.parent_transcription:

            # get the index of the segment from the parent's segments list
            segment_index = self.get_index()

            # delete the segment from the parent
            # (if it still exists in the parent's segments list)
            if segment_index is not None:
                self.parent_transcription.delete_segment(segment_index)

        # if the segment does not have a parent, just delete it
        else:
            del self


class TranscriptionUtils:

    @staticmethod
    def write_to_transcription_file(transcription_data, transcription_file_path, backup=False):

        # if no full path was passed
        if transcription_file_path is None:
            logger.error('Cannot save transcription to path "{}".'.format(transcription_file_path))
            return False

        # if the transcription file path is a directory
        if os.path.isdir(transcription_file_path):
            logger.error(
                'Cannot save transcription - path "{}" is a directory.'.format(transcription_file_path))
            return False

        # if the directory of the transcription file path doesn't exist
        if not os.path.exists(os.path.dirname(transcription_file_path)):
            # create the directory
            logger.debug("Creating directory for transcription file path: {}")
            try:
                os.makedirs(os.path.dirname(transcription_file_path))
            except OSError:
                logger.error("Cannot create directory for transcription file path.", exc_info=True)
                return False
            except:
                logger.error("Cannot create directory for transcription file path.", exc_info=True)
                return False

        # if backup_original is enabled, it will save a copy of the transcription file to
        # .backups/[filename].backup.json, but if backup is an integer, it will only save a backup after [backup] hours
        if backup and os.path.exists(transcription_file_path):

            # get the backups directory
            backups_dir = os.path.join(os.path.dirname(transcription_file_path), '.backups')

            # if the backups directory doesn't exist, create it
            if not os.path.exists(backups_dir):
                os.mkdir(backups_dir)

            # format the name of the backup file
            backup_transcription_file_path = os.path.basename(transcription_file_path) + '.backup.json'

            # if another backup file with the same name already exists, add a consecutive number to the end
            backup_n = 0
            while os.path.exists(os.path.join(backups_dir, backup_transcription_file_path)):

                # get the modified time of the existing backup file
                backup_file_modified_time = os.path.getmtime(os.path.join(backups_dir, backup_transcription_file_path))

                # if the backup file was modified les than [backup] hours ago, we don't need to save another backup
                if (isinstance(backup, float) or isinstance(backup, int)) \
                        and time.time() - backup_file_modified_time < backup * 60 * 60:
                    backup = False
                    break

                backup_n += 1
                backup_transcription_file_path = \
                    os.path.basename(transcription_file_path) + '.backup.{}.json'.format(backup_n)

            # if the backup setting is still not negative, we should save a backup
            if backup:
                # copy the existing file to the backup
                shutil \
                    .copyfile(transcription_file_path, os.path.join(backups_dir, backup_transcription_file_path))

                logger.debug('Copied transcription file to backup: {}'.format(backup_transcription_file_path))

        # encode the transcription json (do this before writing to the file, to make sure it's valid)
        transcription_json_encoded = json.dumps(transcription_data)

        # write the transcription json to the file
        with open(transcription_file_path, 'w', encoding='utf-8') as outfile:
            outfile.write(transcription_json_encoded)

        logger.debug('Saved transcription to file: {}'.format(transcription_file_path))

        return transcription_file_path

    @staticmethod
    def add_count_to_transcription_path(transcription_file_path, target_dir=None):
        """
        This adds a count to the transcription file path, so that the transcription file path is unique
        ending either in a file with no number (filename.transcription.json) or a number (filename_2.transcription.json)
        """

        # remove .transcription.json from the end of the path, but don't use replace, it needs to be at the end
        if transcription_file_path.endswith(".transcription.json"):
            transcription_file_path_base = transcription_file_path[:-len(".transcription.json")]
        # otherwise, remove the extension after the last dot using os splitext
        else:
            transcription_file_path_base = os.path.splitext(transcription_file_path)[0]

        # if the transcription_file_path_base contains "_{digits}", remove it
        transcription_file_path_base = re.sub(r"_[0-9]+$", "", transcription_file_path_base)

        # use target_dir or don't...
        full_transcription_file_path = os.path.join(target_dir, transcription_file_path_base) \
            if target_dir else transcription_file_path_base

        # add the .transcription.json extension
        full_transcription_file_path += ".transcription.json"

        count = 2
        while os.path.exists(full_transcription_file_path):
            # add the count to the transcription file path
            full_transcription_file_path = f"{transcription_file_path_base}_{count}.transcription.json"

            # increment the count
            count += 1

        return full_transcription_file_path

    @staticmethod
    def convert_srt_to_transcription_json(srt_file_path: str, transcription_file_path: str = None,
                                          overwrite: bool = False):
        '''
        Converts an srt file to a transcription json file, saves it in the same directory
         and returns the name of the transcription file.

        If it's impossible to convert or save the srt file, it will return None

        If overwrite is True, it will overwrite any existing transcription file from the same directory.

        :param srt_file_path:
        :param transcription_file_path:
        :param overwrite:
        :return:
        '''

        # make sure the srt file exists
        if not os.path.exists(srt_file_path):
            logger.warning("SRT file {} doesn't exist.".format(srt_file_path))
            return None

        # get the contents of the srt file
        with codecs.open(srt_file_path, 'r', 'utf-8-sig') as srt_file:
            srt_contents = srt_file.read()

        srt_segments = []
        full_text = ''

        # if properly formatted, the srt file should have 2 new lines between each subtitle
        # so go through all of them
        for line_string in re.split('\r\n|\n', srt_contents):

            if line_string != '':

                # if the line is a number, it's the subtitle number
                if line_string.isdigit():
                    idx = int(line_string)

                    # so create a new subtitle segment
                    srt_segments.append({'id': str(idx), 'start': 0.0, 'end': 0.0, 'text': ''})

                # if the line is not a number, it's either the time or the text
                else:
                    # if the line contains '-->', it's the time
                    if '-->' in line_string:
                        # split the line in the middle to get the start and end times

                        start_time, end_time = line_string.split('-->')

                        # add these to the last subtitle segment
                        srt_segments[-1]['start'] = TranscriptionUtils.time_str_to_seconds(start_time.strip())
                        srt_segments[-1]['end'] = TranscriptionUtils.time_str_to_seconds(end_time.strip())

                    # if the line doesn't contain '-->', it's the text
                    else:

                        # add the text to the last subtitle segment
                        # but also a white space if there's already a string inside the segment text
                        srt_segments[-1]['text'] += \
                            ' ' + line_string if len(srt_segments[-1]['text']) > 0 else line_string

                        # add the text to the full text
                        full_text += ' ' + line_string if len(full_text) > 0 else line_string

        # initialize the transcription_data for the transcription_file
        transcription_data = {'text': full_text,
                              'segments': srt_segments,
                              'task': 'convert_srt_to_transcription_json',
                              'audio_file_path': '',
                              'srt_file_path': os.path.basename(srt_file_path),
                              'name': os.path.splitext(os.path.basename(srt_file_path))[0]
                              }

        # if no transcription file path was passed, create one based on the srt file name
        if transcription_file_path is None:
            transcription_file_path = os.path.splitext(srt_file_path)[0] + '.transcription.json'

        if not overwrite and os.path.exists(transcription_file_path):
            logger.error("Transcription file {} already exists. Cannot overwite.".format(transcription_file_path))
            return None

        # if the transcription file already exists, log that we're overwriting it
        elif overwrite and os.path.exists(transcription_file_path):
            logger.info("Overwritting {} with transcription from SRT.".format(transcription_file_path))

        else:
            logger.info("Saving transcription from SRT to {}.".format(transcription_file_path))

        TranscriptionUtils.write_to_transcription_file(
            transcription_file_path=transcription_file_path, transcription_data=transcription_data)

        return transcription_file_path

    @staticmethod
    def time_str_to_seconds(time_str: str) -> float:
        '''
        Converts 00:00:00.000 time formats to seconds.
        :param time_str: 00:00:00.000 (string)
        :return:
        '''

        # use regex to get the hours, minutes, seconds and milliseconds
        # from the time string
        time_regex = re.compile(r'(\d{2}):(\d{2}):(\d{2}).(\d)')
        time_match = time_regex.match(time_str)

        # if the time string matches the regex
        if time_match:

            # calculate the seconds
            seconds = int(time_match.group(1)) * 3600 + \
                      int(time_match.group(2)) * 60 + \
                      int(time_match.group(3)) + \
                      int(time_match.group(4)) / 1000

        # otherwise, throw an error
        else:
            exception = 'The passed time string {} is not formatted correctly.'.format(time_str)
            logger.error(exception)

            # throw exception
            raise ValueError(exception)

        return seconds

    @staticmethod
    def format_srt_timestamp(seconds: float, always_include_hours: bool = False, decimal_marker: str = '.'):
        assert seconds >= 0, "non-negative timestamp expected"
        milliseconds = round(seconds * 1000.0)

        hours = milliseconds // 3_600_000
        milliseconds -= hours * 3_600_000

        minutes = milliseconds // 60_000
        milliseconds -= minutes * 60_000

        seconds = milliseconds // 1_000
        milliseconds -= seconds * 1_000

        hours_marker = f"{hours:02d}:" if always_include_hours or hours > 0 else ""
        return f"{hours_marker}{minutes:02d}:{seconds:02d}{decimal_marker}{milliseconds:03d}"

    @staticmethod
    def write_srt(transcript_segments: list, srt_file_path: str):
        """
        Write the transcript segments to a file in SRT format.
        """

        if not transcript_segments:
            return

        with open(srt_file_path, "w", encoding="utf-8") as srt_file:
            i = 1
            for segment in transcript_segments:

                start_str = TranscriptionUtils.format_srt_timestamp(
                    segment.start, always_include_hours=True, decimal_marker=',')

                end_str = TranscriptionUtils.format_srt_timestamp(
                    segment.end, always_include_hours=True, decimal_marker=',')

                text_str = segment.text.strip().replace('-->', '->')

                # write srt lines
                print(
                    f"{i}\n"
                    f"{start_str} --> "
                    f"{end_str}\n"
                    f"{text_str}\r\n",
                    file=srt_file,
                    flush=True,
                )
                i += 1

    @staticmethod
    def write_txt(transcript_segments: list, txt_file_path: str):
        """
        Write the transcript segments to a file in TXT format.
        Each segment is written on a new line.
        """

        if not transcript_segments:
            return

        with open(txt_file_path, "w", encoding="utf-8") as txt_file:
            for segment in transcript_segments:
                # write txt lines
                print(
                    f"{segment.text.strip()}",
                    file=txt_file,
                    flush=True,
                )

    @staticmethod
    def write_avid_ds(transcript_segments: dict, avid_ds_file_path: str, timeline_fps, timeline_start_tc):
        """
        Write the transcript segments to a file in Avid DS format.
        """

        # this is an example format for Avid DS
        # @ This file written with StoryToolkitAI, version x.x.x
        #
        # <begin subtitles>
        #
        # 12:03:46:05 12:03:48:05
        # This is a test.
        #
        # 12:03:48:05 12:03:50:05
        # This is another test.
        #
        # <end subtitles>

        # convert the timeline_start_tc to a Timecode object
        timeline_start_tc = Timecode(timeline_fps, timeline_start_tc)

        def format_timecode_line(start_time, end_time, timeline_fps, timeline_start_tc):
            # convert the start to a timecode
            start_tc = Timecode(timeline_fps, start_seconds=start_time)

            # add the timeline_start_tc to the start_tc
            start_tc = start_tc + timeline_start_tc

            # convert the end to a timecode
            end_tc = Timecode(timeline_fps, start_seconds=end_time)

            # add the timeline_start_tc to the start_tc
            end_tc = end_tc + timeline_start_tc

            return f"{start_tc} {end_tc}"

        with open(avid_ds_file_path, "w", encoding="utf-8") as avid_ds_file:
            # write header
            print(
                f"@ This file was written with StoryToolkitAI\n",
                file=avid_ds_file,
                flush=True
            )

            # write subtitle start
            print(
                f"<begin subtitles>\n",
                file=avid_ds_file,
                flush=True
            )

            # write subtitle lines
            for segment in transcript_segments:
                print(
                    f"{format_timecode_line(segment.start, segment.end, timeline_fps, timeline_start_tc)}\n"
                    f"{segment.text.strip()}\n",
                    file=avid_ds_file,
                    flush=True,
                )

            # write subtitle end
            print(
                f"<end subtitles>",
                file=avid_ds_file,
                flush=True
            )

    @staticmethod
    def write_fusion_text_comp(transcript_segments: dict, comp_file_path: str, timeline_fps):
        '''
        Write the transcript segments into a Fusion Text+ comp file
        '''

        keyframes = []

        # take each transcription segment
        for segment in transcript_segments:

            # frame = int(segment["start"] * fps)

            # calculate frame based on segment start and timeline fps
            # we'll ignore the timeline_start_tc considering that we're in a comp file that starts at 0
            if segment.start != 0:
                keyframe_tc = Timecode(timeline_fps, start_seconds=segment.start)
                frame = keyframe_tc.frames

            # if the segment starts at 0, we'll use frame 1 to form the timecode and frame 0 for the keyframe
            # this is because Timecode objects can't start at 0
            else:
                keyframe_tc = Timecode(timeline_fps, 1)
                frame = 0

            text = segment.text.replace('"', '\\"')

            # create the segment keyframe
            keyframe = '[' + str(frame) + '] = { Value = Text { Value = "' + str(text) + '" } }'

            # if the next segment doesn't start exactly when this one ends, add a keyframe with an empty string
            # but only if this isn't the last segment
            if segment != transcript_segments[-1]:

                # get the next segment
                next_segment = transcript_segments[transcript_segments.index(segment) + 1]

                # if the next segment doesn't start exactly when this one ends, add a keyframe with an empty string
                if next_segment.start != segment.end:
                    # calculate frame based on segment end and timeline fps
                    # we'll ignore the timeline_start_tc considering that we're in a comp file that starts at 0
                    keyframe_tc = Timecode(timeline_fps, start_seconds=segment.end)
                    frame = keyframe_tc.frames
                    keyframe += ',\n[' + str(frame) + '] = { Value = Text { Value = "" } }'

            keyframes.append(keyframe)

        # if there are no keyframes, return False
        if len(keyframes) == 0:
            return False

        # turn the keyframes into a string with newlines and indentation
        keyframes_str = ",\n            ".join(keyframes)

        # place the above keyframes in the fusion template
        fusion_template = '''
        {
            Tools = ordered() {
                TranscriptText = TextPlus {
                    Inputs = {
                        Width = Input { Value = 1920, },
                        Height = Input { Value = 1080, },
                        Font = Input { Value = "Open Sans", },
                        Style = Input { Value = "Bold", },
                        VerticalJustificationNew = Input { Value = 3, },
                        HorizontalJustificationNew = Input { Value = 3, },
                        StyledText = Input {
                            SourceOp = "TranscriptTextStyledText",
                            Source = "Value",
                        },
                    },
                    ViewInfo = OperatorInfo { Pos = { 311.26, 124.0282 } },
                },
                TranscriptTextStyledText = BezierSpline {
                    SplineColor = { Red = 237, Green = 142, Blue = 243 },
                    KeyFrames = {
                        ''' + keyframes_str + ''',
                    }
                },
                MergeText = Merge {
                    CtrlWZoom = false,
                    NameSet = true,
                    Inputs = {
                        Foreground = Input {
                            SourceOp = "TranscriptText",
                            Source = "Output",
                        },
                        PerformDepthMerge = Input { Value = 0, },
                    },
                    ViewInfo = OperatorInfo { Pos = { 311.26, 50.0282 } },
                },
                StoryToolkitAI_Transcript = Underlay {
                    CtrlWZoom = false,
                    NameSet = true,
                    Inputs = {
                        Comments = Input { Value = "Exported using StoryToolkitAI", }
                    },
                    ViewInfo = UnderlayInfo {
                        Pos = { 307.152, 15.0243 },
                        Size = { 172, 164.121 }
                    },
                }
            },
            ActiveTool = "Text1"
        }
        '''

        # write the comp file
        with open(comp_file_path, "w", encoding="utf-8") as comp_file:
            print(
                f'{fusion_template}',
                file=comp_file,
                flush=True
            )

        # return the comp file path
        return comp_file_path
