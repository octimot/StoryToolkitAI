
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

# check if the user is running the any version of Python 3.10
if sys.version_info.major != 3 or sys.version_info.minor != 10:

    logger.warning('You are running Python {}.{}.{}.\n'.format(*sys.version_info) +
                   'StoryToolkitAI is now optimized to run on Python 3.10.\n' +
                   'Please download and install the latest version of Python 3.10 '
                   'from: https://www.python.org/downloads/\nand then re-install the '
                   'tool with a new environment.\n '
                   'More info: https://github.com/octimot/StoryToolkitAI/blob/main/INSTALLATION.mdn\n')

    # keep this message in the console for a bit
    time.sleep(5)

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
                # restart the app while passing all the arguments
                os.execl(sys.executable, sys.executable, *sys.argv)
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

from storytoolkitai.core.storytoolkitai import StoryToolkitAI

StoryToolkitAI.check_ffmpeg()

from storytoolkitai.core.toolkit_ops.toolkit_ops import ToolkitOps

from storytoolkitai.ui.toolkit_ui import run_gui
from storytoolkitai.ui.toolkit_cli import run_cli

def main():

    parser = argparse.ArgumentParser(description="Story Toolkit AI")
    parser.add_argument("--mode", choices=["gui", "cli"], default="gui", help="Choose the mode to run the application")
    parser.add_argument("--debug", action='store_true', help="Enable debug mode")
    parser.add_argument("--noresolve", action='store_true', help="Disable Resolve API")
    parser.add_argument("--skip-python-check", action='store_true', help="Skips the Python version check")
    parser.add_argument("--skip-update-check", action='store_true', help="Does not check for updates")

    # cli args
    parser.add_argument("--output-dir", default=os.getcwd(), help="Target directory for the output files")

    # this allows to pass keyword arguments to the render_timeline function
    # the format should be "--resolve-render \"KEY=VALUE\""
    parser.add_argument("--resolve-render", metavar="\"KEY1=VALUE1\", \"KEY2=VALUE2\", ...\"",
                        help="Renders the current Resolve timeline. Example Resolve API render arguments: "
                             "resolve-render=\", render_preset='H.264 Master', start_render=True, --add_date=True\"")

    # if we want to render a specific job, we use this
    parser.add_argument("--resolve-render-job", metavar="\"JOB_ID\"",
                        help="Renders a specific job from the Resolve Render Queue")

    # we also need --resolve-render-data (in json format) to pass the data to the resolve-render-job
    parser.add_argument("--resolve-render-data", metavar="\"JSON_DATA\"",
                        help="The data that will be written to the .json files associated with the rendered files.")

    args = parser.parse_args()

    # init StoryToolkitAI object
    stAI = StoryToolkitAI(args=args)

    # connect to the API
    # stAI.check_API_credentials()
    # stAI.connect_API()

    # initialize operations object
    toolkit_ops_obj = ToolkitOps(stAI=stAI)

    if '--debug' in sys.argv:
        stAI.debug_mode = True

    if args.mode == "gui":
        run_gui(toolkit_ops_obj=toolkit_ops_obj, stAI=stAI)

    elif args.mode == "cli":
        run_cli(args, parser, toolkit_ops_obj=toolkit_ops_obj, stAI=stAI)

    else:
        logger.error('Invalid mode selected. Please select a valid mode.')


if __name__ == '__main__':
    main()
