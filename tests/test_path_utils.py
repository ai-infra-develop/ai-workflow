import pytest
from pathlib import Path
from flowctl.path_utils import parse_path_prefix, resolve_prefixed_path


def test_parse_path_prefix_no_prefix():
    assert parse_path_prefix("file.md") == ("run:", "file.md")


def test_parse_path_prefix_run_prefix():
    assert parse_path_prefix("run:file.md") == ("run:", "file.md")


def test_parse_path_prefix_workflow_prefix():
    assert parse_path_prefix("workflow:memory/ba.md") == ("workflow:", "memory/ba.md")


def test_parse_path_prefix_repo_prefix():
    assert parse_path_prefix("repo:ARCHITECTURE.md") == ("repo:", "ARCHITECTURE.md")


def test_parse_path_prefix_nested_path():
    assert parse_path_prefix("workflow:memory/sub/ba.md") == ("workflow:", "memory/sub/ba.md")


def test_resolve_prefixed_path_run_default():
    run_dir = Path("/tmp/run")
    result = resolve_prefixed_path("file.md", run_dir)
    assert result == run_dir / "file.md"


def test_resolve_prefixed_path_run_explicit():
    run_dir = Path("/tmp/run")
    result = resolve_prefixed_path("run:file.md", run_dir)
    assert result == run_dir / "file.md"


def test_resolve_prefixed_path_workflow():
    run_dir = Path("/tmp/run")
    workflow_dir = Path("/tmp/workflow")
    result = resolve_prefixed_path("workflow:memory/ba.md", run_dir, workflow_dir)
    assert result == workflow_dir / "memory/ba.md"


def test_resolve_prefixed_path_repo():
    run_dir = Path("/tmp/run")
    repo_dir = Path("/tmp/repo")
    result = resolve_prefixed_path("repo:ARCHITECTURE.md", run_dir, repo_dir=repo_dir)
    assert result == repo_dir / "ARCHITECTURE.md"


def test_resolve_prefixed_path_workflow_fallback_to_run():
    run_dir = Path("/tmp/run")
    result = resolve_prefixed_path("workflow:file.md", run_dir, workflow_dir=None)
    assert result == run_dir / "file.md"


def test_resolve_prefixed_path_repo_fallback_to_run():
    run_dir = Path("/tmp/run")
    result = resolve_prefixed_path("repo:file.md", run_dir, repo_dir=None)
    assert result == run_dir / "file.md"