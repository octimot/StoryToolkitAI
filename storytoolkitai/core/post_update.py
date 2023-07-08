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


def post_update_0_19_4(is_standalone=False):

    # not needed if we are running in standalone mode
    if is_standalone:
        return True

    import sys
    import subprocess

    # uninstall openai-whisper package
    try:
        # uninstall openai-whisper package so we can re-install it and make sure we have the correct commit
        subprocess.check_call([sys.executable, '-m', 'pip', 'uninstall', '-y', 'openai-whisper'])

    except Exception as e:
        logger.error('Failed to uninstall openai-whisper package: {}'.format(e))
        logger.warning('Please uninstall and re-install the openai-whisper package manually.')

        return False

    # install requirements.txt
    try:
        # don't use cache dir
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt', '--no-cache-dir'])
    except Exception as e:
        logger.error('Failed to install requirements.txt: {}'.format(e))
        logger.warning('Please install the requirements.txt manually.')

        return False

    return True

# this is a dictionary of all the post_update functions
# make sure to keep them in order
post_update_functions = {
    '0.19.4': post_update_0_19_4
}

