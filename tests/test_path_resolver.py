import pytest
from pathlib import Path
from flowctl.path_resolver import resolve_paths


def test_resolve_paths_defaults():
    """When no overrides and config missing, use hardcoded defaults."""
    run_dir, workflow_dir, repo_dir = resolve_paths(
        config_path=".flows/config.yaml",
        run_dir_override=None,
        workflow_dir_override=None,
    )
    
    assert run_dir == Path.cwd() / ".flows" / "runs"
    assert workflow_dir == Path.cwd() / ".flows"
    assert repo_dir is None


def test_resolve_paths_cli_overrides_defaults():
    """CLI options override default paths."""
    run_dir, workflow_dir, repo_dir = resolve_paths(
        config_path=".flows/config.yaml",
        run_dir_override="/tmp/custom-runs",
        workflow_dir_override="/shared/workflows",
    )
    
    assert run_dir == Path("/tmp/custom-runs")
    assert workflow_dir == Path("/shared/workflows")
    assert repo_dir is None


def test_resolve_paths_cli_overrides_config():
    """CLI options override config values."""
    import tempfile
    import yaml
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump({
            'preferred_executor': 'echo',
            'run_dir': '/config/runs',
            'workflow_dir': '/config/workflows',
        }, f)
        config_path = f.name
    
    try:
        run_dir, workflow_dir, repo_dir = resolve_paths(
            config_path=config_path,
            run_dir_override="/cli/runs",
            workflow_dir_override=None,
        )
        
        assert run_dir == Path("/cli/runs")
        assert workflow_dir == Path("/config/workflows")
        assert repo_dir is None
    finally:
        Path(config_path).unlink()


def test_resolve_paths_from_config():
    """Config values override defaults."""
    import tempfile
    import yaml
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump({
            'preferred_executor': 'echo',
            'run_dir': '/config/runs',
            'workflow_dir': '/config/workflows',
        }, f)
        config_path = f.name
    
    try:
        run_dir, workflow_dir, repo_dir = resolve_paths(
            config_path=config_path,
            run_dir_override=None,
            workflow_dir_override=None,
        )
        
        assert run_dir == Path("/config/runs")
        assert workflow_dir == Path("/config/workflows")
        assert repo_dir is None
    finally:
        Path(config_path).unlink()


def test_resolve_paths_relative_from_cwd():
    """Relative paths resolved from current working directory."""
    import tempfile
    import yaml
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump({
            'preferred_executor': 'echo',
            'run_dir': 'my-runs',
            'workflow_dir': 'my-workflows',
        }, f)
        config_path = f.name
    
    try:
        run_dir, workflow_dir, repo_dir = resolve_paths(
            config_path=config_path,
            run_dir_override=None,
            workflow_dir_override=None,
        )
        
        assert run_dir == Path.cwd() / "my-runs"
        assert workflow_dir == Path.cwd() / "my-workflows"
        assert repo_dir is None
    finally:
        Path(config_path).unlink()


def test_resolve_paths_with_repo_dir_cli():
    """CLI --repo-dir should override config."""
    run_dir, workflow_dir, repo_dir = resolve_paths(
        ".flows/config.yaml", None, None, repo_dir_override="/tmp/my-repo"
    )
    assert repo_dir == Path("/tmp/my-repo")


def test_resolve_paths_with_repo_dir_config(tmp_path):
    """Config repo_dir should be used if no CLI override."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("repo_dir: /tmp/config-repo")
    
    run_dir, workflow_dir, repo_dir = resolve_paths(
        str(config_file), None, None, repo_dir_override=None
    )
    assert repo_dir == Path("/tmp/config-repo")


def test_resolve_paths_repo_dir_none_without_config():
    """repo_dir should be None if not in config or CLI."""
    run_dir, workflow_dir, repo_dir = resolve_paths(
        ".flows/nonexistent.yaml", None, None, repo_dir_override=None
    )
    assert repo_dir is None


import tempfile


def test_relative_paths_resolve_from_repo_dir():
    """When repo_dir is set via CLI, relative run_dir/workflow_dir resolve from it."""
    run_dir, workflow_dir, repo_dir = resolve_paths(
        ".flows/config.yaml", None, None, repo_dir_override="/tmp/my-repo"
    )
    assert run_dir == Path("/tmp/my-repo/.flows/runs")
    assert workflow_dir == Path("/tmp/my-repo/.flows")
    assert repo_dir == Path("/tmp/my-repo")


def test_config_repo_dir_relative_resolves_from_config_parent():
    """Config repo_dir: .. resolves from config file's parent directory."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_dir = Path(tmp)
        flows_dir = repo_dir / ".flows"
        flows_dir.mkdir()
        config_file = flows_dir / "config.yaml"
        config_file.write_text("repo_dir: ..\nrun_dir: .flows/runs\nworkflow_dir: .flows\n")
        
        run_dir, workflow_dir, repo_dir_resolved = resolve_paths(
            str(config_file), None, None, None
        )
        
        assert repo_dir_resolved == repo_dir.resolve()
        assert run_dir == repo_dir.resolve() / ".flows" / "runs"
        assert workflow_dir == repo_dir.resolve() / ".flows"


def test_cli_repo_dir_relative_resolves_from_cwd():
    """CLI --repo-dir with relative path resolves from cwd."""
    run_dir, workflow_dir, repo_dir = resolve_paths(
        ".flows/config.yaml", None, None, repo_dir_override="relative-repo"
    )
    assert repo_dir == Path.cwd() / "relative-repo"
    assert run_dir == repo_dir / ".flows" / "runs"
    assert workflow_dir == repo_dir / ".flows"


def test_relative_paths_fallback_to_cwd_without_repo_dir():
    """When repo_dir not set, relative paths still resolve from cwd."""
    run_dir, workflow_dir, repo_dir = resolve_paths(
        ".flows/config.yaml", None, None, None
    )
    assert repo_dir is None
    assert run_dir == Path.cwd() / ".flows" / "runs"
    assert workflow_dir == Path.cwd() / ".flows"