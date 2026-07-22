"""
Application runtime options and object construction.

Command-line arguments are converted into explicit runtime decisions here.
Processing objects receive those decisions directly and do not inspect
argparse namespaces or command-line flags themselves.
"""

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class RuntimeOptions:
    """
    Runtime decisions derived from the command-line arguments.

    These values describe how this application session should behave.
    They intentionally contain no argparse-specific objects.
    """

    mode: Literal["gui", "cli"]
    debug: bool
    disable_resolve: bool
    resume_queue: bool
    check_api_key: bool
    check_updates: bool


def runtime_options_from_args(args: Any) -> RuntimeOptions:
    """
    Convert parsed command-line arguments into runtime decisions.

    The command-line parser remains responsible for validating user input.
    This function is responsible only for deciding how the application
    should be constructed for the selected mode.
    """

    # an explicitly forced update check takes precedence over both CLI mode
    # and --skip-update-check
    check_updates = bool(
        args.force_update_check
        or (
            args.mode != "cli"
            and not args.skip_update_check
        )
    )

    # CLI executions are intended to be short-lived and headless, so they
    # do not restore the processing queue or start background API-key checks
    return RuntimeOptions(
        mode=args.mode,
        debug=bool(args.debug),
        disable_resolve=bool(args.noresolve),
        resume_queue=args.mode != "cli",
        check_api_key=args.mode != "cli",
        check_updates=check_updates,
    )


def build_runtime(options: RuntimeOptions):
    """
    Construct the application objects required for one runtime session.

    ToolkitOps is still returned temporarily because the Tk UI has not yet
    completed its version 1 migration. The CLI must use only the engine.
    """

    # keep FFmpeg discovery before the ToolkitOps import
    #
    # some processing modules inspect FFMPEG_BINARY while being imported,
    # so this preserves the startup order used before the refactor
    from storytoolkitai.core.storytoolkitai import StoryToolkitAI

    StoryToolkitAI.check_ffmpeg()

    from storytoolkitai.core.toolkit_ops.toolkit_ops import ToolkitOps
    from storytoolkitai.core.engine import StoryToolkitEngine

    # StoryToolkitAI receives application decisions instead of the complete
    # argparse namespace
    stAI = StoryToolkitAI(
        debug_mode=options.debug,
        check_api_key=options.check_api_key,
        check_updates=options.check_updates,
    )

    # ToolkitOps receives only the runtime decisions that affect processing
    toolkit_ops_obj = ToolkitOps(
        stAI=stAI,
        disable_resolve_api=options.disable_resolve,
        resume_queue=options.resume_queue,
    )

    # all first-party interfaces should use this public processing facade
    engine = StoryToolkitEngine(
        toolkit_ops_obj=toolkit_ops_obj,
    )

    # ToolkitOps is returned only for the temporary Tk compatibility path.
    # Remove it from this return value after the Step 11 UI migration.
    return stAI, toolkit_ops_obj, engine
