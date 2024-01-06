import os.path

from storytoolkitai.core.logger import logger
import packaging


def post_update(current_version, last_version, is_standalone=False):
    """
    This checks when the last post_update was run and runs the post_update if the current version is newer.
    """

    if last_version is None:
        last_version = '0.0.0'

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

    # not needed if we are running in standalone mode
    if is_standalone:
        return True

    import sys
    import subprocess

    # uninstall openai-whisper package
    try:
        # uninstall openai-whisper package so we can re-install it and make sure we have the correct commit
        subprocess.check_call([sys.executable, '-m', 'pip', 'uninstall', '-y', 'openai-whisper'])
        logger.info('Uninstalled openai-whisper package to re-install relevant version on restart.')

    except Exception as e:
        logger.error('Failed to uninstall openai-whisper package: {}'.format(e))
        logger.warning('Please uninstall and re-install the openai-whisper package manually.')

        return False

    # once this is uninstalled,
    # the correct openai-whisper package should be
    # re-installed when the tool restarts and the requirements.txt check is performed

    return True


def post_update_0_22_0(is_standalone=False):
    """
    This converts the "API Token" reference in the config file to "API Key".
    Needed both for the standalone and non-standalone versions.
    """

    import os
    import json

    # we're doing this on the raw file (not through the storytoolkitai class)
    # so let's get the APP_CONFIG_FILE_NAME from the storytoolkitai package first
    from storytoolkitai import APP_CONFIG_FILE_NAME, USER_DATA_PATH
    config_file_path = os.path.join(USER_DATA_PATH, APP_CONFIG_FILE_NAME)

    if os.path.isfile(config_file_path):

        # read the config file
        with open(config_file_path, 'r') as f:
            config = json.load(f)

        # check if the API Token is in the config file
        if 'api_token' in config:

            # change the key to API Key
            config['stai_api_key'] = config.pop('api_token')

            # write the config file
            with open(config_file_path, 'w') as f:
                json.dump(config, f, indent=4)

            logger.info('Updated API Token to API Key in config file.')

        else:
            logger.warning('API Token not found in config file. Change not needed.')

    else:
        logger.warning('Config file not found. Skipping post-update task to update API Token to API Key.')


# this is a dictionary of all the post_update functions
# make sure to keep them in order
# but remove update functions from the past which uninstall and install requirements.txt
# (for eg. 0.19.4 was uninstalling openai-whisper and reinstalling requirements.txt)
post_update_functions = {
    '0.20.1': post_update_0_20_1,
    '0.22.0': post_update_0_22_0,
}

