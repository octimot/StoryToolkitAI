import json
import os

from storytoolkitai.core.logger import logger


class toolkit_CLI:

    def __init__(self, args, parser, engine):

        # the CLI uses only the public processing facade
        self.engine = engine

        # add "CLI" to the logger name
        logger.name = 'StAI_CLI'

        self.parser = parser

        self.command_parser(args=args)

    @staticmethod
    def _log_operation_error(result, default_message):
        """
        Log the message returned by an engine operation when available.
        """

        if isinstance(result, dict) and result.get('message'):
            logger.error(result['message'])

        else:
            logger.error(default_message)

    def command_parser(self, args):

        # remove any quotes from the output_dir argument
        if args.output_dir:
            args.output_dir = args.output_dir.replace("'", "").replace('"', "")

        # process the Resolve timeline render argument
        if args.resolve_render:
            return self.resolve_render(args=args)

        # process one existing Resolve render queue job
        if args.resolve_render_job:
            return self.resolve_render_job(args=args)

        return True

    def resolve_render_job(self, args):
        """
        Render an existing Resolve render queue job via the engine.
        """

        render_data = {}

        if args.resolve_render_data:

            # remove the start and end quotes from the render_data argument
            render_data_json = args.resolve_render_data.strip('"')

            # the render_data should be a JSON object that looks like:
            # {"project_name": "Project Name", "timeline_name": "Some Timeline",
            #  "in_offset": 0, ...}
            try:
                render_data = json.loads(render_data_json)

            except (TypeError, json.JSONDecodeError):
                logger.error(
                    'Unable to parse --resolve-render-data as JSON.',
                    exc_info=True,
                )
                self.parser.error(
                    '--resolve-render-data must contain valid JSON'
                )
                return False

            if not isinstance(render_data, dict):
                self.parser.error(
                    '--resolve-render-data must contain a JSON object'
                )
                return False

        logger.info(
            'Rendering Resolve job {} via CLI...'.format(
                args.resolve_render_job,
            )
        )

        # connection startup and waiting belong to processing
        connection_result = self.engine.ensure_resolve_connection(
            timeout_seconds=5.0,
        )

        if not connection_result.get('ok'):
            self._log_operation_error(
                connection_result,
                'Resolve is not connected. Please open Resolve and try again.',
            )
            return False

        render_result = self.engine.render_resolve_job(
            job_id=args.resolve_render_job,
            render_data=render_data,
        )

        if not render_result.get('ok'):
            self._log_operation_error(
                render_result,
                'Error rendering Resolve job.',
            )
            return False

        logger.info(
            'Rendering Resolve job {} via CLI completed.'.format(
                args.resolve_render_job,
            )
        )

        return True

    def resolve_render(self, args):
        """
        Render the current Resolve timeline via the engine.
        """

        if not args.output_dir:
            self.parser.error(
                '--resolve-render requires --output-dir'
            )
            return False

        if not os.path.isdir(args.output_dir):
            self.parser.error(
                '--output-dir does not exist: {}'.format(
                    args.output_dir,
                )
            )
            return False

        resolve_kwargs = {}

        try:

            # the format is:
            # KEY1=VALUE1, KEY2=VALUE2
            for item in args.resolve_render.split(', '):
                key, value = item.split('=', 1)

                key = key.strip()
                value = value.strip().strip("'").strip('"')

                if not key:
                    raise ValueError('Resolve render option has no key')

                # convert command-line boolean strings to real booleans
                if value.lower() == 'true':
                    value = True

                elif value.lower() == 'false':
                    value = False

                resolve_kwargs[key] = value

        except (AttributeError, ValueError):
            logger.error(
                'Unable to parse --resolve-render options.',
                exc_info=True,
            )
            self.parser.error(
                '--resolve-render must use KEY=VALUE pairs separated by ", "'
            )
            return False

        # a Resolve render preset is required by the existing render workflow
        if (
            'render_preset' not in resolve_kwargs
            or not resolve_kwargs['render_preset']
        ):
            self.parser.error(
                '--resolve-render requires render_preset'
            )
            return False

        logger.info('Rendering Resolve timeline via CLI...')

        # connection startup and waiting belong to processing
        connection_result = self.engine.ensure_resolve_connection(
            timeout_seconds=5.0,
        )

        if not connection_result.get('ok'):
            self._log_operation_error(
                connection_result,
                'Resolve is not connected. Please open Resolve and try again.',
            )
            return False

        render_result = self.engine.render_resolve_timeline(
            target_dir=args.output_dir,
            render_options=resolve_kwargs,
        )

        if not render_result.get('ok'):
            self._log_operation_error(
                render_result,
                'Error rendering Resolve timeline.',
            )
            return False

        logger.info('Rendering Resolve timeline via CLI completed.')

        return True


def run_cli(args, parser, engine):
    """
    Run the command-line interface using the public engine facade.
    """

    return toolkit_CLI(
        args=args,
        parser=parser,
        engine=engine,
    )
