import os
import codecs
import json
import copy
import time
import shutil
import hashlib

from threading import Timer

from storytoolkitai import USER_DATA_PATH
from storytoolkitai.core.logger import logger

PROJECTS_PATH = os.path.join(os.path.join(USER_DATA_PATH, 'projects'))


class Project:

    _instances = {}

    def __new__(cls, **kwargs):
        """
        This checks if the current project file path isn't already loaded in an instance
        and returns that instance if it is.
        """

        project_path = kwargs.get('project_path', None)

        # if project_path is None and project_name is not None:
        if project_path is None and kwargs.get('project_name', None) is not None:
            project_path = os.path.join(PROJECTS_PATH, kwargs.get('project_name'))

        if project_path is None:
            raise ValueError('Project path or name must be passed to initialize a project.')

        # we use the project path as the id for the instance
        project_path_id = cls.get_project_path_id(
            project_path=kwargs.get('project_path', None) or project_path
        )

        # if we're supposed to force a reload, we delete the instance if it exists
        if kwargs.get('force_reload', False) and project_path_id in cls._instances:
            del cls._instances[project_path_id]

        # if the project path is already loaded in an instance, we return that instance
        if project_path_id in cls._instances:
            return cls._instances[project_path_id]

        # otherwise we create a new instance
        instance = super().__new__(cls)

        # and we store it in the instances dict
        cls._instances[project_path_id] = instance

        # then we return the instance
        return instance

    def __init__(self, *, project_path=None, project_name=None, force_reload=False):

        # prevent initializing the instance more than once if it was found in the instances dict
        # but only if we're not supposed to force a reload
        if hasattr(self, '_initialized') and self._initialized and not force_reload:
            return

        # if we don't have a project path, use the project name to create one
        if project_path is None and project_name is not None:
            project_path = os.path.join(PROJECTS_PATH, project_name)

        elif project_path is None and project_name is None:
            raise ValueError('Project path or name must be passed to initialize a project.')

        # the project path must be a directory
        self._project_path = project_path

        self._name = None
        self._last_target_dir = None

        self._timelines = {}

        # we use this to keep track if we updated, deleted, added, or changed anything
        self._dirty = False

        # this is used to keep track of the last time the project was saved
        self._last_save_time = None

        # if the load was unsuccessful, we mark the project as dirty so that it will be saved
        if not self.load_from_path(project_path=self._project_path):
            self._dirty = True

        # with this we can set a timer to save the project after a certain amount of time
        # this way, we don't create another timer if one is already running and the save_soon method is called again
        self._save_timer = None

        # if we're saving very often, we can throttle the save timer
        # the throttle is a ratio used to multiply the save timer interval
        # the more often we save, the longer the interval between saves
        # but then this is reset to 1 when we're not saving often
        self._save_timer_throttle = 1

        # add this to know that we already initialized this instance
        self._initialized = True

    @property
    def project_path(self):
        return self._project_path

    @property
    def name(self):
        return self._name

    @property
    def last_target_dir(self):
        return self._last_target_dir

    @property
    def timelines(self):
        return self._timelines

    @property
    def is_dirty(self):
        return self._dirty

    def set_dirty(self, value=True, *, save_soon=False):
        """
        This sets the dirty flag to True, which means that the project needs to be saved.
        If save_soon is True, it will also save the project soon.
        """

        self._dirty = value

        if save_soon:
            self.save_soon()

    __known_attributes = ['name', 'last_target_dir', 'timelines']

    def set(self, key: str or dict, value=None, save_soon=False):
        """
        We use this to set some of the attributes of the transcription.
        If the attribute was changed, we set the dirty flag to true.
        """

        # if we're setting a dictionary of attributes
        if isinstance(key, dict):

            # we iterate through the dictionary
            for k, v in key.items():

                # and set each attribute
                self.set(k, v)

            return True

        # if the key is a string and is allowed, do this:
        if key in self.__known_attributes:

            # if the attribute is different from the current value
            if getattr(self, '_' + key) != value:

                # set the attribute
                setattr(self, '_' + key, value)

                # set the dirty flag
                self.set_dirty(save_soon=save_soon)

            return True

        # throw an error if the key is not valid
        else:
            raise AttributeError('Cannot set the attribute {} for Transcription, '
                                 'only {} can be set.'.format(key, self.__known_attributes))

    def load_from_path(self, project_path):
        """
        This loads a project from a project folder
        """

        # for a project path to be valid, it must be a directory and have a project.json file in it
        if not os.path.isdir(project_path):
            logger.debug("Project path {} is not a directory".format(project_path))
            return False

        project_json_path = os.path.join(project_path, 'project.json')
        if not os.path.isfile(project_json_path):
            logger.debug("Project file {} does not exist".format(project_json_path))
            return False

        logger.debug("Loading project from {}".format(project_path))

        self._project_path = project_path

        # load the json found in the file into attributes
        self._load_json_into_attributes()

    def _load_json_into_attributes(self):

        project_json_path = os.path.join(self._project_path, 'project.json')

        try:
            with codecs.open(project_json_path, 'r', 'utf-8-sig') as json_file:
                self._data = json.load(json_file)

                # let's make a deep copy of the data
                # so that we can manipulate it without changing the original data
                self._data = copy.deepcopy(self._data)

        # in case we get JSONDecodeError, we assume that the file is not a valid JSON file
        except json.decoder.JSONDecodeError:
            logger.error("Project file {} is invalid".format(project_json_path))
            self._data = {}

        # if we have a file that is not a valid JSON file, we assume that it is not a project file
        except Exception as e:
            logger.error("Project file {} is invalid\n{}".format(project_json_path, str(e)))
            self._data = {}

        # if we have a valid JSON file, we assume that it is a project file
        # so load all the known attributes into the object
        for attribute in self.__known_attributes:

            # if the attribute is in the data, set the attribute
            if attribute in self._data:
                setattr(self, '_{}'.format(attribute), self._data[attribute])

            # if the attribute is not in the data, set the attribute to None
            else:
                setattr(self, '_{}'.format(attribute), None)

    def to_dict(self):
        """
        This returns the project attributes as a dict, but only if they are in the __known_attributes list
        """

        # create a copy of the data
        project_dict = dict()

        # add the known attributes to the data
        for attribute in self.__known_attributes:

            # if the attribute is set, add it to the dict
            if hasattr(self, '_'+attribute) and getattr(self, '_'+attribute) is not None:
                project_dict[attribute] = getattr(self, '_'+attribute)

        return project_dict

    def save_soon(self, force=False, backup: bool or float = False, sec=3, **kwargs):
        """
        This saves the project to the project file, while keeping track of the last time it was saved,
        and only saving if it's been a while since the last save
        :param force: bool, whether to force save the project even if it's not dirty
        :param backup: bool, whether to back up the project file before saving, if an integer is passed,
                             it will be used to determine the time in hours between backups
        :param sec: int, how soon in seconds to save the project, if 0, save immediately
                    (0 seconds also means waiting for the execution to finish before returning from the function)
        """

        # if the transcription is not dirty
        # or if this is not a forced save
        # don't save it
        if not self.is_dirty and not force:
            logger.debug("Project is unchanged. Not saving.")
            return False

        # if there's no waiting time set, save immediately
        if sec == 0:

            # but first cancel the save timer if it's running
            if self._save_timer is not None:
                self._save_timer.cancel()
                self._save_timer = None

            return self._save(backup=backup)

        # if we're calling this function again before the last save was done
        # it means that we're calling this function more often so many changes might follow in our Project,
        # so throttle the save timer for the next time to increase the time between saves
        # also, because the last save didn't execute, we don't have to start another save timer
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
              if_successful: callable = None, if_failed: callable = None, **kwargs):
        """
        This saves the project to the project.json file
        :param backup: bool, whether to back up the project file before saving, if an integer is passed,
                                it will be used to determine the time in hours between backups
        :param auxiliaries: bool, whether to save the auxiliaries
        :param if_successful: callable, a function to call if the project was saved successfully
        :param if_failed: callable, a function to call if the project failed to save
        :param if_none: callable, a function to call if the project was not saved because it was not dirty
        """

        # create the project data dict
        project_data = self.to_dict()

        # use the project utils function to write the project to the file
        save_result = ProjectUtils.write_to_project_file(
            project_data=project_data,
            project_path=self._project_path,
            backup=backup
        )

        # set the exists flag to True
        self._exists = True

        if save_result:
            # set the last save time
            self._last_save_time = time.time()

            # reset the save timer
            self._save_timer = None

            # reset the dirty flag back to False
            self.set_dirty(False)

        # if we're supposed to call a function when the project is saved
        if save_result and if_successful is not None:
            logger.debug('Project "{}" saved successfully.'.format(self._project_path))

            # call the function
            if_successful()

        # if we're supposed to call a function when the save failed
        elif not save_result and if_failed is not None:
            logger.debug('Project "{}" failed to save.'.format(self._project_path))
            if_failed()

        return save_result

    @staticmethod
    def get_project_path_id(project_path):
        return hashlib.md5(project_path.encode('utf-8')).hexdigest()

    def get_timeline_setting(self, timeline_name: str, setting_key: str):
        """
        This gets a specific timeline setting from the project.json by looking into the timelines dictionary
        :param timeline_name:
        :param setting_key:
        :return:
        """

        if timeline_name is None or not isinstance(timeline_name, str):
            logger.debug('Cannot get setting "{}" for timeline "{}".'.format(setting_key, timeline_name))
            return None

        if setting_key is None or not isinstance(setting_key, str):
            logger.debug('Cannot get setting "{}" for timeline "{}".'.format(setting_key, timeline_name))

        # does this project have timelines?
        # is there a reference regarding the passed timeline?
        # is there a reference regarding the passed setting key?
        if self.timelines and timeline_name in self.timelines:

            # then return the setting value
            return self.timelines[timeline_name].get(setting_key, None)

        # if the setting key, or any of the stuff above wasn't found
        return None

    def get_timeline_transcriptions(self, timeline_name):
        """
        This gets the all the transcriptions linked to a timeline
        :param timeline_name:
        :return:
        """

        return self.get_timeline_setting(timeline_name=timeline_name, setting_key='transcription_files')

    def is_transcription_linked_to_timeline(self, transcription_file_path, timeline_name):
        """
        This checks if a transcription is linked to a timeline
        :param transcription_file_path:
        :param timeline_name:
        :return:
        """

        transcription_files = self.get_timeline_setting(timeline_name=timeline_name, setting_key='transcription_files')

        if transcription_files is None:
            return False

        return transcription_file_path in transcription_files

    def link_transcription_to_timeline(self, transcription_file_path: str, timeline_name: str, save_soon=False):
        """
        This links a transcription to a timeline
        """

        if transcription_file_path is None or not isinstance(transcription_file_path, str)\
                or timeline_name is None or not isinstance(timeline_name, str):
            logger.debug('Cannot link transcription {} to timeline {}.'
                         .format(transcription_file_path, timeline_name))
            return False

        if self.timelines is None:
            self._timelines = {}

        if timeline_name not in self.timelines:
            self._timelines[timeline_name] = {}

        if 'transcription_files' not in self.timelines[timeline_name]:
            self._timelines[timeline_name]['transcription_files'] = []

        if transcription_file_path not in self.timelines[timeline_name]['transcription_files']:
            self._timelines[timeline_name]['transcription_files'].append(transcription_file_path)

        self.set_dirty(save_soon=save_soon)

        return True

    def unlink_transcription_from_timeline(self, transcription_file_path: str, timeline_name: str, save_soon=False):
        """
        This unlinks a transcription from a timeline
        """

        if transcription_file_path is None or not isinstance(transcription_file_path, str)\
                or timeline_name is None or not isinstance(timeline_name, str):
            logger.debug('Cannot link transcription {} to timeline {}.'
                         .format(transcription_file_path, timeline_name))
            return False

        if timeline_name not in self.timelines:
            return False

        if 'transcription_files' not in self.timelines[timeline_name]:
            return False

        if transcription_file_path not in self.timelines[timeline_name]['transcription_files']:
            return False

        self.timelines[timeline_name]['transcription_files'].remove(transcription_file_path)

        self.set_dirty(save_soon=save_soon)

        return True

    def set_timeline_markers(self, timeline_name, markers, save_soon=False) -> bool:
        """
        This sets the markers for a timeline
        :param timeline_name: str, the name of the timeline
        :param markers: list, a list of markers, if None, the markers will be removed
        :param save_soon: bool, whether to save the project to file
        :return:
        """

        if timeline_name is None:
            logger.debug('Cannot set markers for timeline "{}".'.format(timeline_name))
            return False

        if self.timelines is None:
            self._timelines = {}

        if timeline_name not in self.timelines:
            self._timelines[timeline_name] = {}

        # only allow a dict of markers or None
        # the dict items usually look like this: {marker_frame: {color, duration, note, name, customData, ...}}
        if not isinstance(markers, dict) and markers is not None:
            logger.debug('Cannot set markers for timeline "{}" in this format.'.format(timeline_name, markers))
            return False

        # remove the markers key from the timeline if the markers are None
        if not markers and 'markers' in self.timelines[timeline_name]:
            del self._timelines[timeline_name]['markers']

        # otherwise set the markers
        else:
            self._timelines[timeline_name]['markers'] = markers

        self.set_dirty(save_soon=save_soon)

        return True

    def get_timeline_markers(self, timeline_name) -> list or None:
        """
        This gets the markers for a timeline
        :param timeline_name: str, the name of the timeline
        :return:
        """

        return self.get_timeline_setting(timeline_name=timeline_name, setting_key='markers')

    def set_timeline_timecode_data(self, timeline_name, timeline_fps=None, timeline_start_tc=None, save_soon=False):
        """
        This sets the timecode data for a timeline (timeline_fps and timeline_start_tc values)
        """

        if timeline_name is None:
            logger.debug('Cannot set timecode data for timeline "{}".'.format(timeline_name))
            return False

        if self.timelines is None:
            self._timelines = {}

        if timeline_name not in self.timelines:
            self._timelines[timeline_name] = {}

        if timeline_fps is not None:
            self._timelines[timeline_name]['timeline_fps'] = timeline_fps

        if timeline_start_tc is not None:
            self._timelines[timeline_name]['timeline_start_tc'] = timeline_start_tc

        self.set_dirty(save_soon=save_soon)

        return True

    def get_timeline_timecode_data(self, timeline_name) -> tuple:
        """
        This gets the timecode data for a timeline (timeline_fps and timeline_start_tc values)
        :param timeline_name: str, the name of the timeline
        :return: tuple, (timeline_fps, timeline_start_tc)
        """

        return (
            self.get_timeline_setting(timeline_name=timeline_name, setting_key='timeline_fps'),
            self.get_timeline_setting(timeline_name=timeline_name, setting_key='timeline_start_tc')
        )


