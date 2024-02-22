import os.path

from storytoolkitai.core.logger import logger
import packaging
import time
import subprocess
import sys


def reinstall_requirements():

    try:
        # get the absolute path to requirements.txt,
        # considering it should be relative to the current file
        requirements_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', '..', 'requirements.txt'
        )

        # don't use cache dir
        subprocess.check_call(
            [sys.executable, '-m', 'pip', 'install', '-r', requirements_file_path, '--no-cache-dir'])
    except Exception as e:
        logger.error('Failed to install requirements.txt: {}'.format(e))
        logger.warning('Please install the requirements.txt manually.')

        return False

    return True


def post_update(current_version, last_version, is_standalone=False):
    """
    This checks when the last post_update was run and runs the post_update if the current version is newer.
    """

    if last_version is None:
        logger.debug('The last version value was not passed. Skipping post-update tasks.')
        return False

    # use packaging to compare the versions
    if packaging.version.parse(current_version) <= packaging.version.parse(last_version):
        return False

    logger.debug('Running post-update tasks from {} to {}...'.format(last_version, current_version))

    # go through all post_update_functions, and run them if they are newer than the last version
    # start from the last version

    # get the list of versions
    versions = list(post_update_functions.keys())

    # filter out the versions that are older than the last version
    versions = \
        [version for version in versions
         if packaging.version.parse(last_version)
         < packaging.version.parse(version)
         <= packaging.version.parse(current_version)
         ]

    # go through the versions in order
    for version in versions:

        # run the post_update function
        logger.info('Running post-update tasks for {}...'.format(version))
        post_update_functions[version](is_standalone=is_standalone)

    return True


def post_update_0_20_1(is_standalone=False):
    """
    This re-installs Whisper to make sure we have the right commit
    """

    # not needed if we are running in standalone mode
    if is_standalone:
        return True

    # uninstall openai-whisper package
    try:
        # uninstall openai-whisper package so we can re-install it and make sure we have the correct commit
        subprocess.check_call([sys.executable, '-m', 'pip', 'uninstall', '-y', 'openai-whisper'])
        logger.info('Uninstalled openai-whisper package to re-install relevant version.')

    except Exception as e:
        logger.error('Failed to uninstall openai-whisper package: {}'.format(e))
        logger.warning('Please uninstall and re-install the openai-whisper package manually.')
        time.sleep(3)

        return False

    # install the needed openai-whisper commit
    try:
        # don't use cache dir
        subprocess.check_call(
            [sys.executable, '-m', 'pip', 'install', '--upgrade', '--no-cache-dir',
             'openai-whisper@git+https://github.com/openai/whisper.git@ba3f3cd54b0e5b8ce1ab3de13e32122d0d5f98ab'])
    except Exception as e:
        logger.error('Failed to install requirements.txt: {}'.format(e))
        logger.warning('Please install the requirements.txt manually.')

        return False

    return True


def post_update_0_22_0(is_standalone=False):
    """
    This converts the "API Token" reference in the config file to "API Key".
    Needed both for the standalone and non-standalone versions.
    """

    import os
    import json

    # we're doing this on the raw file (not through the storytoolkitai class)
    from storytoolkitai import APP_CONFIG_FILE_PATH, USER_DATA_PATH

    if os.path.isfile(APP_CONFIG_FILE_PATH):

        # read the config file
        with open(APP_CONFIG_FILE_PATH, 'r') as f:
            config = json.load(f)

        # check if the API Token is in the config file
        if 'api_token' in config:

            # change the key to API Key
            config['stai_api_key'] = config.pop('api_token')

            # write the config file
            with open(APP_CONFIG_FILE_PATH, 'w') as f:
                json.dump(config, f, indent=4)

            logger.info('Updated API Token to API Key in config file.')

        else:
            logger.warning('API Token not found in config file. Change not needed.')

    else:
        logger.warning('Config file not found. Skipping post-update task to update API Token to API Key.')


