from __future__ import annotations

import pytest
from packaging.version import InvalidVersion

import storytoolkitai.core.post_update as post_update_module
from storytoolkitai.core.versioning import is_update_available, parse_version


def test_development_version_is_newer_than_previous_release() -> None:
    """The version 1 development line follows the previous 0.x release."""

    assert parse_version("1.0.0.dev0") > parse_version("0.25.1")


def test_final_release_is_newer_than_development_release() -> None:
    """The final 1.0.0 release must update a 1.0.0.dev0 installation."""

    assert parse_version("1.0.0") > parse_version("1.0.0.dev0")


def test_development_build_numbers_are_ordered() -> None:
    """Later development build numbers compare as newer builds."""

    assert parse_version("1.0.0.dev1") > parse_version("1.0.0.dev0")


def test_github_tag_prefix_is_accepted() -> None:
    """GitHub-style release tags compare like normal version strings."""

    assert parse_version("v1.0.0") == parse_version("1.0.0")


def test_surrounding_whitespace_is_ignored() -> None:
    """Whitespace from a remote version response is harmless."""

    assert parse_version("  1.0.0.dev0\n") == parse_version("1.0.0.dev0")


def test_invalid_version_is_rejected() -> None:
    """Malformed versions should not silently produce an ordering."""

    with pytest.raises(InvalidVersion):
        parse_version("not-a-version")


def test_development_build_skips_post_update_tasks(
    monkeypatch,
) -> None:
    """
    A development checkout must not migrate user data or advance last_update.
    """

    calls: list[bool] = []

    def post_update_1_0_0(is_standalone: bool = False) -> None:
        calls.append(is_standalone)

    monkeypatch.setattr(
        post_update_module,
        "post_update_functions",
        {
            "1.0.0": post_update_1_0_0,
        },
    )

    result = post_update_module.post_update(
        current_version="1.0.0.dev0",
        last_version="0.25.1",
        is_standalone=False,
    )

    assert result is False
    assert calls == []


def test_final_release_runs_version_1_post_update(
    monkeypatch,
) -> None:
    """The final release runs migrations that were deferred during dev."""

    calls: list[bool] = []

    def post_update_1_0_0(is_standalone: bool = False) -> None:
        calls.append(is_standalone)

    monkeypatch.setattr(
        post_update_module,
        "post_update_functions",
        {
            "1.0.0": post_update_1_0_0,
        },
    )

    result = post_update_module.post_update(
        current_version="1.0.0",
        last_version="0.25.1",
        is_standalone=True,
    )

    assert result is True
    assert calls == [True]

def test_stable_installation_ignores_online_development_version() -> None:
    """
    Stable users must not be offered the version 1 development branch.
    """

    assert is_update_available(
        local_value="0.25.2",
        online_value="1.0.0.dev0",
    ) is False


def test_development_installation_accepts_final_release() -> None:
    """
    The final 1.0.0 release is newer than its development build.
    """

    assert is_update_available(
        local_value="1.0.0.dev0",
        online_value="1.0.0",
    ) is True


def test_stable_installation_accepts_newer_stable_release() -> None:
    """Normal stable updates remain available."""

    assert is_update_available(
        local_value="0.25.2",
        online_value="1.0.0",
    ) is True


def test_equal_version_is_not_an_update() -> None:
    """The currently installed release is not offered again."""

    assert is_update_available(
        local_value="0.25.2",
        online_value="0.25.2",
    ) is False


def test_older_online_version_is_not_an_update() -> None:
    """An older advertised version is never offered."""

    assert is_update_available(
        local_value="1.0.0.dev0",
        online_value="0.25.2",
    ) is False
