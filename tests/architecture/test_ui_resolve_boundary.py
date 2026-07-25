import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
UI_ROOT = PROJECT_ROOT / "storytoolkitai" / "ui"

FORBIDDEN_RESOLVE_NAMES = {
    "MotsResolve",
    "NLE",
}
FORBIDDEN_RESOLVE_ATTRIBUTES = {
    "resolve_api",
}


def test_ui_does_not_access_resolve_processing_internals():
    violations = []

    for file_path in sorted(UI_ROOT.rglob("*.py")):
        tree = ast.parse(
            file_path.read_text(encoding="utf-8"),
            filename=str(file_path),
        )

        for node in ast.walk(tree):
            forbidden_reference = None

            if (
                isinstance(node, ast.Name)
                and node.id in FORBIDDEN_RESOLVE_NAMES
            ):
                forbidden_reference = node.id

            elif (
                isinstance(node, ast.Attribute)
                and node.attr in FORBIDDEN_RESOLVE_ATTRIBUTES
            ):
                forbidden_reference = node.attr

            if forbidden_reference is None:
                continue

            violations.append(
                "{}:{} references {}".format(
                    file_path.relative_to(PROJECT_ROOT),
                    node.lineno,
                    forbidden_reference,
                )
            )

    assert not violations, (
        "UI code must access Resolve through StoryToolkitEngine:\n"
        + "\n".join(violations)
    )
