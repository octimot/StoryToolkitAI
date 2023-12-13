import copy
import os
import codecs
import json
import hashlib
import shutil
import time
from datetime import datetime
import re
from threading import Timer

from timecode import Timecode

from storytoolkitai.core.logger import logger
from .transcription import Transcription
from .media import MediaItem


class Story:
    
    _instances = {}
    
    def __new__(cls, *args, **kwargs):
        """
        This checks if the current story file path isn't already loaded in an instance
        and returns that instance if it is.
        """

        # we use the story file path as the id for the instance
        story_path_id = cls.get_story_path_id(*args, **kwargs)

        # if the story file path is already loaded in an instance, we return that instance
        if story_path_id in cls._instances:

            return cls._instances[story_path_id]

        # otherwise we create a new instance
        instance = super().__new__(cls)

        # and we store it in the instances dict
        cls._instances[story_path_id] = instance

        # then we return the instance
        return instance
    
    def __init__(self, story_file_path):

        # prevent initializing the instance more than once if it was found in the instances dict
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._story_path_id = None
        self.__story_file_path = None

        # this is used to check if the file has changed
        # it will be updated only when the file is loaded and saved
        self._last_hash = None

        self._name = None

        self._lines = []
        self._text = ''

        # timecode data variables
        self._timeline_fps = None
        self._timeline_start_tc = None

        # the main language of the story
        self._language = None

        # this is set to false if the file wasn't found
        self._exists = False

        # for a file to qualify as a story file,
        # it needs to have lines or a lines attribute
        self._is_story_file = False

        # this is set to true if the story file has lines (len > 0)
        self._has_lines = False

        # here we store all the other data that is not part of the known attributes
        # but was found in the story file
        self._other_data = {}

        # where we store the story data from the file
        # this will be empty once the data is loaded into attributes
        self._data = None

        # use the passed story file path
        self.load_from_file(file_path=story_file_path)

        # we use this to keep track if we updated, deleted, added, or changed anything
        self._dirty = False

        # this is used to keep track of the last time the story was saved
        self._last_save_time = None

        # with this we can set a timer to save the story after a certain amount of time
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
        if self.__class__._instances[self.story_path_id] == self:
            del self.__class__._instances[self.story_path_id]

    @property
    def language(self):
        return self._language

    @property
    def story_file_path(self):
        return self.__story_file_path

    @property
    def has_lines(self):
        return self._has_lines

    @property
    def is_story_file(self):
        return self._is_story_file

    @property
    def story_path_id(self):
        return self._story_path_id

    @property
    def lines(self):
        return self._lines

    @property
    def name(self):
        return self._name

    @property
    def text(self):
        return self._text

