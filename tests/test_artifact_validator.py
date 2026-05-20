import pytest
from pathlib import Path
from flowctl.artifact_validator import validate_artifacts


def test_validate_workflow_prefix(tmp_path):
    """Output with workflow: prefix should resolve to workflow_dir."""
    workflow_dir = tmp_path / "flows"
    workflow_dir.mkdir()
    memory_dir = workflow_dir / "memory"
    memory_dir.mkdir()
    
    output_file = memory_dir / "ba.md"
    output_file.write_text("test content")
    
    errors = validate_artifacts(
        {"memory_update": "workflow:memory/ba.md"},
        run_dir=tmp_path / "runs/test",
        workflow_dir=workflow_dir,
        repo_dir=None,
    )
    
    assert len(errors) == 0


def test_validate_repo_prefix(tmp_path):
    """Output with repo: prefix should resolve to repo_dir."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    
    output_file = repo_dir / "ARCHITECTURE.md"
    output_file.write_text("test content")
    
    errors = validate_artifacts(
        {"arch": "repo:ARCHITECTURE.md"},
        run_dir=tmp_path / "runs/test",
        workflow_dir=tmp_path / "flows",
        repo_dir=repo_dir,
    )
    
    assert len(errors) == 0


def test_validate_missing_file_workflow_prefix(tmp_path):
    """Missing file with workflow: prefix should report error."""
    workflow_dir = tmp_path / "flows"
    workflow_dir.mkdir()
    
    errors = validate_artifacts(
        {"memory": "workflow:memory/ba.md"},
        run_dir=tmp_path / "runs/test",
        workflow_dir=workflow_dir,
    )
    
    assert len(errors) == 1
    assert "memory" in errors[0]
    assert "missing" in errors[0]


def test_validate_missing_file_repo_prefix(tmp_path):
    """Missing file with repo: prefix should report error."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    
    errors = validate_artifacts(
        {"arch": "repo:ARCHITECTURE.md"},
        run_dir=tmp_path / "runs/test",
        workflow_dir=tmp_path / "flows",
        repo_dir=repo_dir,
    )
    
    assert len(errors) == 1
    assert "arch" in errors[0]
    assert "missing" in errors[0]


def test_validate_empty_file_workflow_prefix(tmp_path):
    """Empty file with workflow: prefix should report error."""
    workflow_dir = tmp_path / "flows"
    workflow_dir.mkdir()
    memory_dir = workflow_dir / "memory"
    memory_dir.mkdir()
    
    output_file = memory_dir / "ba.md"
    output_file.write_text("")
    
    errors = validate_artifacts(
        {"memory": "workflow:memory/ba.md"},
        run_dir=tmp_path / "runs/test",
        workflow_dir=workflow_dir,
    )
    
    assert len(errors) == 1
    assert "memory" in errors[0]
    assert "empty" in errors[0]


def test_validate_empty_file_repo_prefix(tmp_path):
    """Empty file with repo: prefix should report error."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    
    output_file = repo_dir / "ARCHITECTURE.md"
    output_file.write_text("")
    
    errors = validate_artifacts(
        {"arch": "repo:ARCHITECTURE.md"},
        run_dir=tmp_path / "runs/test",
        workflow_dir=tmp_path / "flows",
        repo_dir=repo_dir,
    )
    
    assert len(errors) == 1
    assert "arch" in errors[0]
    assert "empty" in errors[0]


def test_validate_run_prefix_missing(tmp_path):
    """Missing file with run: prefix (or no prefix) should report error."""
    run_dir = tmp_path / "runs/test"
    run_dir.mkdir(parents=True)
    
    errors = validate_artifacts(
        {"design": "design.md"},
        run_dir=run_dir,
    )
    
    assert len(errors) == 1
    assert "design" in errors[0]
    assert "missing" in errors[0]


def test_validate_multiple_errors(tmp_path):
    """Validator should collect all errors, not stop at first."""
    run_dir = tmp_path / "runs/test"
    run_dir.mkdir(parents=True)
    workflow_dir = tmp_path / "flows"
    workflow_dir.mkdir()
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    
    (run_dir / "design.md").write_text("content")
    
    errors = validate_artifacts(
        {
            "design": "design.md",
            "missing_run": "missing.md",
            "missing_workflow": "workflow:memory/ba.md",
            "missing_repo": "repo:ARCHITECTURE.md",
        },
        run_dir=run_dir,
        workflow_dir=workflow_dir,
        repo_dir=repo_dir,
    )
    
    assert len(errors) == 3
