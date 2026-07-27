import storytoolkitai.core.storytoolkitai as storytoolkitai_module
from storytoolkitai.core.storytoolkitai import StoryToolkitAI


class ImmediateThread:
    """
    Test replacement for Thread that runs its target synchronously.
    """

    def __init__(
        self,
        target=None,
        args=None,
        kwargs=None,
        daemon=None,
    ):
        self.target = target
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.daemon = daemon

    def start(self):
        if self.target is not None:
            self.target(
                *self.args,
                **self.kwargs,
            )


def _prepare_runtime_test(monkeypatch):
    calls = {
        'api': 0,
        'update': 0,
    }

    # do not execute migrations or write configuration files
    monkeypatch.setattr(
        storytoolkitai_module,
        'post_update',
        lambda **kwargs: False,
    )

    # return constructor defaults without touching the user config
    monkeypatch.setattr(
        StoryToolkitAI,
        'get_app_setting',
        lambda self, setting_name=None, default_if_none=None: default_if_none,
    )

    monkeypatch.setattr(
        StoryToolkitAI,
        'get_git_commit',
        staticmethod(lambda: None),
    )

    def check_api_thread(self, api_key=None):
        calls['api'] += 1

    def check_update(self):
        calls['update'] += 1
        return False, '1.0.0'

    monkeypatch.setattr(
        StoryToolkitAI,
        'check_api_thread',
        check_api_thread,
    )
    monkeypatch.setattr(
        StoryToolkitAI,
        'check_update',
        check_update,
    )
    monkeypatch.setattr(
        storytoolkitai_module,
        'Thread',
        ImmediateThread,
    )

    return calls


def test_runtime_can_enable_startup_checks(monkeypatch):
    calls = _prepare_runtime_test(monkeypatch)

    app = StoryToolkitAI(
        debug_mode=True,
        check_api_key=True,
        check_updates=True,
    )

    assert app.debug_mode is True
    assert calls == {
        'api': 1,
        'update': 1,
    }
    assert app.update_available is False
    assert app.online_version == '1.0.0'
    assert not hasattr(app, 'cli_args')


def test_runtime_can_disable_startup_checks(monkeypatch):
    calls = _prepare_runtime_test(monkeypatch)

    app = StoryToolkitAI(
        debug_mode=False,
        check_api_key=False,
        check_updates=False,
    )

    assert app.debug_mode is False
    assert calls == {
        'api': 0,
        'update': 0,
    }
    assert app.update_available is None
    assert app.online_version is None
    assert not hasattr(app, 'cli_args')
