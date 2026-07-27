import os
from pathlib import Path

import storytoolkitai




def test_tests_use_isolated_user_data_path() -> None:
    """
    This protects against a future change accidentally causing tests 
    to write into the maintainer’s real StoryToolkitAI directory.
    """
    expected_path = Path(
        os.environ["STORYTOOLKITAI_USER_DATA_PATH"]
    ).resolve()

    actual_path = Path(storytoolkitai.USER_DATA_PATH).resolve()

    assert actual_path == expected_path
    assert actual_path.exists()
