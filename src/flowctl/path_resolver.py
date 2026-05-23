from pathlib import Path
from .models import FlowctlConfig


def resolve_paths(
    config_path: str,
    run_dir_override: str | None,
    workflow_dir_override: str | None,
    repo_dir_override: str | None = None,
) -> tuple[Path, Path, Path | None]:
    """Resolve run_dir, workflow_dir, and repo_dir from config + CLI overrides.
    
    Precedence: CLI > config > defaults
    Resolution order: repo_dir first, then run_dir/workflow_dir from repo_dir or cwd
    
    Returns:
        Tuple of (run_dir, workflow_dir, repo_dir or None)
    """
    config = _load_config(config_path)
    config_file_dir = Path(config_path).parent.resolve()
    
    run_dir = run_dir_override or config.run_dir or ".flows/runs"
    workflow_dir = workflow_dir_override or config.workflow_dir or ".flows"
    repo_dir = repo_dir_override or config.repo_dir
    
    repo_dir_path: Path | None = None
    if repo_dir:
        repo_dir_path = Path(repo_dir)
        if not repo_dir_path.is_absolute():
            if repo_dir_override:
                repo_dir_path = (Path.cwd() / repo_dir_path).resolve()
            else:
                repo_dir_path = (config_file_dir / repo_dir_path).resolve()
    
    base_dir = repo_dir_path or Path.cwd()
    
    run_dir_path = Path(run_dir)
    workflow_dir_path = Path(workflow_dir)
    
    if not run_dir_path.is_absolute():
        run_dir_path = (base_dir / run_dir_path).resolve()
    if not workflow_dir_path.is_absolute():
        workflow_dir_path = (base_dir / workflow_dir_path).resolve()
    
    return run_dir_path, workflow_dir_path, repo_dir_path


def _load_config(config_path: str) -> FlowctlConfig:
    """Load config from file, return defaults if not found."""
    path = Path(config_path)
    if path.exists():
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return FlowctlConfig(**data)
    return FlowctlConfig()