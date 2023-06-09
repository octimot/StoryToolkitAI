import sys
import os
import json
import platform
import subprocess
import time

from storytoolkitai import USER_DATA_PATH, OLD_USER_DATA_PATH, APP_CONFIG_FILE_NAME, initial_target_dir
from storytoolkitai.core.logger import logger
from storytoolkitai.core.logger import Style as loggerStyle

from requests import get


class StoryToolkitAI:
    def __init__(self, server=False, args=None):
        # import version.py - this holds the version stored locally
        import version

        self.cli_args = args

        # are we running the standalone version?
        # keep track of this in this class variable
        if getattr(sys, 'frozen', False):
            self.standalone = True
        else:
            self.standalone = False

        # keep the version in memory
        self.__version__ = self.version = version.__version__

        # this is where all the user files should be stored
        # if it's not absolute, make sure it's relative to the app.py script location
        # to make it easier for the users to find it
        # (and to prevent paths relative to possible virtual environment paths)
        if not os.path.isabs(USER_DATA_PATH):
            self.user_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), USER_DATA_PATH)
        else:
            self.user_data_path = USER_DATA_PATH

        # the config file should be in the user data directory
        self.config_file_path = os.path.join(self.user_data_path, APP_CONFIG_FILE_NAME)

        # create a config variable
        self.config = None

        # the projects directory is always inside the user_data_path
        # this is where we will store all the stuff related to specific projects
        self.projects_dir_path = os.path.join(self.user_data_path, 'projects')

        # create a project settings variable
        self.project_settings = {}

        # define the api variables
        self.api_possible = False
        self.api_user = None
        self.api_token = None
        self.api_host = None
        self.api = None
        self.api_token_valid = False

        self.debug_mode = False

        if not self.cli_args or not self.cli_args.mode == 'cli':
            self.check_api_token()

        # add a variable that holds usage statistics
        # this is only preserved until the app is closed
        self.statistics = {}

        # keep track of the initial_target_dir for this session
        # this is the directory that the user has last used in the file dialogs
        self.initial_target_dir = initial_target_dir

        # check if a new version of the app exists on GitHub
        # but use either the release version number or version.py,
        # depending on standalone is True or False
        if not self.cli_args or not self.cli_args.mode == 'cli' or not self.cli_args.skip_update_check:
            [self.update_available, self.online_version] = self.check_update()
        else:
            logger.debug("Skipping update check due to command line argument.")

        logger.info(loggerStyle.BOLD + loggerStyle.UNDERLINE + "Running StoryToolkitAI{} version {} {}"
                    .format(' SERVER' if server else '',
                            self.__version__,
                            '(standalone)' if self.standalone else ''))

        # get the backup_transcript_saves_every_n_hours setting
        self.transcript_backup_interval = \
            self.get_app_setting(setting_name='backup_transcription_saves_every_n_hours', default_if_none=2)


    def update_statistics(self, key, value):
        '''
        Updates the statistics dictionary
        '''
        if key not in self.statistics:
            self.statistics[key] = 0

        self.statistics[key] = value

    def read_statistics(self, key):
        '''
        Reads the statistics dictionary
        '''

        # return none if the key doesn't exist
        if key not in self.statistics:
            return None

        # otherwise return the value
        return self.statistics[key]

    def user_data_dir_exists(self, create_if_not=True):
        '''
        Checks if the user data dir exists and creates one if asked to
        :param create_if_not:
        :return:
        '''

        # if the directory doesn't exist
        if not os.path.exists(self.user_data_path):
            logger.warning('User data directory {} doesn\'t exist.'
                           .format(os.path.abspath(self.user_data_path)))

            if create_if_not:
                logger.warning('Creating user data directory.')

                # and create the whole path to it if it doesn't
                os.makedirs(self.user_data_path)

                # for users of versions prior to 0.16.14, the user data directory was at OLD_USER_DATA_PATH
                # so make sure we copy everything from the old path to the new directory
                old_user_data_path_abs = os.path.join(os.path.dirname(os.path.abspath(__file__)), OLD_USER_DATA_PATH)

                # we first check if the old_user_data_path_abs exists
                if os.path.exists(old_user_data_path_abs):
                    import shutil
                    from datetime import date
                    import platform

                    logger.warning('Old user data directory found.\n\n')

                    # let the user know that we are moving the files
                    move_user_data_path_msg = \
                        'Starting with version 0.16.14, ' \
                        'the user data directory on {} has moved to {}.\n' \
                        'This means that any existing configuration and project ' \
                        'settings files will be copied there.\n' \
                        'If the files are at the new location, feel free to delete {}\n' \
                            .format(platform.node(),
                                    self.user_data_path, old_user_data_path_abs, old_user_data_path_abs)

                    logger.warning(move_user_data_path_msg)

                    logger.warning('Copying user data files to new location.')

                    # copy all the contents of the OLD_USER_DATA_PATH to the new path
                    for item in os.listdir(old_user_data_path_abs):
                        s = os.path.join(old_user_data_path_abs, item)
                        d = os.path.join(self.user_data_path, item)

                        logger.warning((' - {}'.format(item)))

                        if os.path.isdir(s):
                            shutil.copytree(s, d, False, None)
                        else:
                            shutil.copy2(s, d)

                    logger.warning('Finished copying user data files to {}'.format(self.user_data_path))

                    # reload the config file
                    self.config = self.get_config()

                    # leave a readme file in the OLD_USER_DATA_PATH so that the user knows that stuff was moved
                    with open(os.path.join(old_user_data_path_abs, 'README.txt'), 'a') as f:
                        f.write('\n' + str(date.today()) + '\n')
                        f.write(move_user_data_path_msg)


            else:
                return False

        return True

    def project_dir_exists(self, project_settings_path=None, create_if_not=True):

        if project_settings_path is None:
            return False

        # if the directory doesn't exist
        if not os.path.exists(os.path.dirname(project_settings_path)):
            logger.warning('Project settings directory {} doesn\'t exist.'
                           .format(os.path.abspath(os.path.dirname(project_settings_path))))

            if create_if_not:
                logger.warning('Creating project settings directory.')

                # and create the whole path to it if it doesn't
                os.makedirs(os.path.dirname(project_settings_path))

            else:
                return False

        return True

    def get_app_setting(self, setting_name=None, default_if_none=None):
        '''
        Returns a specific app setting or None if it doesn't exist
        If default if none is passed, the app will also save the setting to the config for future use
        :param setting_name:
        :param default_if_none:
        :return:
        '''

        if setting_name is None or not setting_name or setting_name == '':
            logger.error('No setting was passed.')
            return False

        # if the config doesn't exist, create it
        # this means that the configurations are only loaded once per session
        # or when the user changes them during the session
        if self.config is None:
            self.config = self.get_config()

        # look for the requested setting
        if setting_name in self.config:

            # and return it
            return self.config[setting_name]

        # if the requested setting doesn't exist in the config
        # but a default was passed
        elif default_if_none is not None:

            logger.info('Config setting {} saved as "{}" '.format(setting_name, default_if_none))

            # save the default to the config
            self.save_config(setting_name=setting_name, setting_value=default_if_none)

            # and then return the default
            return default_if_none

        # otherwise simple return none
        else:
            return None

    def save_config(self, setting_name=None, setting_value=None):
        '''
        Saves a setting to the app configuration file
        :param config_key:
        :param config_value:
        :return:
        '''

        # if a setting name and value was passed
        if setting_name is not None and setting_value is not None:
            # get existing configuration
            self.config = self.get_config()

            logger.info('Updated config file {} with {} data.'
                        .format(os.path.abspath(self.config_file_path), setting_name))
            self.config[setting_name] = setting_value

        # if the config is empty something might be wrong
        if self.config is None:
            logger.error('Config file needs to be loaded before saving')
            return False

        # before writing the configuration to the config file
        # check if the user data directory exists (and create it if not)
        self.user_data_dir_exists(create_if_not=True)

        # then write the config to the config json
        with open(self.config_file_path, 'w') as outfile:
            json.dump(self.config, outfile, indent=3)

            logger.info('Config file {} saved.'.format(os.path.abspath(self.config_file_path)))

        # and return the config back to the user
        return self.config

    def get_config(self):
        '''
        Gets the app configuration from the config file (if one exists)
        :return:
        '''

        # read the config file if it exists
        if os.path.exists(self.config_file_path):
            logger.debug('Loading config file {}.'.format(self.config_file_path))

            try:
                # read the app config
                with open(self.config_file_path, 'r') as json_file:
                    self.config = json.load(json_file)

                # and return the config
                return self.config

            except:
                logger.error('Unable to read config file {}.'.format(self.config_file_path))
                logger.error('Make sure that it is a valid json file. '
                             'If you are not sure, delete it or rename it and restart the tool. '
                             'But keep in mind that you will lose all your settings.')

                sys.exit()

        # if the config file doesn't exist, return an empty dict
        else:
            logger.debug('No config file found at {}.'.format(self.config_file_path))
            return {}

    def _project_settings_path(self, project_name=None):

        # the full path to the project settings file
        if project_name is not None and project_name != '':
            return os.path.join(self.projects_dir_path, project_name, 'project.json')

    def get_project_settings(self, project_name=None):
        '''
        Gets the settings of a specific project
        :return:
        '''

        if project_name is None:
            logger.error('Unable to get project settings if no project name was passed.')

        # the full path to the project settings file
        project_settings_path = self._project_settings_path(project_name=project_name)

        # read the project settings file if it exists
        if project_settings_path is not None and os.path.exists(project_settings_path):

            # read the project settings from the project.json
            with open(project_settings_path, 'r') as json_file:
                self.project_settings = json.load(json_file)

            # and return the project settings
            return self.project_settings

        # if the project settings file doesn't exist, return an empty dict
        else:
            logger.debug('Project settings file {} not found.'.format(project_settings_path))
            return {}

    def save_project_settings(self, project_name=None, project_settings=None):
        '''
        Saves the settings of a specific project.
        This will OVERWRITE any existing project settings so make sure you include the whole project settings dictionary
        in the call!
        :param project_name:
        :return:
        '''

        if project_name is None or project_name == '' or project_settings is None:
            logger.error('Insufficient data. Unable to save project settings.')
            return False

        # the full path to the project settings file
        project_settings_path = self._project_settings_path(project_name=project_name)

        # before writing the project settings
        # check if the project directory exists (and create it if not)
        if (self.project_dir_exists(project_settings_path=project_settings_path, create_if_not=True)):
            # but make sure it also contains the correct project name
            project_settings['name'] = project_name

            # then overwrite the settings to the project settings json
            with open(project_settings_path, 'w') as outfile:
                json.dump(project_settings, outfile, indent=3)

            logger.debug('Updated project settings file {}.'
                         .format(os.path.abspath(project_settings_path)))

            # and return the config back to the user
            return project_settings

        return False

    def get_project_setting(self, project_name=None, setting_key=None):

        # get all the project settings first
        self.project_settings = self.get_project_settings(project_name=project_name)

        if self.project_settings:

            # is there a setting_key in the project settings
            if setting_key in self.project_settings:
                # then return the setting value
                return self.project_settings[setting_key]

        # if the setting key wasn't found
        return None

    def save_project_setting(self, project_name=None, setting_key=None, setting_value=None):
        '''
        Saves only a specific project setting, by getting the saved project settings and only overwriting
        the setting that was passed (setting_key)
        :param project_name:
        :param setting_key:
        :param setting_value:
        :return:
        '''

        if project_name is None or project_name == '' or setting_key is None:
            logger.error('Insufficient data. Unable to save project setting.')
            return False

        # get the current project settings
        self.project_settings = self.get_project_settings(project_name=project_name)

        # convert None values to False
        if setting_value is None:
            setting_value = False

        # only overwrite the passed setting_key
        self.project_settings[setting_key] = setting_value

        # now save them to file
        self.save_project_settings(project_name=project_name, project_settings=self.project_settings)

        return True

    def get_timeline_setting(self, project_name=None, timeline_name=None, setting_key=None):
        '''
        This gets a specific timeline setting from the project.json by looking into the timelines dictionary
        :param project_name:
        :param timeline_name:
        :param setting_key:
        :return:
        '''

        # get all the project settings first
        self.project_settings = self.get_project_settings(project_name=project_name)

        if self.project_settings:

            # is there a timeline dictionary?
            # is there a reference regarding the passed timeline?
            # is there a reference regarding the passed setting key?
            if 'timelines' in self.project_settings \
                    and timeline_name in self.project_settings['timelines'] \
                    and setting_key in self.project_settings['timelines'][timeline_name]:
                # then return the setting value
                return self.project_settings['timelines'][timeline_name][setting_key]

        # if the setting key, or any of the stuff above wasn't found
        return None

    def check_api_token(self, api_token=None):
        '''
        This checks if the user token is valid
        If no token is set, it will return False without performing the check
        :return:
        '''

        # if the user token is empty, False or '0' ('0' needed for backwards compatibility)
        if api_token is None or api_token == '' or not api_token or api_token == '0':

            # get the user token from the settings
            self.api_token = self.get_app_setting(setting_name='api_token', default_if_none=None)
        else:
            self.api_token = api_token

        # if the user token is not empty
        if self.api_token and self.api_token != '':
            check_path = 'https://api.storytoolkit.ai/check_token?token={}'.format(self.api_token)

            # check if the user token is valid on the server
            try:
                # access the check path
                response = get(check_path, timeout=5)

                # if the response is 200 and the text response is 'true'
                if response.status_code == 200 and response.text == 'true':
                    logger.debug('Using valid user token.')
                    self.api_token_valid = True
                    return True

                else:
                    logger.debug('User token is not valid.')
                    self.api_token_valid = False
                    return False

            except:
                pass

        self.api_token_valid = False
        return False

    def check_update(self):
        '''
        This checks if there's a new version of the app on GitHub and returns True if it is and the version number

        :param: release: if True, it will only check for standalone releases, and ignore the version.py file
        :return: [bool, str online_version]
        '''

        # get the latest release from GitHub if release is True
        if self.standalone:

            try:
                # get the latest release from GitHub
                latest_release = get('https://api.github.com/repos/octimot/storytoolkitai/releases/latest').json()

                # remove the 'v' from the release version (tag)
                online_version_raw = latest_release['tag_name'].replace('v', '')

            # show exception if it fails, but don't crash
            except Exception as e:
                logger.warning('Unable to check the latest release version of StoryToolkitAI: {}. '
                               '\nIs your Internet connection working?'.format(e))

                # return False - no update available and None instead of an online version number
                return False, None

        # otherwise get the latest version from the api.storytoolkit.ai/version file
        else:
            version_request = "https://api.storytoolkit.ai/version"

            # retrieve the latest version number from github
            try:
                r = get(version_request, verify=True)

                # extract the actual version number from the string
                online_version_raw = r.text.split('"')[1]

            # show exception if it fails, but don't crash
            except Exception as e:
                logger.warning('Unable to check the latest version of StoryToolkitAI: {}. '
                               '\nIs your Internet connection working?'.format(e))

                # return False - no update available and None instead of an online version number
                return False, None

        # get the numbers in the version string
        local_version = self.__version__.split(".")
        online_version = online_version_raw.split(".")

        # did the use choose to ignore the update?
        ignore_update = self.get_app_setting(setting_name='ignore_update', default_if_none=False)

        # if they did, is the online version the same as the one they ignored?
        if ignore_update and ignore_update.split(".") == online_version:
            logger.info('Ignoring the new update (version {}) due to app settings.'.format(ignore_update))

            # return False - no update available and the local version number instead of what's online
            return False, self.__version__

        # take each number in the version string and compare it with the local numbers
        for n in range(len(online_version)):

            # only test for the first 3 numbers in the version string
            if n < 3:
                # if there's a number larger online, return true
                if int(online_version[n]) > int(local_version[n]):

                    # if we're checking for a standalone release
                    if self.standalone and 'latest_release' in locals() and 'assets' in latest_release:

                        release_files = latest_release['assets']
                        if len(release_files) == 0:
                            return False, online_version_raw

                        # is there a release file for mac, given the current architecture?
                        if platform.system() == 'Darwin':
                            # check if there is a file that contains the current machine's architecture
                            release_file = [f for f in release_files if platform.machine() in f['name'].lower()]
                            return len(release_file) > 0, online_version_raw

                        # if we're on windows, check if there is a file that contains 'win'
                        elif platform.system() == 'Windows':
                            release_file = [f for f in release_files if 'win' in f['name'].lower()]
                            return len(release_file) > 0, online_version_raw

                    # worst case, return True to make sure the user is notified despite the lack of a release file
                    return True, online_version_raw

                # continue the search if there's no version mismatch
                if int(online_version[n]) == int(local_version[n]):
                    continue
                break

        # return false (and the online version) if the local and the online versions match
        return False, online_version_raw

    def check_ffmpeg(self):

        # check if ffmpeg is installed

        try:

            # first, check if the user added the ffmpeg path to the app settings
            ffmpeg_path_custom = self.get_app_setting(setting_name='ffmpeg_path')

            # if the ffmpeg path is not empty
            if ffmpeg_path_custom is not None and ffmpeg_path_custom != '':

                logger.debug('Found ffmpeg path in app config: {}'.format(ffmpeg_path_custom))

                if os.path.isfile(ffmpeg_path_custom):

                    # add it to the environment variables
                    os.environ['FFMPEG_BINARY'] = ffmpeg_path_custom

                else:
                    logger.warning('The ffmpeg path {} found in app config is not valid.'
                                   .format(ffmpeg_path_custom))

                    ffmpeg_path_custom = None

            # otherwise try to find the binary next to the app
            if ffmpeg_path_custom is None:

                # and if it exists, define the environment variable for ffmpeg for this session
                if os.path.exists('ffmpeg'):
                    logger.debug('Found ffmpeg in current working directory.')
                    os.environ['FFMPEG_BINARY'] = 'ffmpeg'

            # and check if it's working

            logger.debug('Looking for ffmpeg in env variable.')

            # get the FFMPEG_BINARY variable
            ffmpeg_binary = os.getenv('FFMPEG_BINARY')

            # if the variable is empty, try to find ffmpeg in the PATH
            if ffmpeg_binary is None or ffmpeg_binary == '':
                logger.debug('FFMPEG_BINARY env variable is empty. Looking for ffmpeg in PATH.')
                import shutil
                ffmpeg_binary = ffmpeg_binary if ffmpeg_binary else shutil.which('ffmpeg')

            # if ffmpeg is still not found in the path either, try to brute force it
            if ffmpeg_binary is None:
                logger.debug('FFMPEG_BINARY environment variable not set. Trying to use "ffmpeg".')
                ffmpeg_binary = 'ffmpeg'

            cmd = [
                ffmpeg_binary]

            logger.debug('Checking ffmpeg binary: {}'.format(ffmpeg_binary))

            # check if ffmpeg answers the call
            exit_code = subprocess.call(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            logger.debug('FFMPEG exit code: {}'.format(exit_code))

            if exit_code == 1:
                logger.info('FFMPEG found at {}'.format(ffmpeg_binary))

            else:
                logger.error('FFMPEG not found on this machine, some features will not work')

            # if it does, just return true
            return True

        except FileNotFoundError:

            # print the exact exception
            import traceback
            traceback_str = traceback.format_exc()

            logger.error(traceback_str)

            # if the ffmpeg binary wasn't found, we presume that ffmpeg is not installed on the machine
            return False

    def check_API_credentials(self):
        '''
        Checks if the API credentials are set in the app settings
        :return:
        '''

        # get the API token from the app settings
        api_token = self.get_app_setting(setting_name='api_token', default_if_none=False)

        # get the API username from the app settings
        api_user = self.get_app_setting(setting_name='api_user', default_if_none=False)

        # get the API host from the app settings
        api_host = self.get_app_setting(setting_name='api_host', default_if_none=False)

        # if the API token and username are not False or empty
        if api_token and api_user and api_token is not None and api_user is not None:
            logger.info('Found API username and token in config')
            self.api_user = api_user
            self.api_token = api_token
            self.api_host = api_host
            self.api_possible = True

        else:
            logger.debug('No API username and token found in config, so API connection not possible')
            self.api_user = None
            self.api_token = None
            self.api_host = None
            self.api_possible = False
            return None

    def connect_API(self):
        '''
        Connects to the API
        :return:
        '''

        # if the API credentials are not set, return False
        if not self.api_possible:
            logger.error('API credentials not set, so API connection not possible')
            return False

        # if the API credentials are set, try to connect to the API
        try:

            logger.info('Trying to connect to the API')

            import socket

            # get the host and ip from self.api_host
            host = self.api_host.split(':')[0]
            port = int(self.api_host.split(':')[1])

            # connect to API using sockets, ssl and user and token
            self.api = socket.create_connection((host, port))

            # wrap the socket in an SSL context
            # self.api = ssl.wrap_socket(self.api, ssl_version=ssl.PROTOCOL_TLSv1_2)

            # send the username and token to the API
            self.api.send(bytes('login:{}:{}'.format(self.api_user, self.api_token), 'utf-8'))

            # get the response from the API
            response = self.api.recv(1024).decode('utf-8')

            # if the response is not 'ok', return False
            if response != 'ok':
                logger.error('API connection failed: {}'.format(response))
                return False

            logger.info('API authenticated')
            self.api_connected = True

            while True:
                # ping the server every 2 seconds
                time.sleep(2)
                self.send_API_command(command='ping')

            # send the ping command
            # self.send_API_command(command='transcribe:file_path')

            return True

        # if the connection fails, return False
        except Exception as e:
            logger.error('Unable to connect to the API: {}'.format(e))
            self.api_connected = False
            return False

    def send_API_command(self, command):

        if self.api is None:
            logger.error('API not connected, so no command can be sent')
            return False

        try:
            self.api.send(bytes(command, 'utf-8'))
            logger.debug('Sending command to API: {}'.format(command))

            response = self.api.recv(1024).decode('utf-8')

            logger.debug('Received response from API: {}'.format(response))
            return response

        except Exception as e:
            logger.error('Unable to send command to API: {}'.format(e))
            return False