def post_update_0_23_0(is_standalone=False):
    """
    This re-installs transformers and urllib3 to make sure we have the right version
    """

    # not needed if we are running in standalone mode
    if is_standalone:
        return True

    try:
        # uninstall packages so we can re-install them
        subprocess.check_call(
            [sys.executable, '-m', 'pip', 'uninstall', '-y', 'transformers', 'urllib3', 'opencv-python'])
        logger.info('Uninstalled transformers, urllib3, opencv-python to re-install relevant versions.')

    except Exception as e:
        logger.error('Failed to uninstall packages. {}'.format(e))
        logger.warning('Please uninstall and re-install transformers, urllib3, opencv-python packages manually.')
        time.sleep(3)

        return False

    # force a requirements.txt check and install
    return reinstall_requirements()


def post_update_0_24_0(is_standalone=False):
    """
    This re-writes the project.json files found for the projects in PROJECTS_PATH
    to make sure that the transcriptions are also mentioned a separate list from the timelines

    and

    Upgrades octimot/CustomTkinter to commit a2a8c37dd8dac1dee30133476596a5128adb0530 to support scrolling to y
    """

    from storytoolkitai.core.toolkit_ops.projects import Project, PROJECTS_PATH
    import json

    # if we don't have a PROJECTS_PATH, this update is not needed
    if not os.path.isdir(PROJECTS_PATH):
        return True

    # get the list of projects in the projects path
    projects = [f for f in os.listdir(PROJECTS_PATH) if Project(project_name=f).exists]

    if not projects:
        return True

    # sort by last modified
    projects.sort(key=lambda x: os.path.getmtime(os.path.join(PROJECTS_PATH, x, 'project.json')))

    # take each project
    for project_name in projects:

        project = Project(project_name=project_name)

        # skip if this is not a valid project
        if not project or not project.exists:
            continue

        # we're not going to use the Project class to make the update,
        # considering that it might change in the future, so let's work with the raw project.json file

        # first, get the path to the project.json file from the project
        project_json_path = os.path.join(project.project_path, 'project.json')

        # if the project.json file doesn't exist, skip it
        if not os.path.isfile(project_json_path):
            continue

        # read the project.json file
        with open(project_json_path, 'r') as f:
            project_json = json.load(f)

        # skip if there are no transcriptions
        if 'timelines' not in project_json:
            # but touch the file to update the modified time so we preserve the order
            os.utime(project_json_path, None)
            continue

        # take all timelines and see if there are transcription_files
        # if there are, copy them to a separate list but keep them in the timelines as well

        project_transcriptions = []

        for timeline in project_json['timelines']:

            # if for whatever reason, this is not a dictionary, skip it
            if not isinstance(project_json['timelines'][timeline], dict):
                continue

            # does this timeline have a transcription_files key?
            if 'transcription_files' not in project_json['timelines'][timeline]:
                continue

            transcription_files = project_json['timelines'][timeline]['transcription_files']

            # if it's not a list, or it's empty, skip it
            if not transcription_files or not isinstance(transcription_files, list):
                continue

            # take all the transcription files
            for transcription_file_path in transcription_files:

                # add them to the transcriptions_dict
                # if the transcription_file_path is not in the dict, add it
                if transcription_file_path not in project_transcriptions:
                    project_transcriptions.append(transcription_file_path)

        # add the transcriptions_dict to the project_json
        project_json['transcriptions'] = project_transcriptions

        # save the project_json
        with open(project_json_path, 'w') as f:
            json.dump(project_json, f, indent=4)

        # now let's take care of the CustomTkinter update
        try:
            # uninstall packages so we can re-install them
            subprocess.check_call(
                [sys.executable, '-m', 'pip', 'uninstall', '-y', 'customtkinter'])
            logger.info('Uninstalled customtkinter package to re-install relevant version.')

        except Exception as e:
            logger.error('Failed to uninstall customtkinter. {}'.format(e))
            logger.warning('Please uninstall and re-install customtkinter manually.')
            time.sleep(3)

            return False

        # force a requirements.txt check and install
        return reinstall_requirements()


# this is a dictionary of all the post_update functions
# make sure to keep them in order
# but clean update functions from the past
# which perform the same operations mentioned in further updates (for e.g. upgrading required packages)
post_update_functions = {
    '0.20.1': post_update_0_20_1,
    '0.22.0': post_update_0_22_0,
    '0.23.0': post_update_0_23_0,
    '0.24.0': post_update_0_24_0,
}
