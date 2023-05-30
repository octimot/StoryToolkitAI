import argparse
from storytoolkitai.core import toolkit_ops
from storytoolkitai.integrations.mots_resolve import MotsResolve
from storytoolkitai.core.logger import *

class toolkit_CLI:

    def __init__(self, args, toolkit_ops_obj, stAI):
        self.toolkit_ops_obj = toolkit_ops_obj
        self.stAI = stAI

        self.command_parser(args=args)

    def command_parser(self, args):

        if args.render_resolve_timeline:

            render_preset = self.stAI.get_app_setting(setting_name='transcription_render_preset',
                                                 default_if_none='transcription_WAV')

            if not self.toolkit_ops_obj.resolve_api:
                logger.error('Resolve is not connected. Please open Resolve and try again.')
                return

            try:
                logger.info('Rendering Resolve timeline')
                self.toolkit_ops_obj.resolve_api.render_timeline(
                    args.output_dir, render_preset, True, False, False, True)

            except Exception:
                logger.error('Error rendering Resolve timeline.', exc_info=True)

def run_cli(args, toolkit_ops_obj, stAI):

    # initialize CLI
    toolkit_CLI(args, toolkit_ops_obj=toolkit_ops_obj, stAI=stAI)

