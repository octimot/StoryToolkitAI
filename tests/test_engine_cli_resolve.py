from storytoolkitai.core.engine import StoryToolkitEngine


class FakeEvents:

    def subscribe(self, listener):
        return None

    def unsubscribe(self, listener):
        return None


class FakeResolveOps:

    def __init__(self):
        self.events = FakeEvents()
        self.connected = True
        self.calls = []

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
            'data': {
                'result': True,
            },
        }
        self.job_result = {
            'ok': True,
            'code': None,
            'message': None,
            'data': {
                'job_id': 'job-123',
            },
        }

    def is_resolve_connected(self):
        self.calls.append(
            ('is_resolve_connected',)
        )
        return self.connected

    def ensure_resolve_connection(
        self,
        timeout_seconds=5.0,
        poll_interval=0.05,
    ):
        self.calls.append(
            (
                'ensure_resolve_connection',
                timeout_seconds,
                poll_interval,
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


def test_engine_reports_resolve_connection():
    operations = FakeResolveOps()
    engine = StoryToolkitEngine(operations)

    assert engine.is_resolve_connected() is True
    assert operations.calls == [
        ('is_resolve_connected',),
    ]


def test_engine_waits_for_resolve_through_processing():
    operations = FakeResolveOps()
    engine = StoryToolkitEngine(operations)

    result = engine.ensure_resolve_connection(
        timeout_seconds=3.0,
        poll_interval=0.1,
    )

    assert result['ok'] is True
    assert operations.calls == [
        (
            'ensure_resolve_connection',
            3.0,
            0.1,
        ),
    ]


def test_engine_returns_copied_connection_result():
    operations = FakeResolveOps()
    engine = StoryToolkitEngine(operations)

    result = engine.ensure_resolve_connection()
    result['data']['connected'] = False

    assert (
        operations.connection_result['data']['connected']
        is True
    )


def test_engine_renders_timeline_through_processing(tmp_path):
    operations = FakeResolveOps()
    engine = StoryToolkitEngine(operations)

    render_options = {
        'render_preset': 'H.264 Master',
        'start_render': True,
    }

    result = engine.render_resolve_timeline(
        target_dir=str(tmp_path),
        render_options=render_options,
    )

    assert result['ok'] is True
    assert operations.calls == [
        (
            'render_resolve_timeline',
            str(tmp_path),
            render_options,
        ),
    ]


def test_engine_renders_job_through_processing():
    operations = FakeResolveOps()
    engine = StoryToolkitEngine(operations)

    render_data = {
        'project_name': 'Test Project',
    }

    result = engine.render_resolve_job(
        job_id='job-123',
        render_data=render_data,
    )

    assert result['ok'] is True
    assert operations.calls == [
        (
            'render_resolve_job',
            'job-123',
            render_data,
        ),
    ]
