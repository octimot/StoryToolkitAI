from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
UI_ROOT = PROJECT_ROOT / "storytoolkitai" / "ui"

FORBIDDEN_RESOLVE_FRAGMENTS = (
    "NLE.",
    ".resolve_api",
    "MotsResolve.",
)


def test_ui_does_not_access_resolve_processing_internals():
    violations = []

    for file_path in sorted(UI_ROOT.rglob("*.py")):
        source = file_path.read_text(
            encoding="utf-8",
        )

        for fragment in FORBIDDEN_RESOLVE_FRAGMENTS:
            if fragment not in source:
                continue

            violations.append(
                "{} contains {!r}".format(
                    file_path.relative_to(PROJECT_ROOT),
                    fragment,
                )
            )

    assert not violations, (
        "UI code must access Resolve through StoryToolkitEngine:\n"
        + "\n".join(violations)
    )
