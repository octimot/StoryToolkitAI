from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path


# this code runs before pytest imports the test modules.
_TEST_USER_DATA_PATH = Path(
    tempfile.mkdtemp(prefix="storytoolkitai-tests-")
)

os.environ["STORYTOOLKITAI_USER_DATA_PATH"] = str(
    _TEST_USER_DATA_PATH
)


def pytest_unconfigure(config) -> None:
    """Close StoryToolkitAI log files and remove temporary test data."""

    logger = logging.getLogger("StAI")

    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)

    shutil.rmtree(_TEST_USER_DATA_PATH, ignore_errors=True)
