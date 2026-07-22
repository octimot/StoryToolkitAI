"""Architecture tests for advanced search ownership."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SEARCH_SOURCE_PATH = (
    PROJECT_ROOT
    / "storytoolkitai"
    / "core"
    / "toolkit_ops"
    / "search.py"
)

TK_UI_SOURCE_PATH = (
    PROJECT_ROOT
    / "storytoolkitai"
    / "ui"
    / "toolkit_ui.py"
)


def read_source(path: Path) -> str:
    """Read one source file without importing its heavyweight dependencies."""

    return path.read_text(encoding="utf-8")


def test_search_processing_does_not_receive_toolkit_ops():
    """Search processors must depend only on their narrow SearchConfig."""

    search_source = read_source(SEARCH_SOURCE_PATH)

    assert "toolkit_ops_obj" not in search_source
    assert "self.toolkit_ops_obj" not in search_source
    assert "self.stAI" not in search_source


def test_tk_ui_does_not_construct_search_processors():
    """Tk must ask StoryToolkitEngine to create search processors."""

    ui_source = read_source(TK_UI_SOURCE_PATH)

    assert "TextSearch(" not in ui_source
    assert "VideoSearch(" not in ui_source


def test_tk_ui_does_not_keep_live_search_processors():
    """Tk windows and callbacks must retain only an engine search ID."""

    ui_source = read_source(TK_UI_SOURCE_PATH)

    assert "text_search_item" not in ui_source
    assert "video_search_item" not in ui_source


def test_tk_ui_does_not_prepare_search_processing():
    """Corpus and model preparation belong to the engine."""

    ui_source = read_source(TK_UI_SOURCE_PATH)

    assert ".prepare_search_corpus(" not in ui_source
    assert ".load_index_paths(" not in ui_source
