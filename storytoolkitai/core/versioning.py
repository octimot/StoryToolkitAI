"""
Helpers for parsing and comparing StoryToolkitAI versions.

StoryToolkitAI uses Python's PEP 440 version format. This supports stable
versions such as ``1.0.0`` and development versions such as
``1.0.0.dev0``.
"""

from packaging.version import InvalidVersion, Version


def parse_version(value: str) -> Version:
    """
    Parse a StoryToolkitAI version into a comparison-aware Version object.

    A single leading ``v`` is accepted because GitHub release tags commonly
    use names such as ``v1.0.0``. The returned object follows PEP 440 ordering.

    Args:
        value:
            Version string such as ``1.0.0``, ``1.0.0.dev0``, or ``v1.0.0``.

    Returns:
        A parsed ``packaging.version.Version`` object.

    Raises:
        InvalidVersion:
            If the value is not a valid PEP 440 version.
    """

    if not isinstance(value, str):
        raise InvalidVersion(repr(value))

    normalized_value = value.strip()

    # Strip only a leading release-tag prefix. Do not use replace("v", ""),
    # because that would also corrupt the "v" in a suffix such as ".dev0".
    if normalized_value[:1].lower() == "v":
        normalized_value = normalized_value[1:]

    return Version(normalized_value)

def is_update_available(
    local_value: str,
    online_value: str,
) -> bool:
    """
    Return whether an online version should be offered as a normal update.

    Development releases are intentionally excluded from the normal update
    channel. They may still be installed manually by maintainers or testers.

    Args:
        local_value:
            Version currently running.

        online_value:
            Version advertised by the update service.

    Returns:
        ``True`` only when the online version is a newer non-development
        release.
    """

    local_version = parse_version(local_value)
    online_version = parse_version(online_value)

    if online_version.is_devrelease:
        return False

    return online_version > local_version
