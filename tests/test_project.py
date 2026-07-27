import json

from storytoolkitai.core.toolkit_ops.projects import Project


def test_project_loads_existing_project_file(tmp_path) -> None:
    project_path = tmp_path / "example-project"
    project_path.mkdir()

    project_data = {
        "name": "Example Project",
        "last_target_dir": "/example/export",
        "timelines": {
            "Timeline 1": {
                "timeline_fps": 24,
                "timeline_start_tc": "01:00:00:00",
            }
        },
        "transcriptions": ["/media/interview.transcription.json"],
        "stories": [],
        "documents": [],
    }

    (project_path / "project.json").write_text(
        json.dumps(project_data),
        encoding="utf-8",
    )

    project = Project(
        project_path=str(project_path),
        force_reload=True,
    )

    assert project.exists is True
    assert project.name == "Example Project"
    assert project.last_target_dir == "/example/export"
    assert project.transcriptions == [
        "/media/interview.transcription.json"
    ]
    assert project.to_dict() == project_data


def test_project_changes_can_be_saved_immediately(tmp_path) -> None:
    project_path = tmp_path / "example-project"
    project_path.mkdir()

    (project_path / "project.json").write_text(
        json.dumps(
            {
                "name": "Example Project",
                "transcriptions": [],
                "stories": [],
                "documents": [],
                "timelines": {},
            }
        ),
        encoding="utf-8",
    )

    project = Project(
        project_path=str(project_path),
        force_reload=True,
    )

    project.set("last_target_dir", "/new/export/path")

    assert project.is_dirty is True
    assert project.save_soon(sec=0)

    saved_data = json.loads(
        (project_path / "project.json").read_text(
            encoding="utf-8"
        )
    )

    assert saved_data["last_target_dir"] == "/new/export/path"
    assert project.is_dirty is False
