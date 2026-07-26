import os.path

from storytoolkitai.core.logger import logger
from packaging.version import InvalidVersion

from storytoolkitai.core.versioning import parse_version
import time
import subprocess
import sys


def cuda_is_available():
    try:
        # check if nvcc (NVIDIA's CUDA compiler) is installed
        subprocess.check_output(['nvcc', '--version'])
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        return False


def reinstall_requirements():
    # get the absolute path to requirements.txt,
    # considering it should be relative to the current file
    requirements_file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', '..', 'requirements.txt'
    )

    original_requirements = None

    logger.info('Re-installing requirements.txt...')
    logger.info('This may take a few minutes.')
    try:

        # but before we reinstall, detect if we have CUDA available:
        if cuda_is_available():

            logger.info('CUDA is available on this system. '
                        'Trying to install CUDA compatible versions of torch, torchaudio, and torchvision.')

            # if we do, we will use torch 2.0.0+cu117, torchaudio 2.0.1+cu117, and torchvision 0.15.1+cu117
            # so we need to replace the torch, torchaudio, and torchvision lines in the requirements.txt file
            # copy the requirements.txt file to a temporary file
            with open(requirements_file_path, 'r') as f:
                requirements = f.readlines()
                original_requirements = requirements.copy()

            # replace the torch, torchaudio, and torchvision lines
            for i, line in enumerate(requirements):
                if 'torchaudio' in line:
                    requirements[i] = \
                        'torchaudio==2.0.1+cu117 --extra-index-url https://download.pytorch.org/whl/cu117\n'
                elif 'torch' in line:
                    requirements[i] = \
                        'torch==2.0.0+cu117 --extra-index-url https://download.pytorch.org/whl/cu117\n'

            # write the requirements back to the file
            with open(requirements_file_path, 'w') as f:
                f.writelines(requirements)

        # don't use cache dir
        subprocess.check_call(
            [sys.executable, '-m', 'pip', 'install', '-r', requirements_file_path, '--no-cache-dir'])

        # restore the original requirements
        if original_requirements:
            with open(requirements_file_path, 'w') as f:
                f.writelines(original_requirements)
    except Exception as e:
        logger.error('Failed to install requirements.txt: {}'.format(e))
        logger.warning('Please install the requirements.txt manually.')

        # restore the original requirements
        with open(requirements_file_path, 'w') as f:
            f.writelines(original_requirements)

        return False

    return True


def post_update(current_version, last_version, is_standalone=False):
    """
    Run post-update tasks required between two released app versions.

    Development builds intentionally do not run automatic migrations or
    advance the saved ``last_update`` checkpoint. This prevents a dev checkout
    from changing the migration state used by a stable installation.

    The caller restarts the application when this function returns ``True``.
    """

    if last_version is None:
        logger.debug(
            'The last version value was not passed. '
            'Skipping post-update tasks.'
        )

        return False

    try:
        parsed_current_version = parse_version(current_version)

    except InvalidVersion as exc:
        logger.error(
            'The current StoryToolkitAI version "{}" is invalid: {}'.format(
                current_version,
                exc,
            )
        )

        return False

    # Do not automatically migrate real user data while running a development
    # checkout. Migrations intended for version 1 should be registered under
    # the final "1.0.0" version and will run when that release is installed.
    if parsed_current_version.is_devrelease:
        logger.debug(
            'Skipping post-update tasks for development version {}.'.format(
                current_version
            )
        )

        return False

    try:
        parsed_last_version = parse_version(last_version)

    except InvalidVersion as exc:
        logger.error(
            'The saved last_update version "{}" is invalid: {}'.format(
                last_version,
                exc,
            )
        )

        return False

    if parsed_current_version <= parsed_last_version:
        return False

    logger.debug(
        'Running post-update tasks from {} to {}...'.format(
            last_version,
            current_version,
        )
    )

    try:
        # Sort by parsed version rather than relying on dictionary insertion
        # order. This also supports future prerelease or post-release keys.
        versions = sorted(
            [
                version
                for version in post_update_functions
                if (
                    parsed_last_version
                    < parse_version(version)
                    <= parsed_current_version
                )
            ],
            key=parse_version,
        )

    except InvalidVersion as exc:
        logger.error(
            'A post-update task has an invalid version key: {}'.format(exc)
        )

        return False

    for version in versions:
        logger.info(
            'Running post-update tasks for {}...'.format(version)
        )

        # Preserve the current behavior: individual post-update return values
        # do not change whether the version transition is recorded.
        post_update_functions[version](
            is_standalone=is_standalone,
        )

    # Returning True tells StoryToolkitAI.__init__ to save the new
    # last_update value and restart once. This is retained for stable releases,
    # even when no version-specific migration was registered.
    return True


def post_update_0_22_0(is_standalone=False):
    """
    This converts the "API Token" reference in the config file to "API Key".
    Needed both for the standalone and non-standalone versions.
    """

    import os
    import json

    # we're doing this on the raw file (not through the storytoolkitai class)
    from storytoolkitai import APP_CONFIG_FILE_PATH

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

def post_update_0_25_0(is_standalone=False):
    """
    This re-installs Whisper to make sure we have the commit 517a43ecd132a2089d85f4ebc044728a71d49f6e
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
             'openai-whisper@git+https://github.com/openai/whisper.git@517a43ecd132a2089d85f4ebc044728a71d49f6e'])
    except Exception as e:
        logger.error('Failed to install requirements.txt: {}'.format(e))
        logger.warning('Please install the requirements.txt manually.')

        return False

    return True


# this is a dictionary of all the post_update functions
# make sure to keep them in order
# but clean update functions from the past
# which perform the same operations mentioned in further updates (for e.g. upgrading required packages)
post_update_functions = {
    '0.22.0': post_update_0_22_0,
    '0.23.0': post_update_0_23_0,
    '0.24.0': post_update_0_24_0,
    '0.25.0': post_update_0_25_0,
}
