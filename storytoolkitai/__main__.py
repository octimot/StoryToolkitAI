
import sys
import argparse
import platform
import time
import subprocess
import os

# add content root to sys.path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from storytoolkitai.core.logger import *

# signal the start of the session in the log by adding some info about the machine
logger.debug('\n--------------\n'
             'Platform: {} {}\n Platform version: {}\n OS: {} \n running Python {}'
             '\n--------------'.format(
    platform.system(), platform.release(),
    platform.version(),
    ' '.join(map(str, platform.win32_ver() + platform.mac_ver())),
    '.'.join(map(str, sys.version_info))))

# get the current path of this file
file_path = os.path.abspath(__file__)

# the requirements file should be either one directory up from this file
requirements_file_path = os.path.join(os.path.dirname(file_path), '..', 'requirements.txt')

# or in this directory (valid for the standalone app)
if not os.path.exists(requirements_file_path):
    requirements_file_path = os.path.join(os.path.dirname(file_path), 'requirements.txt')

if not os.path.exists(requirements_file_path):
    logger.warning('Could not find the requirements.txt file.')

# this makes sure that the user has all the required packages installed
try:

    # check if all the requirements are met
    import pkg_resources

    pkg_resources.require(open(requirements_file_path, mode='r'))

    logger.debug('All package requirements met.')

except:

    # let the user know that the packages are wrong
    import traceback

    traceback_str = traceback.format_exc()

    logger.error(traceback_str)

    requirements_warning_msg = ('Some of the packages required to run StoryToolkitAI '
                                'are missing from your Python environment.\n')

    logger.warning(requirements_warning_msg)

    # if this is not a standalone app, try to install the requirements automatically
    if not getattr(sys, 'frozen', False):

        # try to install the requirements automatically
        logger.warning('Attempting to automatically install the required packages...')

        # get the relative path to the requirements file
        requirements_file_path_rel = os.path.relpath(requirements_file_path)

        # install the requirements
        # invoke pip as a subprocess:
        pip_complete = subprocess.call([sys.executable, '-m', 'pip', 'install', '-r', requirements_file_path_rel])

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
                .format(requirements_file_path_rel, APP_LOG_FILE))

    else:
        logger.warning('\n'
                       'If you are running the standalone version of the app, please report this error to the developers together '
                       'with the log file found at: {}\n'.format(APP_LOG_FILE))

    # keep this message in the console for a bit
    time.sleep(5)

from storytoolkitai.integrations.mots_resolve import MotsResolve

from storytoolkitai import USER_DATA_PATH, OLD_USER_DATA_PATH, APP_CONFIG_FILE_NAME, APP_LOG_FILE, initial_target_dir
from storytoolkitai.core.toolkit_ops import ToolkitOps
from storytoolkitai.ui.toolkit_ui import toolkit_UI
from storytoolkitai.ui.toolkit_cli import toolkit_CLI
from storytoolkitai.core.storytoolkitai import StoryToolkitAI

from storytoolkitai.ui.toolkit_ui import run_gui
from storytoolkitai.ui.toolkit_cli import run_cli

def main():

    # init StoryToolkitAI object
    stAI = StoryToolkitAI()

    # connect to the API
    # stAI.check_API_credentials()
    # stAI.connect_API()

    parser = argparse.ArgumentParser(description="Story Toolkit AI version {}".format(stAI.version))
    parser.add_argument("--mode", choices=["gui", "cli"], default="gui", help="Choose the mode to run the application")
    parser.add_argument("--debug", action='store_true', help="Enable debug mode")
    parser.add_argument("--noresolve", action='store_true', help="Disable Resolve API polling")
    parser.add_argument("--skip-python-check", action='store_true', help="Skips the Python version check")

    # cli args
    parser.add_argument("--render-resolve-timeline", action='store_true', help="Render current Resolve timeline")
    parser.add_argument("--output-dir", default=os.getcwd(), help="Target directory for the output files")

    args = parser.parse_args()

    # initialize operations object
    toolkit_ops_obj = ToolkitOps(stAI=stAI)

    if '--debug' in sys.argv:
        stAI.debug_mode = True

    if args.mode == "gui":
        run_gui(toolkit_ops_obj=toolkit_ops_obj, stAI=stAI)

    elif args.mode == "cli":
        run_cli(args, toolkit_ops_obj=toolkit_ops_obj, stAI=stAI)

    else:
        logger.error('Invalid mode selected. Please select a valid mode.')


if __name__ == '__main__':
    main()
