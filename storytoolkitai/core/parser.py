import argparse
import os

def create_parser():
    """
    We use this function to add the command line arguments to the parser to keep the main function clean.
    """

    parser = argparse.ArgumentParser(description="Story Toolkit AI")
    parser.add_argument("--mode", choices=["gui", "cli"], default="gui", help="Choose the mode to run the application")
    parser.add_argument("--debug", action='store_true', help="Enable debug mode")
    parser.add_argument("--noresolve", action='store_true', help="Disable Resolve API")
    parser.add_argument("--skip-python-check", action='store_true', help="Skips the Python version check")
    parser.add_argument("--skip-update-check", action='store_true', help="Does not check for updates")
    parser.add_argument("--force-update-check", action='store_true', help="Forces an update check")

    # CLI-focused arguments
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

    return parser, args