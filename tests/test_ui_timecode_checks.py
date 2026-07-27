from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLKIT_UI_PATH = (
    PROJECT_ROOT
    / "storytoolkitai"
    / "ui"
    / "toolkit_ui.py"
)


def _load_timecode_lookup_method():
    source = TOOLKIT_UI_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(TOOLKIT_UI_PATH))
    toolkit_ui_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "toolkit_UI"
    )
    transcript_edit_class = next(
        node
        for node in toolkit_ui_class.body
        if isinstance(node, ast.ClassDef)
        and node.name == "TranscriptEdit"
    )
    method = next(
        node
        for node in transcript_edit_class.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "get_timecode_data_from_transcription"
    )

    test_class = ast.ClassDef(
        name="TestedTranscriptEdit",
        bases=[],
        keywords=[],
        body=[method],
        decorator_list=[],
    )
    module = ast.fix_missing_locations(
        ast.Module(body=[test_class], type_ignores=[])
    )
    namespace = {
        "Timecode": object,
        "logger": SimpleNamespace(debug=lambda *args: None),
        "messagebox": SimpleNamespace(),
    }
    exec(
        compile(module, str(TOOLKIT_UI_PATH), "exec"),
        namespace,
    )
    return namespace["TestedTranscriptEdit"], namespace["messagebox"]


def test_missing_timecode_list_prompts_once_before_falling_back():
    transcript_edit_class, messagebox = _load_timecode_lookup_method()
    prompt_calls = []
    messagebox.askyesno = lambda **kwargs: prompt_calls.append(kwargs) or False

    window = SimpleNamespace()
    transcription = SimpleNamespace(
        get_timecode_data=lambda: [None, None],
        transcription_file_path="interview.transcription.json",
    )
    transcript_edit = transcript_edit_class()
    transcript_edit.get_window_transcription = lambda window_id: transcription
    transcript_edit.toolkit_UI_obj = SimpleNamespace(
        get_window_by_id=lambda window_id: window,
        notify_via_messagebox=lambda **kwargs: None,
    )

    assert transcript_edit.get_timecode_data_from_transcription("transcript") == (
        None,
        None,
    )
    assert len(prompt_calls) == 1
    assert window.asked_for_timecode is True


def test_source_has_no_identity_comparisons_against_container_literals():
    violations = []

    for path in sorted((PROJECT_ROOT / "storytoolkitai").rglob("*.py")):
        tree = ast.parse(
            path.read_text(encoding="utf-8"),
            filename=str(path),
        )

        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue

            operands = [node.left, *node.comparators]

            for operator, left, right in zip(
                node.ops,
                operands,
                operands[1:],
            ):
                if not isinstance(operator, (ast.Is, ast.IsNot)):
                    continue

                if isinstance(
                    left,
                    (ast.Tuple, ast.List, ast.Dict, ast.Set),
                ) or isinstance(
                    right,
                    (ast.Tuple, ast.List, ast.Dict, ast.Set),
                ):
                    violations.append(
                        "{}:{}: {}".format(
                            path.relative_to(PROJECT_ROOT),
                            node.lineno,
                            ast.unparse(node),
                        )
                    )

    assert not violations, (
        "Container literals must be compared by value, length, or truth value:\n"
        + "\n".join(violations)
    )
