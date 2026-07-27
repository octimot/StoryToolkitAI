from __future__ import annotations

import pytest
from packaging.version import InvalidVersion

import storytoolkitai.core.post_update as post_update_module
import storytoolkitai.core.storytoolkitai as storytoolkitai_module
from storytoolkitai.core.storytoolkitai import StoryToolkitAI
from storytoolkitai.core.versioning import is_update_available, parse_version


class _UpdateResponse:
    """Minimal requests response used by direct update-check tests."""

    def __init__(self, *, text: str = "", payload: dict | None = None) -> None:
        self.text = text
        self.payload = payload

    def json(self) -> dict | None:
        return self.payload


def _update_runtime(
    *,
    local_version: str,
    standalone: bool = False,
    ignored_version: str | bool = False,
) -> StoryToolkitAI:
    """Build only the runtime state needed by ``check_update``."""

    runtime = StoryToolkitAI.__new__(StoryToolkitAI)
    runtime.__version__ = local_version
    runtime.standalone = standalone
    runtime.get_app_setting = (
        lambda setting_name=None, default_if_none=None: ignored_version
    )
    return runtime


def _mock_source_version(monkeypatch, online_version: str) -> None:
    response = _UpdateResponse(
        text='__version__ = "{}"\n'.format(online_version)
    )
    monkeypatch.setattr(
        storytoolkitai_module,
        "get",
        lambda *args, **kwargs: response,
    )


def _mock_standalone_release(
    monkeypatch,
    *,
    online_version: str,
    assets: list[dict],
) -> None:
    response = _UpdateResponse(
        payload={
            "tag_name": "v{}".format(online_version),
            "assets": assets,
        },
    )
    monkeypatch.setattr(
        storytoolkitai_module,
        "get",
        lambda *args, **kwargs: response,
    )


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

def test_source_endpoint_without_quotes_fails_safely(
    monkeypatch,
) -> None:
    """A response without a quoted version is handled safely."""

    runtime = _update_runtime(local_version="1.0.0")
    response = _UpdateResponse(text="1.0.1")

    monkeypatch.setattr(
        storytoolkitai_module,
        "get",
        lambda *args, **kwargs: response,
    )

    assert runtime.check_update() == (False, None)


def test_invalid_version_is_rejected() -> None:
    """Malformed versions should not silently produce an ordering."""

    with pytest.raises(InvalidVersion):
        parse_version("not-a-version")


@pytest.mark.parametrize(
    "local_version, online_version",
    [
        ("0.25.1", "1.0.0"),
        ("1.0.0", "1.0.1"),
    ],
)
def test_source_installation_offers_newer_stable_version(
    monkeypatch,
    local_version: str,
    online_version: str,
) -> None:
    """Source users continue to receive newer stable releases."""

    runtime = _update_runtime(local_version=local_version)
    _mock_source_version(monkeypatch, online_version)

    assert runtime.check_update() == (True, online_version)


def test_stable_source_installation_ignores_development_version(
    monkeypatch,
) -> None:
    """The source update channel does not advertise development builds."""

    runtime = _update_runtime(local_version="1.0.0")
    _mock_source_version(monkeypatch, "1.0.1.dev0")

    assert runtime.check_update() == (False, "1.0.1.dev0")


def test_exact_ignored_version_is_suppressed(monkeypatch) -> None:
    """A user-selected skipped release is not offered again."""

    runtime = _update_runtime(
        local_version="1.0.0",
        ignored_version="1.0.1",
    )
    _mock_source_version(monkeypatch, "1.0.1")

    assert runtime.check_update() == (False, "1.0.1")


def test_later_version_after_ignored_version_is_offered(monkeypatch) -> None:
    """Skipping one release does not suppress subsequent releases."""

    runtime = _update_runtime(
        local_version="1.0.0",
        ignored_version="1.0.1",
    )
    _mock_source_version(monkeypatch, "1.0.2")

    assert runtime.check_update() == (True, "1.0.2")


def test_standalone_source_only_release_has_no_update(monkeypatch) -> None:
    """A release without packaged artifacts is not offered to standalone users."""

    runtime = _update_runtime(local_version="1.0.0", standalone=True)
    _mock_standalone_release(
        monkeypatch,
        online_version="1.0.1",
        assets=[],
    )

    assert runtime.check_update() == (False, "1.0.1")


def test_macos_standalone_matching_asset_is_offered(monkeypatch) -> None:
    """A macOS build matching the current architecture is offered."""

    runtime = _update_runtime(local_version="1.0.0", standalone=True)
    _mock_standalone_release(
        monkeypatch,
        online_version="1.0.1",
        assets=[{"name": "StoryToolkitAI-1.0.1-macOS-arm64.zip"}],
    )
    monkeypatch.setattr(storytoolkitai_module.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(storytoolkitai_module.platform, "machine", lambda: "arm64")

    assert runtime.check_update() == (True, "1.0.1")


def test_macos_standalone_non_matching_asset_is_not_offered(
    monkeypatch,
) -> None:
    """A macOS build for another architecture is not offered."""

    runtime = _update_runtime(local_version="1.0.0", standalone=True)
    _mock_standalone_release(
        monkeypatch,
        online_version="1.0.1",
        assets=[{"name": "StoryToolkitAI-1.0.1-macOS-x86_64.zip"}],
    )
    monkeypatch.setattr(storytoolkitai_module.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(storytoolkitai_module.platform, "machine", lambda: "arm64")

    assert runtime.check_update() == (False, "1.0.1")


def test_windows_standalone_matching_asset_is_offered(monkeypatch) -> None:
    """A Windows artifact is offered to standalone Windows users."""

    runtime = _update_runtime(local_version="1.0.0", standalone=True)
    _mock_standalone_release(
        monkeypatch,
        online_version="1.0.1",
        assets=[{"name": "StoryToolkitAI-1.0.1-Windows-x64.zip"}],
    )
    monkeypatch.setattr(storytoolkitai_module.platform, "system", lambda: "Windows")

    assert runtime.check_update() == (True, "1.0.1")


def test_malformed_endpoint_version_fails_safely(monkeypatch) -> None:
    """An invalid advertised version does not escape the update check."""

    runtime = _update_runtime(local_version="1.0.0")
    _mock_source_version(monkeypatch, "not-a-version")

    assert runtime.check_update() == (False, "not-a-version")


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


def test_source_endpoint_without_quotes_fails_safely(
    monkeypatch,
) -> None:
    """A response without a quoted version is handled safely."""

    runtime = _update_runtime(local_version="1.0.0")
    response = _UpdateResponse(text="1.0.1")

    monkeypatch.setattr(
        storytoolkitai_module,
        "get",
        lambda *args, **kwargs: response,
    )

    assert runtime.check_update() == (False, None)

def test_invalid_ignored_version_does_not_block_update(
    monkeypatch,
) -> None:
    runtime = _update_runtime(
        local_version="1.0.0",
        ignored_version="invalid-value",
    )
    _mock_source_version(monkeypatch, "1.0.1")

    assert runtime.check_update() == (True, "1.0.1")