#    def __str__(self):
#        return self.text

    def __dict__(self):
        return self.to_dict()

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
    def other_data(self):
        return self._other_data
    
    @property
    def dirty(self):
        return self._dirty

    def is_dirty(self):
        return self._dirty

    def set_dirty(self, value=True):
        self._dirty = value

    def set(self, key: str or dict, value=None):
        """
        We use this to set some of the attributes of the story.
        If the attribute was changed, we set the dirty flag to true.
        """

        # everything that is "known"
        allowed_attributes = copy.deepcopy(self.__known_attributes)

        # but without the lines attribute
        allowed_attributes.remove('lines')

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
            raise AttributeError('Cannot set the attribute {} for Story, '
                                 'only {} can be set.'.format(key, allowed_attributes))
        
    def reload_from_file(self, save_first=False):
        """
        This reloads the story file from disk and sets the attributes
        :param save_first: if True, we save the story first and then reload it
        """

        # if there's a save timer running, we save the story first
        if save_first and self._save_timer is not None:

            # cancel timer
            self._save_timer.cancel()

            # save story now
            self._save()

        # load the story file from disk
        self.load_from_file(file_path=self.__story_file_path)

    def load_from_file(self, file_path):
        """
        This changes the story_file_path
        and loads the story file from disk and sets the attributes
        """
        self.__story_file_path = file_path

        # when we set the story file_path, we also check if the file exists
        # but only if the file_path is a string
        self._exists = os.path.isfile(self.__story_file_path) if isinstance(file_path, str) else False

        # load the json found in the file into attributes
        self._load_json_into_attributes()

    __known_attributes = [
        'name', 'lines',
        'language',
        'timeline_fps', 'timeline_start_tc'
    ]

    @staticmethod
    def get_story_path_id(story_file_path: str = None):
        return hashlib.md5(story_file_path.encode('utf-8')).hexdigest()
    
    def _load_json_into_attributes(self):

        # calculate the new path id
        self._story_path_id = self.get_story_path_id(self.__story_file_path) \
            if self.__story_file_path else None

        if self._exists:
            # get the contents of the story file
            try:

                logger.debug("Loading story file {}".format(self.__story_file_path))

                with codecs.open(self.__story_file_path, 'r', 'utf-8-sig') as json_file:
                    self._data = json.load(json_file)

                    # let's make a deep copy of the data
                    # so that we can manipulate it without changing the original data
                    self._data = copy.deepcopy(self._data)

            # in case we get JSONDecodeError, we assume that the file is not a valid JSON file
            except json.decoder.JSONDecodeError:
                self._data = {}

            # if we have a file that is not a valid JSON file, we assume that it is not a story file
            except:
                logger.error("story file {} is invalid".format(self.__story_file_path, exc_info=True))
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

        # calculate the hash of the story data
        self._get_story_hash()

        # check if this is a valid story
        self._is_valid_story_data()

    def to_dict(self):
        """
        This returns the story data as a dict.
        It doesn't include all the attributes, only the known ones and the other data.
        """

        # create a copy of the data
        story_dict = dict()

        # add the known attributes to the data
        for attribute in self.__known_attributes:

            # if the attribute is set, add it to the dict
            if hasattr(self, '_'+attribute) and getattr(self, '_'+attribute) is not None:

                # if the attribute is lines, we need to convert the lines to dicts too
                if attribute == 'lines':
                    story_dict[attribute] = [line.to_dict() for line in getattr(self, '_'+attribute)]

                # otherwise, we just add the attribute
                else:
                    story_dict[attribute] = getattr(self, '_'+attribute)

        # merge the other data with the story data
        story_dict.update(self._other_data)

        return story_dict

    def _is_valid_story_data(self):
        """
        This checks if the story is valid by looking at the lines in the data
        """

        # for story data to be valid
        # it needs to have lines which are a list
        # and either the list needs to be empty or the first item in the list needs to be a valid line
        if (isinstance(self._lines, list) \
                and (len(self._lines) == 0
                     or (isinstance(self._lines[0], StoryLine) and self._lines[0].is_valid)
                     or StoryLine(self._lines[0]).is_valid)):
            self._is_story_file = True
        else:
            self._is_story_file = False

    def _process_attribute(self, attribute_name, value):
        """
        This processes the attributes of the story file
        """

        if attribute_name == 'name':

            # if there is no name, we use the file name without the extension
            if not value or value == '':
                value = os.path.splitext(os.path.basename(self.__story_file_path))[0]

        # the lines
        elif attribute_name == 'lines':

            # set the lines
            self._set_lines(lines=value)

            # return None since we already set the attributes in the method
            return None

        return value

    def _set_lines(self, lines: list = None):
        """
        This method sets the _lines attribute (if lines is not None),
        checks if all the lines are StoryLines
        then re-calculates the _has_lines
        """

        # if lines were passed, set them
        if lines is not None:
            self._lines = lines

        # if we have lines, make sure that they're all objects
        for index, line in enumerate(self._lines):

            # if the line is not an object, make it an object
            if not isinstance(line, StoryLine):

                # turn this into a line object
                self._lines[index] = StoryLine(line, parent_story=self)

            # take the text from all the lines and put it in the story ._text attribute
            self._text = (self._text + self._lines[index].text) \
                if isinstance(self._text, str) else self._lines[index].text

        # sort all the lines by their start time
        # self._lines = sorted(self._lines, key=lambda x: x.start)

        # re-calculate the self._has_lines attribute
        self._has_lines = len(self._lines) > 0

        # re-generate the self._line_ids attribute
        # self._line_ids = {i: line.id for i, line in enumerate(self._lines)}

        # re-calculate if it's valid
        self._is_valid_story_data()

    def get_lines(self):
        """
        This returns the lines in the story
        """

        # if we have lines, return them
        return self._lines if self._has_lines else self._lines
    
    def get_line(self, line_index: int = None):
        """
        This returns a specific line object by its index in the lines list
        :param line_index: the index of the line in the lines list
        """

        if line_index is None:
            logger.error('Cannot get line index "{}".'.format(line_index))
            return None

        # if we have lines
        if self._has_lines:

            # if we know the index
            if line_index is not None:

                # if the index is valid
                if 0 <= line_index < len(self._lines):

                    # if the line is not a StoryLine object, make it one
                    if not isinstance(self._lines[line_index], StoryLine):
                        self._lines[line_index] = StoryLine(self._lines[line_index])

                    return self._lines[line_index]
                else:
                    logger.error('Cannot get line with index "{}".'.format(line_index))
                    return None

    def get_num_lines(self):
        """
        This returns the total number of lines in the story
        """

        # if we have lines, return the number of lines
        if self._has_lines:
            return len(self._lines)

        # otherwise return 0
        return 0

    def __len__(self):
        """
        This returns the total number of lines in the story
        """
        return self.get_num_lines()

    def replace_all_lines(self, new_lines: list):
        """
        This deletes all the lines in the story and then replaces them with the new lines
        """
        # if we have lines
        if self._has_lines:

            # delete all the lines
            self._lines = []

        # add the new lines
        self.add_lines(new_lines)

        # set the dirty flag anyway
        self.set_dirty()

    def delete_line(self, line_index: int, reset_lines: bool = True):
        """
        This removes a line from the story and then re-sets the lines
        """

        # if the index is valid
        if line_index is not None and 0 <= line_index < len(self._lines):

            # remove the line
            self._lines.pop(line_index)

            # reset the lines if not mentioned otherwise
            if reset_lines:
                self._set_lines()

        # set the dirty flag anyway
        self.set_dirty()

    def add_lines(self, lines: list):
        """
        This adds a list of lines to the story and then re-sets the lines
        """

        for line in lines:
            self.add_line(line, skip_reset=True)

        # reset the lines if not mentioned otherwise
        self._set_lines()

    def add_line(self, line: dict or object, line_index: int = None, skip_reset=False):
        """
        This adds a line to the story and then re-sets the lines.
        If a line_index is passed, the line will be added at that index, and the rest of the lines will be
        shifted to the right. If no line_index is passed, the line will be added to the end of the lines list.
        """

        # make sure we have a lines list
        if not self._has_lines:
            self._lines = []

        # if the line_data is a dict, turn it into a StoryLine object
        line = StoryLine(line, parent_story=self) if isinstance(line, dict) else line

        # if the line doesn't contain a type, we assume it's a text line
        if not line.type:
            line._type = 'text'

        if not isinstance(line, StoryLine):
            logger.error('Cannot add line "{}" to story - must be dict or StoryLine object.'.format(line))
            return False

        # if we're adding a line at a specific index
        # and the index is valid
        if line_index is not None and 0 <= line_index < len(self._lines):

            # add the line at the index
            self._lines.insert(line_index, line)
            self._has_lines = True

        # otherwise, add the line to the end of the list
        else:
            self._lines.append(line)
            self._has_lines = True

        # reset the lines
        if not skip_reset:
            self._set_lines()

        # set the dirty flag
        self.set_dirty()
        
    def save_soon(self, force=False, backup: bool or float = False, sec=1, **kwargs):
        """
        This saves the story to the file,
        but keeping track of the last time it was saved, and only saving
        if it's been a while since the last save
        :param force: bool, whether to force save the story even if it's not dirty
        :param backup: bool, whether to backup the story file before saving, if an integer is passed,
                             it will be used to determine the time in hours between backups
        :param sec: int, how soon in seconds to save the story, if 0, save immediately
        """

        # if the story is not dirty
        # or if this is not a forced save
        # don't save it
        if not self.is_dirty() and not force:
            logger.debug("Story is unchanged. Not saving.")
            return False

        # if there's no waiting time set, save immediately
        if sec == 0:

            # but first cancel the save timer if it's running
            if self._save_timer is not None:
                self._save_timer.cancel()
                self._save_timer = None

            return self._save(backup=backup, **kwargs)

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

    def _save(self, backup: bool or float = False,
              if_successful: callable = None, if_failed: callable = None, if_none: callable = None, **kwargs):
        """
        This saves the story to the file
        :param backup: bool, whether to backup the story file before saving, if an integer is passed,
                                it will be used to determine the time in hours between backups
        :param auxiliaries: bool, whether to save the auxiliaries
        :param if_successful: callable, a function to call if the story was saved successfully
        :param if_failed: callable, a function to call if the story failed to save
        :param if_none: callable, a function to call if the story was not saved because it was not dirty
        """

        # create the story data dict
        story_data = self.to_dict()

        # add 'modified' to the story json
        story_data['last_modified'] = str(time.time()).split('.')[0]

        # use the story utils function to write the story to the file
        save_result = StoryUtils.write_to_story_file(
            story_data=story_data,
            story_file_path=self.__story_file_path,
            backup=backup
        )

        # set the exists flag to True
        self._exists = True

        if save_result:
            # set the last save time
            self._last_save_time = time.time()

            # recalculate story hash
            self._get_story_hash()

            # reset the save timer
            self._save_timer = None

            # reset the dirty flag back to False
            self.set_dirty(False)

        # if we're supposed to call a function when the story is saved
        if save_result and if_successful is not None:

            # call the function
            if_successful()

        # if we're supposed to call a function when the save failed
        elif not save_result and if_failed is not None:
            if_failed()

        return save_result

    def _get_story_hash(self):
        """
        This calculates the hash of a dict version of the story
        (the actual things that are written to the file)
        and then calculates the hash.
        """

        # get the dict version of the story
        story_dict = self.to_dict()

        # calculate the hash (also sort the keys to make sure the hash is consistent)
        self._last_hash = hashlib.md5(json.dumps(story_dict, sort_keys=True).encode('utf-8')).hexdigest()

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
        Then it also sets the dirty flag and saves the story
        """
        self._timeline_fps = timeline_fps
        self._timeline_start_tc = timeline_start_tc

        self._dirty = True
        self.save_soon(sec=0, auxiliaries=False)


class StoryLine:
    """
    This is a class for a line in a story.
    """

    def __init__(self, line_data: dict, parent_story: Story = None):

        # for the line to be valid,
        # it needs to have start and end times
        self._is_valid = False

        self._type = None
        self._text = None
        self._source_start = None
        self._source_end = None
        self._transcription_file_path = None
        self._source_file_path = None
        self._source_fps = None
        self._source_start_tc = None

        self._other_data = {}

        # use this in case we need to communicate with the parent
        self._parent_story = parent_story

        self._load_dict_into_attributes(line_data)

    @property
    def is_valid(self):
        return self._is_valid

    @property
    def parent_story(self):
        return self._parent_story

    @parent_story.setter
    def parent_story(self, value):
        self._parent_story = value

    @property
    def type(self):
        return self._type

    @property
    def text(self):
        return self._text

    @property
    def source_start(self):
        return self._source_start

    @property
    def source_end(self):
        return self._source_end

    @property
    def transcription_file_path(self):
        return self._transcription_file_path

    @property
    def source_file_path(self):
        return self._source_file_path

    @property
    def source_fps(self):
        return self._source_fps

    @property
    def source_start_tc(self):
        return self._source_start_tc

    def __str__(self):
        return self.text

    @property
    def other_data(self):
        return self._other_data

    def set(self, key: str, value):
        """
        We use this to set some of the attributes of the line.
        If the line has a parent, it flags it as dirty.
        """

        allowed_attributes = ['text', 'source_fps', 'source_start_tc', 'transcription_file_path', 'source_file_path',]

        if key in allowed_attributes:
            setattr(self, '_'+key, value)

            # if the line has a parent, flag it as dirty
            if self.parent_story:
                self.parent_story.set_dirty()

            return True

        # throw an error if the key is not valid
        else:
            raise AttributeError('Cannot set the attribute {} for StoryLine, '
                                 'only {} can be set.'.format(key, allowed_attributes))

    def update(self, line_data: dict or object):
        """
        This updates the line with new line_data
        """

        self._load_dict_into_attributes(line_data)

    # set the known attributes
    __known_attributes = ['text', 'type', 'source_start', 'source_end', 'transcription_file_path',
                          'source_file_path', 'source_fps', 'source_start_tc']

    def _load_dict_into_attributes(self, line_dict):

        # we need to make a copy of the line data
        # to make sure that we don't change the original data
        line_dict = copy.deepcopy(line_dict)

        # if the line is not a dictionary, it is not valid
        if not isinstance(line_dict, dict):
            self._is_valid = False

        # set the attributes
        for attribute in self.__known_attributes:

            # if the known attribute is in the json, set the attribute
            if isinstance(line_dict, dict) and attribute in line_dict:

                # convert the start and end times to floats
                if attribute == 'start' or attribute == 'end':
                    line_dict[attribute] = float(line_dict[attribute])

                setattr(self, '_'+attribute, line_dict[attribute])

            # if the known attribute is not in the json,
            # set the attribute to None so we can still access it
            else:
                setattr(self, '_'+attribute, None)

        # other data is everything else
        if line_dict:
            self._other_data = {k: v for k, v in line_dict.items() if k not in self.__known_attributes}
        else:
            self._other_data = {}

        # for a line to be valid,
        # it needs to have text and type
        if self._text is None or self._type is None:
            self._is_valid = False
        else:
            self._is_valid = True

    def to_dict(self):
        """
        This returns the line data as a dict, but it only converts the attributes that are __known_attributes
        """

        # create a copy of the data
        line_dict = dict()

        # add the known attributes to the data
        for attribute in self.__known_attributes:

            if hasattr(self, '_'+attribute) and getattr(self, '_'+attribute) is not None:
                line_dict[attribute] = getattr(self, '_'+attribute)

        # merge the other data with the story data
        line_dict.update(self._other_data)

        return line_dict
    
    def get_index(self):
        """
        This returns the index of the line in the parent story
        """

        # if the line has a parent, return its index
        if self.parent_story:

            # try to see if the line is in the parent's lines list
            try:
                line_index = self.parent_story.lines.index(self)

            # it might be that the object was already cleared from the parent's lines list
            except ValueError:
                line_index = None

            return line_index

        # if the line does not have a parent, return None
        else:
            return None

    def __del__(self):
        """
        This deletes the line from the parent story, if it has one, otherwise it just deletes the line
        """

        # if the line has a parent, remove it from the parent
        if self.parent_story:

            # get the index of the line from the parent's lines list
            line_index = self.get_index()

            # delete the line from the parent
            # (if it still exists in the parent's lines list)
            if line_index is not None:
                self.parent_story.delete_line(line_index)

        # if the line does not have a parent, just delete it
        else:
            del self


class StoryUtils:

    @staticmethod
    def write_to_story_file(story_data, story_file_path, backup=False):

        # if no full path was passed
        if story_file_path is None:
            logger.error('Cannot save story to path "{}".'.format(story_file_path))
            return False

        # if the story file path is a directory
        if os.path.isdir(story_file_path):
            logger.error(
                'Cannot save story - path "{}" is a directory.'.format(story_file_path))
            return False

        # if the directory of the story file path doesn't exist
        if not os.path.exists(os.path.dirname(story_file_path)):
            # create the directory
            logger.debug("Creating directory for story file path: {}")
            try:
                os.makedirs(os.path.dirname(story_file_path))
            except OSError:
                logger.error("Cannot create directory for story file path.", exc_info=True)
                return False
            except:
                logger.error("Cannot create directory for story file path.", exc_info=True)
                return False

        # if backup_original is enabled, it will save a copy of the story file to
        # .backups/[filename].backup.sts, but if backup is an integer, it will only save a backup after [backup] hours
        if backup and os.path.exists(story_file_path):

            # get the backups directory
            backups_dir = os.path.join(os.path.dirname(story_file_path), '.backups')

            # if the backups directory doesn't exist, create it
            if not os.path.exists(backups_dir):
                os.mkdir(backups_dir)

            # format the name of the backup file
            backup_story_file_path = os.path.basename(story_file_path) + '.backup.sts'

            # if another backup file with the same name already exists, add a consecutive number to the end
            backup_n = 0
            while os.path.exists(os.path.join(backups_dir, backup_story_file_path)):

                # get the modified time of the existing backup file
                backup_file_modified_time = os.path.getmtime(
                    os.path.join(backups_dir, backup_story_file_path))

                # if the backup file was modified les than [backup] hours ago, we don't need to save another backup
                if (isinstance(backup, float) or isinstance(backup, int)) \
                        and time.time() - backup_file_modified_time < backup * 60 * 60:
                    backup = False
                    break

                backup_n += 1
                backup_story_file_path = \
                    os.path.basename(story_file_path) + '.backup.{}.sts'.format(backup_n)

            # if the backup setting is still not negative, we should save a backup
            if backup:
                # copy the existing file to the backup
                shutil \
                    .copyfile(story_file_path, os.path.join(backups_dir, backup_story_file_path))

                logger.debug('Copied story file to backup: {}'.format(backup_story_file_path))

        # encode the story json (do this before writing to the file, to make sure it's valid)
        story_json_encoded = json.dumps(story_data, indent=4)

        # write the story json to the file
        with open(story_file_path, 'w', encoding='utf-8') as outfile:
            outfile.write(story_json_encoded)

        logger.debug('Saved story to file: {}'.format(story_file_path))

        return story_file_path

    @staticmethod
    def add_count_to_story_path(story_file_path, target_dir=None):
        """
        This adds a count to the story file path, so that the story file path is unique
        ending either in a file with no number (filename.sts) or a number (filename_2.sts)
        """

        # remove .sts from the end of the path, but don't use replace, it needs to be at the end
        if story_file_path.endswith(".sts"):
            story_file_path_base = story_file_path[:-len(".sts")]
        # otherwise, remove the extension after the last dot using os splitext
        else:
            story_file_path_base = os.path.splitext(story_file_path)[0]

        # if the story_file_path_base contains "_{digits}", remove it
        story_file_path_base = re.sub(r"_[0-9]+$", "", story_file_path_base)

        # use target_dir or don't...
        full_story_file_path = os.path.join(target_dir, story_file_path_base) \
            if target_dir else story_file_path_base

        # add the .sts extension
        full_story_file_path += ".sts"

        count = 2
        while os.path.exists(full_story_file_path):
            # add the count to the story file path
            full_story_file_path = f"{story_file_path_base}_{count}.sts"

            # increment the count
            count += 1

        return full_story_file_path

    @staticmethod
    def write_txt(story_lines: list, txt_file_path: str):
        """
        Write the story lines to a file in TXT format.
        Each segment is written on a new line.
        """

        if not story_lines:
            return

        with open(txt_file_path, "w", encoding="utf-8") as txt_file:
            for line in story_lines:
                # write txt lines
                print(
                    line.text.rstrip('\n'),
                    file=txt_file,
                    flush=True,
                )

    @staticmethod
    def prepare_export(
            story_lines: list, edit_timeline_fps: float = 24,
            edit_timeline_start_tc=None, use_timelines=None, export_blocks=True, export_notes=True,
            add_media_paths=True, join_gaps=None):

        if not story_lines:
            return

        # make sure we're not passing 0 as a timecode (it's not valid)
        if edit_timeline_start_tc == '00:00:00:00':
            edit_timeline_start_tc = None

        edit_timeline_start_tc = Timecode(edit_timeline_fps, start_timecode=edit_timeline_start_tc)

        # the first edit starts at the timeline start timecode
        edit_start_tc = edit_end_tc = edit_timeline_start_tc

        # first process each line
        lines_to_export = []
        last_file_name = None
        last_line_end_tc = None
        files = []
        for line in story_lines:

            # skip if the line is not a transcription segment or video segment
            if line.type != 'transcription_segment' and line.type != 'video_segment':

                if line.type == 'text':

                    # check if the trimmed line starts with [[ and ends with ]]
                    if export_notes and line.text.strip().startswith('[[') and line.text.strip().endswith(']]'):

                        # it means that this is a note line (fountain format)
                        # so consider it as a marker line
                        line_start_tc = edit_start_tc
                        line_end_tc = line_start_tc + 1

                        edit_end_tc = edit_start_tc + 1

                        # append the line to the list
                        lines_to_export.append({
                            'start_tc': line_start_tc,
                            'end_tc': line_end_tc,
                            'edit_start_tc': edit_start_tc,
                            'edit_end_tc': edit_end_tc,
                            'marker': line.text+' |M: Note| D:1'
                        })

                        continue

                last_file_name = None
                last_line_end_tc = None
                continue

            source_fps = line.source_fps if line.source_fps else None
            source_start_tc = line.source_start_tc \
                if line.source_start_tc \
                and line.source_start_tc != '00:00:00:00' else None

            if use_timelines:

                # try to use the transcription timeline name as the file name
                try:
                    source_transcription = Transcription(transcription_file_path=line.transcription_file_path)

                    if source_transcription.timeline_name:
                        file_name = source_transcription.timeline_name

                    else:
                        logger.warning('Cannot use the timeline name for {} - timeline name not set for transcription.'
                                    .format(line.transcription_file_path))
                        file_name = os.path.basename(line.source_file_path)

                except:
                    logger.warning('Cannot use the timeline name for {} - transcription inaccessible.'
                                   .format(line.transcription_file_path))
                    file_name = os.path.basename(line.source_file_path)

            else:
                file_name = os.path.basename(line.source_file_path)

            # we need to have a source fps and a source start tc to be able to export the line
            # but source_start_tc can be None if line.source_start_tc == '00:00:00:00'
            if not source_fps or (not source_start_tc and line.source_start_tc != '00:00:00:00'):
                line_text = line.text if line.text else ''
                logger.warning('Skipping line "{}" because timeline_fps or timeline_start_tc are not set.'
                               .format(' '.join(line_text.split(' ')[:4]) + '...')
                               )
                continue

            # initialize the timeline start tc as a Timecode object
            source_start_tc = Timecode(source_fps, start_timecode=source_start_tc)

            try:
                line_start_tc = Timecode(framerate=source_fps, start_seconds=line.source_start)

            # if the start timecode is not valid, we set it to 00:00:00:00 by not passing a start_seconds
            except ValueError:
                line_start_tc = Timecode(framerate=source_fps)

            try:
                line_end_tc = Timecode(framerate=source_fps, start_seconds=line.source_end)

            # if the end timecode is not valid, we set it to 00:00:00:00
            # this would be very weird though, because it means that the line has no duration
            except ValueError:
                line_end_tc = Timecode(framerate=source_fps)

            # now add the timeline start tc to the media start tc and end tc
            line_start_tc = line_start_tc + source_start_tc
            line_end_tc = line_end_tc + source_start_tc

            # how many frames are between the media start and end?
            if line_start_tc == '00:00:00:00':
                line_duration = line_end_tc.frames

            elif line_end_tc == '00:00:00:00':
                line_duration = 0

            else:
                line_duration = line_end_tc - line_start_tc

            if line_duration == 0:
                logger.warning('Skipping line {} because it contains 0 frames.'.format(line.text))
                continue

            edit_end_tc = edit_start_tc + line_duration

            # we're adding the full path to the media file here if needed
            # but we're also checking if the file exists
            media_file_path = ''
            if add_media_paths:

                # add the media file path to the line
                media_file_path = line.source_file_path

                if not media_file_path:
                    logger.warning('Media file path for {} unknown. Export will not contain file reference.'
                                   .format(line.text))

                elif os.path.isfile(media_file_path):
                    logger.warning('Media file path for {} inaccessible.'
                                   .format(line.text))

            # if the file name and the start timecode of the line are the same as the last line
            # we just update the end timecode of the last line to chunk the lines together
            # also, if join_gaps is set, we join the lines if the gap is less than join_gaps
            if export_blocks and last_file_name == file_name \
                and (last_line_end_tc == line_start_tc or (join_gaps and line_start_tc - last_line_end_tc < join_gaps)):

                # here we need to factor in the gap and add it to the edit_end_tc
                # this will keep an accurate out point for the clip in the timeline
                edit_end_tc = edit_end_tc + (line_start_tc - last_line_end_tc)

                lines_to_export[-1]['end_tc'] = line_end_tc
                lines_to_export[-1]['edit_end_tc'] = edit_end_tc

            # otherwise, add the line to the list
            else:
                lines_to_export.append({
                    'start_tc': line_start_tc,           # this is the in point for the clip
                    'end_tc': line_end_tc,               # this is the out point for the clip
                    'edit_start_tc': edit_start_tc,      # this is the in point in the timeline
                    'edit_end_tc': edit_end_tc,          # this is the out point in the timeline
                    'file_name': file_name,
                    'source_start_tc': source_start_tc,  # this is the start timecode of the source (the offset),
                    'media_file_path': media_file_path,
                })

                # add the source file path to the list of files
                if line.source_file_path and line.source_file_path not in files:
                    files.append(line.source_file_path)

            # remember the filename and the start timecode of the last line
            last_file_name = file_name
            last_line_end_tc = line_end_tc

            # the next edit starts where the previous edit ended
            edit_start_tc = edit_end_tc

        return lines_to_export, files, edit_timeline_start_tc, edit_end_tc

    @classmethod
    def write_edl(cls, story_name: str, story_lines: list, edl_file_path: str,
                  edit_timeline_fps: float = 24, edit_timeline_start_tc=None, use_timelines=None,
                  export_blocks=True, export_notes=True, join_gaps=None):
        """
        Write the story lines to a file in EDL format.
        """

        ###
        # This is an example of an EDL file:
        # TITLE: AT 04 Workshop Conversation
        # FCM: NON-DROP FRAME
        #
        # 001  AX       V     C        11:40:39:07 12:04:09:00 01:00:00:00 01:23:29:17
        # * FROM CLIP NAME: C001_08241140_C001.braw
        #
        # 002  AX       A     C        11:40:39:07 12:04:09:00 01:00:00:00 01:23:29:17
        # * FROM CLIP NAME: C001_08241140_C001.braw
        #
        # Segment 1:
        # - Video source identified as "AX" - i.e. Auxiliary source
        # - Type of source is "Video" (V)
        # - Type of transition is "Cut" (C)
        # - The source clip starts at "11:40:39:07" and ends at "12:04:09:00"
        # - In the edited sequence, it will appear starting at "01:00:00:00" and ending at "01:23:29:17"
        # - The name of the video clip being used is "C001_08241140_C001.braw"
        #
        # Segment 2:
        # - Audio source identified as "AX" - i.e. Auxiliary source
        # - Type of source is "Audio" (A)
        # - Type of transition is "Cut" (C)
        # - The same details for source start time, end time, and the time frame in the final sequence apply.
        # - The same video clip "C001_08241140_C001.braw" is used for audio as well.
        #
        #
        # In simple terms, it's detailing that the video and audio from clip "C001_08241140_C001.braw"
        # starting from "11:40:39:07" to "12:04:09:00"
        # will be used in the final video sequence from "01:00:00:00" to "01:23:29:17".
        # The "V" indicates a video track and "A" indicates an audio track.
        # - these can also be V2, A2 etc. depending on which track they are on.
        # The "C" stands for "Cut," the type of transition between clips.

        lines_to_export, _, _, _ = cls.prepare_export(
                                    story_lines=story_lines,
                                    edit_timeline_fps=edit_timeline_fps,
                                    edit_timeline_start_tc=edit_timeline_start_tc,
                                    use_timelines=use_timelines,
                                    export_blocks=export_blocks,
                                    export_notes=export_notes,
                                    join_gaps=join_gaps
                                )

        if not lines_to_export:
            logger.warning('Aborting. No lines to export.')
            return None

        with open(edl_file_path, "w", encoding="utf-8") as edl_file_path:

            # first write the header
            edl_file_path.write("TITLE: {}\n".format(story_name))

            # is this drop frame or non-drop frame?
            if float(edit_timeline_fps) == 29.97 or float(edit_timeline_fps) == 59.94:
                edl_file_path.write("FCM: DROP FRAME\n\n")

            else:
                edl_file_path.write("FCM: NON-DROP FRAME\n\n")

            edit_count = 1
            for line in lines_to_export:

                file_name = line.get('file_name', '')

                # if the file doesn't end with .wav, .mp3 or .aac, it's not just an audio file
                # - so we add the video portion of the edit too
                if file_name \
                    and not file_name.endswith('.wav') \
                    and not file_name.endswith('.mp3') \
                    and not file_name.endswith('.aac'):

                    # 001  AX       V     C        00:00:35:17 00:30:16:02 01:00:00:00 01:00:20:09
                    # * FROM CLIP NAME: C001_08241140_C001.braw
                    #

                    # write the edit line for the video portion
                    edl_file_path.write("{:03d}  AX       V     C        {} {} {} {}\n".format(
                        edit_count,
                        line['start_tc'],
                        line['end_tc'],
                        line['edit_start_tc'],
                        line['edit_end_tc'],
                    ))

                    # write the source file name
                    edl_file_path.write("* FROM CLIP NAME: {}\n\n".format(line['file_name']))

                    edit_count += 1

                if file_name:

                    # 002  AX       A     C        00:00:35:17 00:30:16:02 01:00:00:00 01:00:20:09
                    # * FROM CLIP NAME: C001_08241140_C001.braw

                    # write the edit line for the audio portion
                    edl_file_path.write("{:03d}  AX       A     C        {} {} {} {}\n".format(
                        edit_count,
                        line['start_tc'],
                        line['end_tc'],
                        line['edit_start_tc'],
                        line['edit_end_tc'],
                    ))

                    # write the source file name
                    edl_file_path.write("* FROM CLIP NAME: {}\n\n".format(line['file_name']))

                elif 'marker' in line:
                    edl_file_path.write("{:03d}  AX       V     C        {} {} {} {}\n".format(
                        edit_count,
                        line['start_tc'],
                        line['end_tc'],
                        line['edit_start_tc'],
                        line['edit_end_tc'],
                    ))
                    edl_file_path.write(line.get('text', '') + line.get('marker'))
                    edl_file_path.write('\n\n')

                # increment the edit count
                edit_count += 1

        return edl_file_path

    @classmethod
    def write_fcp7xml(cls, story_name: str, story_lines: list, xml_file_path: str,
                  edit_timeline_fps: float = 24, edit_timeline_start_tc=None, use_timelines=None,
                  export_blocks=True, export_notes=True, join_gaps=None):
        """
        Write the story lines to a file in FCP7XML format.
        Reference: https://developer.apple.com/library/archive/documentation/AppleApplications/Reference/FinalCutPro_XML/Basics/Basics.html#//apple_ref/doc/uid/TP30001154-DontLinkElementID_63
        """

        lines_to_export, files, edit_start_tc, edit_end_tc = cls.prepare_export(
                                                                story_lines=story_lines,
                                                                edit_timeline_fps=edit_timeline_fps,
                                                                edit_timeline_start_tc=edit_timeline_start_tc,
                                                                use_timelines=use_timelines,
                                                                export_blocks=export_blocks,
                                                                export_notes=export_notes,
                                                                add_media_paths=True,
                                                                join_gaps=join_gaps
                                                            )

        if not lines_to_export:
            logger.warning('Aborting. No lines to export.')
            return None

        # we use this to increment the clip id depending on how many times a file is used
        file_unique_ids = {}

        # make sure that the edit_timeline_start_tc is a Timecode object for calculations
        edit_timeline_start_tc = Timecode(
            framerate=edit_timeline_fps,
            start_timecode=edit_timeline_start_tc if edit_timeline_start_tc != '00:00:00:00' else None
        )

        # pre-process each line
        for line in lines_to_export:

            # skip non-file lines
            if 'file_name' not in line:
                continue

            # FIRST,
            # assign unique ids to each clip item (both for video and audio)
            # this will be useful when we want to link them in the XML instructions using <linkclipref>

            # get the current unique id for the file
            file_unique_id = file_unique_ids.get(line['file_name'], 0)

            # set the unique id for the file
            line['file_unique_id'] = "{} {}".format(line['file_name'], file_unique_id)

            # increment the unique id
            file_unique_id += 1

            # set the unique id for the file on this cut (video part)
            line['video_clip_unique_id'] = "{} {}".format(line['file_name'], file_unique_id)

            # increment the unique id
            file_unique_id += 1

            # set the unique id for the file on this cut (audio part)
            line['audio_clip_unique_id'] = "{} {}".format(line['file_name'], file_unique_id)

            # increment the unique id
            file_unique_id += 1

            # save the unique id for the file for later use
            file_unique_ids[line['file_name']] = file_unique_id

            # increment the unique id
            file_unique_id += 1

            # get the framerate from the start timecode
            source_fps = line['start_tc'].framerate

            # subtract the start timecodes for start_tc and end_tc to respect XML formatting
            try:
                line['start_tc'] = line['start_tc'] - line['source_start_tc']
                line['start_frame'] = line['start_tc'].frames
            except ValueError:
                line['start_tc'] = Timecode(framerate=source_fps)
                line['start_frame'] = 0

            try:
                line['end_tc'] = line['end_tc'] - line['source_start_tc']
                line['end_frame'] = line['end_tc'].frames
            except ValueError:
                line['end_tc'] = Timecode(framerate=source_fps)
                line['end_frame'] = 0

            # also subtract the timeline start timecode for edit_start_tc and edit_end_tc
            try:
                line['edit_start_tc'] = line['edit_start_tc'] - edit_timeline_start_tc
                line['edit_start_frame'] = line['edit_start_tc'].frames
            except ValueError:
                line['edit_start_tc'] = Timecode(framerate=edit_timeline_fps)
                line['edit_start_frame'] = 0

            try:
                line['edit_end_tc'] = line['edit_end_tc'] - edit_timeline_start_tc
                line['edit_end_frame'] = line['edit_end_tc'].frames
            except ValueError:
                line['edit_end_tc'] = Timecode(framerate=edit_timeline_fps)
                line['edit_end_frame'] = 0

            # re-calculate the timebase and ntsc flags
            #  should 23.976 also the case? float(source_fps) == 23.976
            if float(source_fps) == 29.97 or float(source_fps) == 59.94:

                # set the ntsc flag to true
                line['ntsc'] = 'TRUE'

                # we round up the source fps to the nearest integer according to the FCP7XML standard
                # which specifies that each program should deal with the maths in its own way
                line['timebase'] = int(round(float(source_fps)))

            else:
                line['ntsc'] = 'FALSE'
                line['timebase'] = int(round(float(source_fps)))

            # open the file using Media object
            media = MediaItem(line['media_file_path'])

            try:
                duration_sec = media.get_duration()
            except IOError:
                logger.error('The line is not being exported correctly. Cannot get duration for {}'
                             .format(line['media_file_path']))
                duration_sec = 0

            if not duration_sec:
                logger.error('The line is not being exported correctly. Cannot get duration for {}'
                             .format(line['media_file_path']))

                line['total_duration'] = 0

            else:
                # calculate the total duration of the clip depending on the timebase set above
                line['total_duration'] = duration_sec*line['timebase']

        with open(xml_file_path, "w", encoding="utf-8") as xml_file_path:

            timeline_duration = edit_end_tc - edit_start_tc
            timeline_duration_frames = timeline_duration.frames

            drop_frame = 'DF' \
                if edit_timeline_fps == 29.97 or edit_timeline_fps == 59.94 else 'NDF'

            # write the header
            xml_file_path.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            xml_file_path.write('<!DOCTYPE xmeml>\n')
            xml_file_path.write('<xmeml version="5">\n')
            xml_file_path.write('\t<sequence>\n')
            xml_file_path.write('\t\t<name>{}</name>\n'.format(story_name))
            xml_file_path.write('\t\t<duration>{}</duration>\n'.format(timeline_duration_frames))
            xml_file_path.write('\t\t<rate>\n')
            xml_file_path.write('\t\t\t<timebase>{}</timebase>\n'.format(edit_timeline_fps))
            xml_file_path.write('\t\t\t<ntsc>FALSE</ntsc>\n')
            xml_file_path.write('\t\t</rate>\n')
            xml_file_path.write('\t\t<in>-1</in>\n')
            xml_file_path.write('\t\t<out>-1</out>\n')
            xml_file_path.write('\t\t<timecode>\n')
            xml_file_path.write('\t\t\t<string>{}</string>\n'.format(edit_timeline_start_tc))
            xml_file_path.write('\t\t\t<frame>{}</frame>\n'.format(edit_start_tc.frames))
            xml_file_path.write('\t\t\t<displayformat>{}</displayformat>\n'.format(drop_frame))
            xml_file_path.write('\t\t\t<rate>\n')
            xml_file_path.write('\t\t\t\t<timebase>{}</timebase>\n'.format(edit_timeline_fps))
            xml_file_path.write('\t\t\t\t<ntsc>FALSE</ntsc>\n')
            xml_file_path.write('\t\t\t</rate>\n')
            xml_file_path.write('\t\t</timecode>\n')
            xml_file_path.write('\t\t<media>\n')

            # write the video track
            xml_file_path.write('\t\t\t<video>\n')

            # THE VIDEO TRACK
            # create the track and add the video clips for the video track
            xml_file_path.write('\t\t\t\t<track>\n')

            for line in lines_to_export:

                # if the line has a file name, it's not a clip worth adding
                if not 'file_name' in line:
                    continue

                # if the file name doesn't end with .wav, .mp3 or .aac, it's not just an audio file
                # so we add the video portion of the edit too
                if not line['file_name'].endswith('.wav') \
                    and not line['file_name'].endswith('.mp3') \
                    and not line['file_name'].endswith('.aac'):

                    # note:
                    # in out refers to the in and out points of the clip
                    # start end refers to the in and out points of the clip in the timeline

                    xml_file_path.write('\t\t\t\t\t<clipitem id="{}">\n'.format(line['video_clip_unique_id']))
                    xml_file_path.write('\t\t\t\t\t\t<name>{}</name>\n'.format(line['file_name']))
                    xml_file_path.write('\t\t\t\t\t\t<duration>{}</duration>\n'.format(line['total_duration']))
                    xml_file_path.write('\t\t\t\t\t\t<rate>\n')
                    xml_file_path.write('\t\t\t\t\t\t\t<timebase>{}</timebase>\n'.format(line['timebase']))
                    xml_file_path.write('\t\t\t\t\t\t\t<ntsc>{}</ntsc>\n'.format(line['ntsc']))
                    xml_file_path.write('\t\t\t\t\t\t</rate>\n')
                    xml_file_path.write('\t\t\t\t\t\t<start>{}</start>\n'.format(line['edit_start_frame']))
                    xml_file_path.write('\t\t\t\t\t\t<end>{}</end>\n'.format(line['edit_end_frame']))
                    xml_file_path.write('\t\t\t\t\t\t<enabled>TRUE</enabled>\n')
                    xml_file_path.write('\t\t\t\t\t\t<in>{}</in>\n'.format(line['start_frame']))
                    xml_file_path.write('\t\t\t\t\t\t<out>{}</out>\n'.format(line['end_frame']))

                    # THE FILE REFERENCE
                    if 'file_referenced' not in line:
                        xml_file_path.write('\t\t\t\t\t\t<file id="{}" >\n'.format(line['file_unique_id']))
                        xml_file_path.write('\t\t\t\t\t\t\t<duration>{}</duration>\n'.format(line['total_duration']))
                        xml_file_path.write('\t\t\t\t\t\t\t<rate>\n')
                        xml_file_path.write('\t\t\t\t\t\t\t\t<timebase>{}</timebase>\n'.format(line['timebase']))
                        xml_file_path.write('\t\t\t\t\t\t\t\t<ntsc>{}</ntsc>\n'.format(line['ntsc']))
                        xml_file_path.write('\t\t\t\t\t\t\t</rate>\n')
                        xml_file_path.write('\t\t\t\t\t\t\t<name>{}</name>\n'.format(line['file_name']))
                        xml_file_path.write('\t\t\t\t\t\t\t<pathurl>file://{}</pathurl>\n'
                                            .format(line['media_file_path']))
                        xml_file_path.write('\t\t\t\t\t\t\t<timecode>\n')
                        xml_file_path.write('\t\t\t\t\t\t\t\t<string>{}</string>\n'.format(line['source_start_tc']))
                        xml_file_path.write('\t\t\t\t\t\t\t\t<displayformat>{}</displayformat>\n'
                                            .format('NDF' if line['ntsc'] == 'FALSE' else 'DF'))
                        xml_file_path.write('\t\t\t\t\t\t\t\t<rate>\n')
                        xml_file_path.write('\t\t\t\t\t\t\t\t\t<timebase>{}</timebase>\n'.format(line['timebase']))
                        xml_file_path.write('\t\t\t\t\t\t\t\t\t<ntsc>{}</ntsc>\n'.format(line['ntsc']))
                        xml_file_path.write('\t\t\t\t\t\t\t\t</rate>\n')
                        xml_file_path.write('\t\t\t\t\t\t\t</timecode>\n')
                        xml_file_path.write('\t\t\t\t\t\t</file>\n')

                        line['file_referenced'] = True

                    else:
                        xml_file_path.write('\t\t\t\t\t\t<file id="{}" />\n'.format(line['file_unique_id']))

                    # add the two <linkclipref> tags that connects the audio and video clips
                    xml_file_path.write('\t\t\t\t\t\t<link>\n')
                    xml_file_path.write('\t\t\t\t\t\t\t<linkclipref>{}</linkclipref>\n'.format(line['video_clip_unique_id']))
                    xml_file_path.write('\t\t\t\t\t\t</link>\n')
                    xml_file_path.write('\t\t\t\t\t\t<link>\n')
                    xml_file_path.write('\t\t\t\t\t\t\t<linkclipref>{}</linkclipref>\n'.format(line['audio_clip_unique_id']))
                    xml_file_path.write('\t\t\t\t\t\t</link>\n')

                    xml_file_path.write('\t\t\t\t\t</clipitem>\n')

                    line['has_video'] = True

            xml_file_path.write('\t\t\t\t\t<enabled>TRUE</enabled>\n')
            xml_file_path.write('\t\t\t\t\t<locked>FALSE</locked>\n')
            xml_file_path.write('\t\t\t\t</track>\n')

            xml_file_path.write('\t\t\t\t<format>\n')
            xml_file_path.write('\t\t\t\t\t<samplecharacteristics>\n')
            xml_file_path.write('\t\t\t\t\t\t<width>1920</width>\n')
            xml_file_path.write('\t\t\t\t\t\t<height>1080</height>\n')
            xml_file_path.write('\t\t\t\t\t\t<pixelaspectratio>square</pixelaspectratio>\n')
            xml_file_path.write('\t\t\t\t\t\t<rate>\n')
            xml_file_path.write('\t\t\t\t\t\t\t<timebase>{}</timebase>\n'.format(round(float(edit_timeline_fps))))
            xml_file_path.write('\t\t\t\t\t\t\t<ntsc>{}</ntsc>\n'.format('TRUE' if drop_frame == 'DF' else 'FALSE'))
            xml_file_path.write('\t\t\t\t\t\t</rate>\n')
            xml_file_path.write('\t\t\t\t\t\t<codec>\n')
            xml_file_path.write('\t\t\t\t\t\t\t<appspecificdata>\n')
            xml_file_path.write('\t\t\t\t\t\t\t\t<appname>Final Cut Pro</appname>\n')
            xml_file_path.write('\t\t\t\t\t\t\t\t<appmanufacturer>Apple Inc.</appmanufacturer>\n')
            xml_file_path.write('\t\t\t\t\t\t\t\t<data>\n')
            xml_file_path.write('\t\t\t\t\t\t\t\t\t<qtcodec/>\n')
            xml_file_path.write('\t\t\t\t\t\t\t\t</data>\n')
            xml_file_path.write('\t\t\t\t\t\t\t</appspecificdata>\n')
            xml_file_path.write('\t\t\t\t\t\t</codec>\n')
            xml_file_path.write('\t\t\t\t\t</samplecharacteristics>\n')
            xml_file_path.write('\t\t\t\t</format>\n')

            xml_file_path.write('\t\t\t</video>\n')

            # THE AUDIO TRACK
            # create the track and add the audio clips for the audio track
            xml_file_path.write('\t\t\t<audio>\n')
            xml_file_path.write('\t\t\t\t<track>\n')

            for line in lines_to_export:

                if not 'file_name' in line:
                    continue

                xml_file_path.write('\t\t\t\t\t<clipitem id="{}">\n'.format(line['audio_clip_unique_id']))
                xml_file_path.write('\t\t\t\t\t\t<name>{}</name>\n'.format(line['file_name']))
                xml_file_path.write('\t\t\t\t\t\t<duration>{}</duration>\n'.format(line['total_duration']))
                xml_file_path.write('\t\t\t\t\t\t<rate>\n')
                xml_file_path.write('\t\t\t\t\t\t\t<timebase>{}</timebase>\n'.format(line['timebase']))
                xml_file_path.write('\t\t\t\t\t\t\t<ntsc>{}</ntsc>\n'.format(line['ntsc']))
                xml_file_path.write('\t\t\t\t\t\t</rate>\n')
                xml_file_path.write('\t\t\t\t\t\t<start>{}</start>\n'.format(line['edit_start_frame']))
                xml_file_path.write('\t\t\t\t\t\t<end>{}</end>\n'.format(line['edit_end_frame']))
                xml_file_path.write('\t\t\t\t\t\t<in>{}</in>\n'.format(line['start_frame']))
                xml_file_path.write('\t\t\t\t\t\t<out>{}</out>\n'.format(line['end_frame']))
                xml_file_path.write('\t\t\t\t\t\t<enabled>TRUE</enabled>\n')

                # THE FILE REFERENCE
                # THE FILE REFERENCE
                if 'file_referenced' not in line:
                    xml_file_path.write('\t\t\t\t\t\t<file id="{}" >\n'.format(line['file_unique_id']))
                    xml_file_path.write('\t\t\t\t\t\t\t<duration>{}</duration>\n'.format(line['total_duration']))
                    xml_file_path.write('\t\t\t\t\t\t\t<rate>\n')
                    xml_file_path.write('\t\t\t\t\t\t\t\t<timebase>{}</timebase>\n'.format(line['timebase']))
                    xml_file_path.write('\t\t\t\t\t\t\t\t<ntsc>{}</ntsc>\n'.format(line['ntsc']))
                    xml_file_path.write('\t\t\t\t\t\t\t</rate>\n')
                    xml_file_path.write('\t\t\t\t\t\t\t<name>{}</name>\n'.format(line['file_name']))
                    xml_file_path.write('\t\t\t\t\t\t\t<pathurl>file://{}</pathurl>\n'.format(line['media_file_path']))
                    xml_file_path.write('\t\t\t\t\t\t\t<timecode>\n')
                    xml_file_path.write('\t\t\t\t\t\t\t\t<string>{}</string>\n'.format(line['source_start_tc']))
                    xml_file_path.write('\t\t\t\t\t\t\t\t<displayformat>{}</displayformat>\n'
                                        .format('NDF' if line['ntsc'] == 'FALSE' else 'DF'))
                    xml_file_path.write('\t\t\t\t\t\t\t\t<rate>\n')
                    xml_file_path.write('\t\t\t\t\t\t\t\t\t<timebase>{}</timebase>\n'.format(line['timebase']))
                    xml_file_path.write('\t\t\t\t\t\t\t\t\t<ntsc>{}</ntsc>\n'.format(line['ntsc']))
                    xml_file_path.write('\t\t\t\t\t\t\t\t</rate>\n')
                    xml_file_path.write('\t\t\t\t\t\t\t</timecode>\n')
                    xml_file_path.write('\t\t\t\t\t\t</file>\n')

                    line['file_referenced'] = True

                else:
                    xml_file_path.write('\t\t\t\t\t\t<file id="{}" />\n'.format(line['file_unique_id']))

                # other audio stuff
                xml_file_path.write('\t\t\t\t\t\t<sourcetrack>\n')
                xml_file_path.write('\t\t\t\t\t\t\t<mediatype>audio</mediatype>\n')
                xml_file_path.write('\t\t\t\t\t\t\t<trackindex>1</trackindex>\n')
                xml_file_path.write('\t\t\t\t\t\t</sourcetrack>\n')

                # only add link if there actually is a video part to this (same above)
                if 'has_video' in line:

                    xml_file_path.write('\t\t\t\t\t\t<link>\n')
                    xml_file_path.write('\t\t\t\t\t\t\t<linkclipref>{}</linkclipref>\n'.format(line['video_clip_unique_id']))
                    xml_file_path.write('\t\t\t\t\t\t\t<mediatype>video</mediatype>\n')
                    xml_file_path.write('\t\t\t\t\t\t</link>\n')
                    xml_file_path.write('\t\t\t\t\t\t<link>\n')
                    xml_file_path.write('\t\t\t\t\t\t\t<linkclipref>{}</linkclipref>\n'.format(line['audio_clip_unique_id']))
                    xml_file_path.write('\t\t\t\t\t\t</link>\n')

                xml_file_path.write('\t\t\t\t\t</clipitem>\n')

            xml_file_path.write('\t\t\t\t\t<enabled>TRUE</enabled>\n')
            xml_file_path.write('\t\t\t\t\t<locked>FALSE</locked>\n')
            xml_file_path.write('\t\t\t\t</track>\n')
            xml_file_path.write('\t\t\t</audio>\n')

            # write the end of the file (closing tags)
            xml_file_path.write('\t\t</media>\n')
            xml_file_path.write('\t</sequence>\n')
            xml_file_path.write('</xmeml>\n')

            return xml_file_path
