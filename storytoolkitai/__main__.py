import sys
import argparse
import platform
import time
import subprocess
import os
import ctypes
import ctypes.util


def is_windows():
    return platform.system() == "Windows"


def is_cuda_available():
    if not is_windows():
        return False

    try:
        cuda = ctypes.CDLL(ctypes.util.find_library("nvcuda") or "nvcuda.dll")
        cuda.cuInit(0)
        return True
    except:
        return False

# add content root to sys.path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from storytoolkitai.core.logger import *

# signal the start of the session in the log by adding some info about the machine
logger.debug('\n--------------\n'
             'Platform: {} {}\n Platform version: {}\n OS: {} \n running Python {}'
             '\n--------------'
             .format(platform.system(), platform.release(), platform.version(),
                     ' '.join(map(str, platform.win32_ver() + platform.mac_ver())),
                     '.'.join(map(str, sys.version_info))))

# check if the user is running any version of Python 3.10 or 3.11
if sys.version_info.major != 3 or (sys.version_info.minor != 10 and sys.version_info.minor != 11):

    logger.warning('You are running Python {}.{}.{}.\n'.format(*sys.version_info) +
                   'StoryToolkitAI is now optimized to run on Python 3.11.\n' +
                   'Please download and install the latest version of Python 3.11 '
                   'from: https://www.python.org/downloads/\nand then re-install the tool with a new environment.\n '
                   'More info: https://github.com/octimot/StoryToolkitAI/blob/main/INSTALLATION.md\n')

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

    logger.debug('Checking package requirements from {}'.format(requirements_file_path))

    try:

        # read requirements file contents
        with open(requirements_file_path, 'r') as f:
            req_lines = f.readlines()

        # check if all the requirements are met
        # important: this does not check if the correct versions of the packages are installed
        # so if a specific version if required, we need to deal with it in the post_update() function
        from packaging.requirements import Requirement
        import importlib.metadata

        for req_line in req_lines:
            req_line = req_line.strip()
            if not req_line or req_line.startswith('#'):
                continue  # skip empty lines and comments

            req = Requirement(req_line)
            try:
                installed_version = importlib.metadata.version(req.name)
            except importlib.metadata.PackageNotFoundError as e:
                logger.debug("Distribution not found for package:", exc_info=True)
                logger.warning("Packages missing from the installation: {}".format(req.name))
                requirements_failed = True
                continue

            # if a version specifier is provided, check that the installed version satisfies it
            if req.specifier and not req.specifier.contains(installed_version, prereleases=True):
                logger.debug("Version conflict in package: {}. Installed: {}, Required: {}".format(
                    req.name, installed_version, req.specifier))
                logger.warning("Version conflict in package: {} (installed: {}, required: {})".format(
                    req.name, installed_version, req.specifier))
                requirements_failed = True

    except Exception as e:
        # log the error and show the warning
        logger.warning("There's something wrong with the packages installed in your Python environment: {}".format(e),
                       exc_info=True)
        requirements_failed = True

    # if the requirements are not met, we need to install them
    if requirements_failed:

        logger.warning('Some of the packages required to run StoryToolkitAI are missing from your Python environment.')

        # try to install the requirements automatically
        logger.warning('Attempting to automatically install the missing packages...')

        # if we are on Windows and CUDA is available, we need to make sure we're using the correct PyTorch version
        if is_windows() and is_cuda_available():

            import shutil

            # create the path for the new requirements file
            windows_requirements_file_path = \
                os.path.abspath(os.path.join(os.path.dirname(file_path), '..', 'requirements_windows_cuda.txt'))

            # copy the original file
            shutil.copy2(requirements_file_path, windows_requirements_file_path)

            # read the contents of the new file
            with open(windows_requirements_file_path, 'r') as f:
                lines = f.readlines()

            # modify the PyTorch related lines
            pytorch_packages = ['torch', 'torchvision', 'torchaudio']
            modified_lines = []
            for line in lines:

                # if it's either torch, torchvision or torchaudio
                if line.startswith('torchaudio'):
                    # modify the line to include the correct version
                    line = 'torchaudio==2.0.1+cu118\n'
                    modified_lines.append(line)

                elif line.startswith('torchvision'):
                    # modify the line to include the correct version
                    line = 'torchvision==0.15.1+cu118\n'
                    modified_lines.append(line)

                elif line.startswith('torch'):
                    # modify the line to include the correct version
                    line = 'torch==2.0.0+cu118\n'
                    modified_lines.append(line)

                # otherwise, just add the line as is
                else:
                    modified_lines.append(line)

            # add this to the beginning of the file
            modified_lines.insert(0, '--find-links https://download.pytorch.org/whl/torch_stable.html\n')

            # write the modified contents back to the file
            with open(windows_requirements_file_path, 'w') as f:
                f.writelines(modified_lines)

            logger.debug(f"Created Windows CUDA requirements file: {windows_requirements_file_path}")

            requirements_file_path = windows_requirements_file_path

        else:
            windows_requirements_file_path = None

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
            except Exception as e:
                logger.error('Could not restart StoryToolkitAI: {}'.format(e))
                logger.error('Please restart the tool manually.')

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

        # if we created a windows requirements file, we can delete it until next time
        if windows_requirements_file_path:
            try:
                # Ensure all file handles are closed
                import gc

                gc.collect()

                # Try to remove the file
                os.remove(windows_requirements_file_path)
                logger.debug(f"Successfully removed temporary file: {windows_requirements_file_path}")
            except PermissionError:
                logger.warning(f"Could not remove temporary file: {windows_requirements_file_path}. It may be in use.")
            except Exception as e:
                logger.warning(f"An error occurred while trying to remove {windows_requirements_file_path}: {str(e)}")

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
