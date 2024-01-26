
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

# check if the user is running any version of Python 3.10
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
requirements_file_path = os.path.abspath(os.path.join(os.path.dirname(file_path), '..', 'requirements.txt'))

# this makes sure that the user has all the required packages installed for the non-standalone app
if not getattr(sys, 'frozen', False):

    if not os.path.exists(requirements_file_path):
        logger.warning('Could not find the requirements.txt file.')

    # check to see if all the requirements are met
    requirements_failed = False

    try:

        # check if all the requirements are met
        # important: this does not check if the correct versions of the packages are installed
        # so if a specific version if required, we need to deal with it in the post_update() function
        import pkg_resources

        pkg_resources.require(open(requirements_file_path, mode='r'))

        logger.debug('All package requirements met.')

    except FileNotFoundError:
        logger.error("Could not find {} to check the required packages" .format(requirements_file_path))
        sys.exit()

    except pkg_resources.VersionConflict as e:
        # log the error and show the warning
        logger.debug("Version conflict in package:", exc_info=True)
        logger.warning("Version conflict in package: {}".format(e))
        requirements_failed = True

    except pkg_resources.DistributionNotFound as e:
        # log the error and show the warning
        logger.debug("Distribution not found for package:", exc_info=True)
        logger.warning("Packages missing from the installation: {}".format(e))
        requirements_failed = True

    except:
        # log the error and show the warning
        logger.warning("There's something wrong with the packages installed in your Python environment:", exc_info=True)
        requirements_failed = True

    # no matter what, we need to check if the user has the correct version of Python installed
    if requirements_failed:

        logger.warning('Some of the packages required to run StoryToolkitAI are missing from your Python environment.')

        # try to install the requirements automatically
        logger.warning('Attempting to automatically install the missing packages...')

        # get the relative path to the requirements file
        requirements_file_path_abs = os.path.abspath(requirements_file_path)

        # install the requirements
        # invoke pip as a subprocess:
        pip_complete = subprocess.call([sys.executable, '-m', 'pip', 'install', '-r', requirements_file_path_abs])

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
                .format(requirements_file_path_abs, APP_LOG_FILE))

        # keep this message in the console for a bit
        time.sleep(2)

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
