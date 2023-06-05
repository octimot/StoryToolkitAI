from storytoolkitai.core.logger import *
import json

class toolkit_CLI:

    def __init__(self, args, parser, toolkit_ops_obj, stAI):
        self.toolkit_ops_obj = toolkit_ops_obj
        self.stAI = stAI

        self.args_validation_error = False

        # add "CLI" to the logger name
        logger.name = 'StAI_CLI'

        self.parser = parser
        self.command_parser(args=args)

    def command_parser(self, args):

        # remove any quotes from the output_dir argument
        if args.output_dir:
            args.output_dir = args.output_dir.replace("'", "").replace('"', "")

        # process the resolve_render argument
        if args.resolve_render:

            self.resolve_render(args=args)

        elif args.resolve_render_job:

            render_data = {}
            if args.resolve_render_data:

                # remove the start and end quotes from the render_data argument
                render_data = args.resolve_render_data.strip('"')

                # the render_data should be a json string that looks like this:
                # {"project_name": "Project Name", "timeline_name": "Some Timeline", "in_offset": 0, ...}
                # convert the json string to a dictionary
                render_data = json.loads(render_data)

            try:
                logger.info('Rendering Resolve job {} via CLI...'.format(args.resolve_render_job))
                self.toolkit_ops_obj.resolve_api.render(render_jobs=[args.resolve_render_job],
                                                        resolve_objects=None,
                                                        stills=False,
                                                        render_data=render_data)
            except Exception:
                logger.error('Error rendering Resolve job.', exc_info=True)

    def resolve_render(self, args):
        """
        Render Resolve timeline via CLI.
        """

        # this only works if we have the output_dir argument and the resolve_render argument
        if not args.output_dir:
            logger.error('Please specify the output directory.')
            self.parser.error("--resolve-render requires --output_dir")
            self.args_validation_error = True

        if not self.toolkit_ops_obj.resolve_api:
            logger.error('Resolve is not connected. Please open Resolve and try again.')
            return

        # parse the resolve_render argument
        # we should get it in a KEY=VALUE format, which looks like this: "KEY1='VALUE1', KEY2='VALUE2'", ...
        # we need convert it to a dictionary
        resolve_render_dict = dict(item.split("=") for item in args.resolve_render.split(", "))

        resolve_kwargs = dict()

        # remove the quotes from the values and the keys
        for key, value in resolve_render_dict.items():

            # remove the single and the double quotes from the keys
            key = key.replace("'", "").replace('"', "")

            # strip the single and the double quotes from the values
            value = value.replace("'", "").replace('"', "")

            # convert True and False strings to booleans
            if value == 'True':
                value = True
            elif value == 'False':
                value = False

            resolve_kwargs[key] = value

        # if no render_preset was sent, abort
        if 'render_preset' not in resolve_kwargs:
            logger.error('Please specify the render preset.')
            self.parser.error("--resolve-render requires --render_preset")
            self.args_validation_error = True

        if self.args_validation_error:
            return

        try:
            logger.info('Rendering Resolve timeline via CLI...')
            self.toolkit_ops_obj.resolve_api.render_timeline(target_dir=args.output_dir, **resolve_kwargs)

            logger.info('Rendering Resolve timeline via CLI completed.')

        except Exception:
            logger.error('Error rendering Resolve timeline.', exc_info=True)

def run_cli(args, parser, toolkit_ops_obj, stAI):

    # initialize CLI
    toolkit_CLI(args, parser, toolkit_ops_obj=toolkit_ops_obj, stAI=stAI)