class ProjectUtils:

    @staticmethod
    def write_to_project_file(project_data, project_path, backup=False):

        if project_path is None:
            logger.error('Cannot save project to path "{}".'.format(project_path))
            return False

        project_file_path = os.path.join(project_path, 'project.json')

        # if no full path was passed
        if project_file_path is None:
            logger.error('Cannot save project to path "{}".'.format(project_file_path))
            return False

        # if the directory of the project doesn't exist
        if not os.path.isdir(project_path):

            # create the directory
            logger.debug("Creating directory project directory {}".format(project_path))
            try:
                os.makedirs(project_path)

            except OSError:
                logger.error("Cannot create directory for project file path.", exc_info=True)
                return False

            except Exception as e:
                logger.error("Cannot create directory for project file path.\n{}".format(str(e)))
                return False

        # if backup_original is enabled, it will save a copy of the project file to
        # .backups/[filename].backup.json, but if backup is an integer, it will only save a backup after [backup] hours
        if backup and os.path.exists(project_file_path):

            # get the backups directory
            backups_dir = os.path.join(project_path, '.backups')

            # if the backups directory doesn't exist, create it
            if not os.path.exists(backups_dir):
                os.mkdir(backups_dir)

            # format the name of the backup file
            backup_project_file_path = 'project.backup.json'

            # if another backup file with the same name already exists, add a consecutive number to the end
            backup_n = 0
            while os.path.exists(os.path.join(backups_dir, backup_project_file_path)):

                # get the modified time of the existing backup file
                backup_file_modified_time = os.path.getmtime(os.path.join(backups_dir, backup_project_file_path))

                # if the backup file was modified less than [backup] hours ago, we don't need to save another backup
                if (isinstance(backup, float) or isinstance(backup, int)) \
                        and time.time() - backup_file_modified_time < backup * 60 * 60:
                    backup = False
                    break

                backup_n += 1
                backup_project_file_path = 'project.backup.{}.json'.format(backup_n)

            # if the backup setting is still not negative, we should save a backup
            if backup:
                # copy the existing file to the backup
                shutil \
                    .copyfile(project_file_path, os.path.join(backups_dir, backup_project_file_path))

                logger.debug('Copied project file to backup: {}'.format(backup_project_file_path))

        # encode the project json (do this before writing to the file, to make sure it's valid)
        project_json_encoded = json.dumps(project_data, indent=4)

        # write the project json to the file
        with open(project_file_path, 'w', encoding='utf-8') as outfile:
            outfile.write(project_json_encoded)

        logger.debug('Saved project to file: {}'.format(project_file_path))

        return project_file_path
