from storytoolkitai.core.toolkit_ops.document import Document

# Document is a small, low-dependency object that loads UTF-8-with-BOM text 
# and records its path, name, text, and existence state.

def test_document_loads_utf8_text(tmp_path) -> None:
    document_path = tmp_path / "notes.txt"
    document_path.write_text(
        "First line\nSecond line",
        encoding="utf-8-sig",
    )

    document = Document(str(document_path))

    assert document.exists is True
    assert document.name == "notes.txt"
    assert document.text == "First line\nSecond line"
    assert document.document_file_path == str(document_path)


def test_missing_document_is_reported_as_not_existing(tmp_path) -> None:
    document_path = tmp_path / "missing.txt"

    document = Document(str(document_path))

    assert document.exists is False
    assert document.text == ""
