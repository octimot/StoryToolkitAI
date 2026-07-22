import json
from argparse import Namespace

import pytest

from storytoolkitai.ui.toolkit_cli import toolkit_CLI


class FakeParser:
    """
    Small parser replacement that exposes argparse-style validation errors.
    """

    def error(self, message):
        raise ValueError(message)


class FakeEngine:

    def __init__(self):
        self.connection_result = {
            'ok': True,
            'code': None,
            'message': None,
            'data': {
                'connected': True,
            },
        }
        self.timeline_result = {
            'ok': True,
            'code': None,
            'message': None,
            'data': {},
        }
        self.job_result = {
            'ok': True,
            'code': None,
            'message': None,
            'data': {},
        }
        self.calls = []

    def ensure_resolve_connection(
        self,
        *,
        timeout_seconds=5.0,
        poll_interval=0.05,
    ):
        self.calls.append(
            (
                'ensure_resolve_connection',
                timeout_seconds,
            )
        )
        return self.connection_result

    def render_resolve_timeline(
        self,
        *,
        target_dir,
        render_options,
    ):
        self.calls.append(
            (
                'render_resolve_timeline',
                target_dir,
                render_options,
            )
        )
        return self.timeline_result

    def render_resolve_job(
        self,
        *,
        job_id,
        render_data=None,
    ):
        self.calls.append(
            (
                'render_resolve_job',
                job_id,
                render_data,
            )
        )
        return self.job_result


def _args(**overrides):
    values = {
        'output_dir': None,
        'resolve_render': None,
        'resolve_render_job': None,
        'resolve_render_data': None,
    }
    values.update(overrides)

    return Namespace(**values)


def test_timeline_render_uses_engine(tmp_path):
    engine = FakeEngine()
    parser = FakeParser()

    toolkit_CLI(
        args=_args(
            output_dir=str(tmp_path),
            resolve_render=(
                "render_preset='H.264 Master', "
                "start_render=True, add_date=False"
            ),
        ),
        parser=parser,
        engine=engine,
    )

    assert engine.calls == [
        (
            'ensure_resolve_connection',
            5.0,
        ),
        (
            'render_resolve_timeline',
            str(tmp_path),
            {
                'render_preset': 'H.264 Master',
                'start_render': True,
                'add_date': False,
            },
        ),
    ]

def test_render_job_uses_engine():
    engine = FakeEngine()
    parser = FakeParser()

    render_data = {
        'project_name': 'Test Project',
        'timeline_name': 'Test Timeline',
        'in_offset': 0,
    }

    toolkit_CLI(
        args=_args(
            resolve_render_job='job-123',
            resolve_render_data=json.dumps(render_data),
        ),
        parser=parser,
        engine=engine,
    )

    assert engine.calls == [
        (
            'ensure_resolve_connection',
            5.0,
        ),
        (
            'render_resolve_job',
            'job-123',
            render_data,
        ),
    ]


def test_connection_failure_does_not_start_timeline_render(tmp_path):
    engine = FakeEngine()
    engine.connection_result = {
        'ok': False,
        'code': 'resolve_unavailable',
        'message': 'Resolve is unavailable',
        'data': {
            'connected': False,
        },
    }

    toolkit_CLI(
        args=_args(
            output_dir=str(tmp_path),
            resolve_render="render_preset='H.264 Master'",
        ),
        parser=FakeParser(),
        engine=engine,
    )

    assert engine.calls == [
        (
            'ensure_resolve_connection',
            5.0,
        ),
    ]


def test_invalid_render_data_is_rejected():
    with pytest.raises(
        ValueError,
        match='valid JSON',
    ):
        toolkit_CLI(
            args=_args(
                resolve_render_job='job-123',
                resolve_render_data='{not-json}',
            ),
            parser=FakeParser(),
            engine=FakeEngine(),
        )


def test_timeline_render_requires_preset(tmp_path):
    with pytest.raises(
        ValueError,
        match='render_preset',
    ):
        toolkit_CLI(
            args=_args(
                output_dir=str(tmp_path),
                resolve_render='start_render=True',
            ),
            parser=FakeParser(),
            engine=FakeEngine(),
        )
