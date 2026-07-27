from argparse import Namespace

import pytest

from storytoolkitai.app import (
    RuntimeOptions,
    runtime_options_from_args,
)


def _args(**overrides):
    """
    Return the command-line values used by runtime_options_from_args.
    """

    values = {
        'mode': 'gui',
        'debug': False,
        'noresolve': False,
        'skip_python_check': False,
        'skip_update_check': False,
        'force_update_check': False,
    }
    values.update(overrides)

    return Namespace(**values)


def test_gui_runtime_defaults():
    options = runtime_options_from_args(
        _args(mode='gui')
    )

    assert options == RuntimeOptions(
        mode='gui',
        debug=False,
        disable_resolve=False,
        skip_python_check=False,
        resume_queue=True,
        check_api_key=True,
        check_updates=True,
    )


def test_cli_runtime_defaults():
    options = runtime_options_from_args(
        _args(mode='cli')
    )

    assert options == RuntimeOptions(
        mode='cli',
        debug=False,
        disable_resolve=False,
        skip_python_check=False,
        resume_queue=False,
        check_api_key=False,
        check_updates=False,
    )

def test_direct_runtime_flags_are_copied_to_runtime_options():
    options = runtime_options_from_args(
        _args(
            debug=True,
            noresolve=True,
            skip_python_check=True,
        )
    )

    assert options.debug is True
    assert options.disable_resolve is True
    assert options.skip_python_check is True


def test_skip_update_check_disables_gui_update_check():
    options = runtime_options_from_args(
        _args(
            mode='gui',
            skip_update_check=True,
        )
    )

    assert options.check_updates is False


@pytest.mark.parametrize(
    'mode, skip_update_check',
    [
        ('gui', False),
        ('gui', True),
        ('cli', False),
        ('cli', True),
    ],
)
def test_force_update_check_has_highest_precedence(
    mode,
    skip_update_check,
):
    options = runtime_options_from_args(
        _args(
            mode=mode,
            skip_update_check=skip_update_check,
            force_update_check=True,
        )
    )

    assert options.check_updates is True
