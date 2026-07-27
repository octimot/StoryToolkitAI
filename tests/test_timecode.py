import pytest

from storytoolkitai.core.toolkit_ops.timecode import (
    sec_to_tc,
    tc_to_sec,
)

# The timecode helpers already contain explicit validation for input
# types and positive frame rates.

def test_sec_to_tc_requires_float_seconds() -> None:
    with pytest.raises(TypeError):
        sec_to_tc(1, fps=24)


@pytest.mark.parametrize("fps", [0, -1, -24.0])
def test_sec_to_tc_requires_positive_fps(fps) -> None:
    with pytest.raises(ValueError):
        sec_to_tc(1.0, fps=fps)


def test_tc_to_sec_requires_string_timecode() -> None:
    with pytest.raises(TypeError):
        tc_to_sec(100, fps=24)


@pytest.mark.parametrize("fps", [0, -1, -24.0])
def test_tc_to_sec_requires_positive_fps(fps) -> None:
    with pytest.raises(ValueError):
        tc_to_sec("00:00:01:00", fps=fps)
