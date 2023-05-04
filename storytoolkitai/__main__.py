
import sys
import argparse
import platform
import time
import subprocess
import os

# add content root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__+'../'))))

from storytoolkitai.core.logger import *
from storytoolkitai.integrations.mots_resolve import MotsResolve

from storytoolkitai import USER_DATA_PATH, OLD_USER_DATA_PATH, APP_CONFIG_FILE_NAME, APP_LOG_FILE, initial_target_dir
from storytoolkitai.core.toolkit_ops import ToolkitOps
from storytoolkitai.ui.toolkit_ui import toolkit_UI
from storytoolkitai.core.storytoolkitai import StoryToolkitAI

# signal the start of the session in the log by adding some info about the machine
logger.debug('\n--------------\n'
             'Platform: {} {}\n Platform version: {}\n OS: {} \n running Python {}'
             '\n--------------'.format(
    platform.system(), platform.release(),
    platform.version(),
    ' '.join(map(str, platform.win32_ver() + platform.mac_ver())),
    '.'.join(map(str, sys.version_info))))

# this makes sure that the user has all the required packages installed
try:
    # the path of this file
    file_path = os.path.abspath(__file__)

    # the requirements file is either one directory up from this file
    requirements_file_path = os.path.join(os.path.dirname(file_path), '..', 'requirements.txt')

    # or in this directory (valid for the standalone app)
    if not os.path.exists(os.path.join(os.path.dirname(file_path), '..', 'requirements.txt')):
        requirements_file_path = os.path.join(os.path.dirname(file_path), 'requirements.txt')

    # check if all the requirements are met
    import pkg_resources

    pkg_resources.require(open(requirements_file_path, mode='r'))

    logger.debug('All package requirements met.')

except:

    # let the user know that the packages are wrong
    import traceback

    traceback_str = traceback.format_exc()

    # get the relative path of the requirements file
    requirements_rel_path = os.path.relpath(os.path.join(os.path.dirname(__file__), 'requirements.txt'))

    logger.error(traceback_str)

    requirements_warning_msg = ('Some of the packages required to run StoryToolkitAI '
                                'are missing from your Python environment.\n')

    logger.warning(requirements_warning_msg)

    # if this is not a standalone app, try to install the requirements automatically
    if not getattr(sys, 'frozen', False):

        # try to install the requirements automatically
        logger.warning('Attempting to automatically install the required packages...')

        # install the requirements
        # invoke pip as a subprocess:
        pip_complete = subprocess.call([sys.executable, '-m', 'pip', 'install', '-r', requirements_rel_path])

        if pip_complete == 0:
            logger.warning('The required packages were installed. Restarting StoryToolkitAI...')

            time.sleep(1)

            try:
                # restart the app
                subprocess.call([sys.executable, os.path.abspath(__file__)] + sys.argv[1:])
                sys.exit(0)
            except:
                logger.error('Could not restart StoryToolkitAI. Please restart the app manually.')

        else:
            # let the user know that the automatic installation failed
            logger.error(
                'Could not auto-install the required packages. '
                'StoryToolkitAI might not work properly without them. '
                'To make sure that the right versions of the required packages are installed, '
                'please close the tool and run:\n\n'
                'pip install -r {} '
                '\n\n'
                .format(requirements_rel_path, APP_LOG_FILE))

    else:
        logger.warning('\n'
                       'If you are running the standalone version of the app, please report this error to the developers together '
                       'with the log file found at: {}\n'.format(APP_LOG_FILE))

    # keep this message in the console for a bit
    time.sleep(5)

from storytoolkitai.ui.toolkit_ui import run_gui

def main():

    # init StoryToolkitAI object
    stAI = StoryToolkitAI()

    # connect to the API
    # stAI.check_API_credentials()
    # stAI.connect_API()

    parser = argparse.ArgumentParser(description="Story Toolkit AI version {}".format(stAI.version))
    parser.add_argument("--mode", choices=["gui"], default="gui", help="Choose the mode to run the application")
    parser.add_argument("--debug", action='store_true', help="Enable debug mode")
    parser.add_argument("--noresolve", action='store_true', help="Disable Resolve API polling")
    #parser.add_argument("--host", default="localhost", help="Server host for server mode")
    #parser.add_argument("--port", type=int, default=8000, help="Server port for server mode")
    args = parser.parse_args()

    # initialize operations object
    toolkit_ops_obj = ToolkitOps(stAI=stAI)

    if args.mode == "gui":
        run_gui(toolkit_ops_obj=toolkit_ops_obj, stAI=stAI)

    #elif args.mode == "cli":
    #    run_cli(parser, toolkit_ops_obj=toolkit_ops_obj, stAI=stAI)
    #
    #elif args.mode == "server":
    #
    #    try:
    #        from storytoolkitai.server.server import run_server
    #        run_server(args.host, args.port)
    #    except ImportError:
    #        logger.error('Server mode is not supported in this version of StoryToolkitAI.')

    else:
        logger.error('Invalid mode selected. Please select a valid mode.')


if __name__ == '__main__':
    main()
