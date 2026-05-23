from pathlib import Path
from flowctl.path_utils import resolve_prefixed_path


def validate_artifacts(
    outputs: dict[str, str],
    run_dir: Path,
    workflow_dir: Path | None = None,
    repo_dir: Path | None = None,
) -> list[str]:
    """Validate output artifacts exist at resolved paths."""
    errors: list[str] = []
    for key, filename in outputs.items():
        resolved_path = resolve_prefixed_path(filename, run_dir, workflow_dir, repo_dir)
        
        if not resolved_path.exists():
            errors.append(f"Output '{key}' missing: {resolved_path}")
        elif resolved_path.stat().st_size == 0:
            errors.append(f"Output '{key}' is empty: {resolved_path}")
    return errors