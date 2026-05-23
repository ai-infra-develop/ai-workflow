from pathlib import Path

PREFIX_RUN = "run:"
PREFIX_WORKFLOW = "workflow:"
PREFIX_REPO = "repo:"
DEFAULT_PREFIX = PREFIX_RUN


def parse_path_prefix(filename: str) -> tuple[str, str]:
    """Extract prefix and relative path from filename.
    
    Args:
        filename: Filename with optional prefix (e.g., "run:file.md", "workflow:mem/ba.md")
        
    Returns:
        Tuple of (prefix, relative_path)
        prefix is one of: "run:", "workflow:", "repo:"
    """
    if filename.startswith(PREFIX_WORKFLOW):
        return PREFIX_WORKFLOW, filename[len(PREFIX_WORKFLOW):]
    elif filename.startswith(PREFIX_REPO):
        return PREFIX_REPO, filename[len(PREFIX_REPO):]
    elif filename.startswith(PREFIX_RUN):
        return PREFIX_RUN, filename[len(PREFIX_RUN):]
    return DEFAULT_PREFIX, filename


def resolve_prefixed_path(
    filename: str,
    run_dir: Path,
    workflow_dir: Path | None = None,
    repo_dir: Path | None = None,
) -> Path:
    """Resolve a prefixed filename to absolute path.
    
    Args:
        filename: Filename with optional prefix
        run_dir: Base directory for run: prefix (and fallback)
        workflow_dir: Base directory for workflow: prefix (optional)
        repo_dir: Base directory for repo: prefix (optional)
        
    Returns:
        Resolved absolute Path
    """
    prefix, rel_path = parse_path_prefix(filename)
    
    if prefix == PREFIX_WORKFLOW:
        base_dir = workflow_dir or run_dir
    elif prefix == PREFIX_REPO:
        base_dir = repo_dir or run_dir
    else:
        base_dir = run_dir
    
    return base_dir / rel_path