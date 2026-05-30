import click
import shutil
from pathlib import Path
from .path_resolver import resolve_paths
from .models import FlowctlConfig


def run_init(target: str | None, config_path: str | None = None, source_workflow_dir: str | None = None):
    """Initialize .flows/ directory structure in target repo.
    
    Args:
        target: Target repo directory (defaults to cwd)
        config_path: Config file path (optional, only used when target not specified)
        source_workflow_dir: Source workflow directory to copy (optional)
    
    If source_workflow_dir is provided, workflow files are copied into target/.flows/
    """
    base = Path(target or ".")
    
    # Validate source directory BEFORE creating .flows
    if source_workflow_dir:
        source_dir = Path(source_workflow_dir)
        if not source_dir.exists():
            raise click.ClickException(f"Source workflow directory not found: {source_dir}")
        
        required_subdirs = ["workflows"]
        
        missing_required = []
        for subdir in required_subdirs:
            if not (source_dir / subdir).exists():
                missing_required.append(subdir)
        
        if missing_required:
            raise click.ClickException(
                f"Source workflow directory must have subdirectories: {missing_required}\n"
                f"Expected structure:\n"
                f"  {source_dir}/\n"
                f"    workflows/\n"
                f"      workflow.yaml\n"
                f"    prompts/    (optional)\n"
                f"    skills/     (optional)\n"
                f"    scripts/    (optional)"
            )
    
    # When target is explicitly specified, always use it as base
    # When target is not specified, use config to resolve flows_dir
    if target:
        flows_dir = base / ".flows"
    elif config_path:
        _, workflow_dir, _ = resolve_paths(config_path, None, None)
        flows_dir = workflow_dir
    else:
        flows_dir = base / ".flows"
    
    dirs = [
        flows_dir,
        flows_dir / "workflows",
        flows_dir / "prompts",
        flows_dir / "skills",
        flows_dir / "scripts",
        flows_dir / "memory",
        flows_dir / "memory" / "local",
        flows_dir / "runs",
    ]
    
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        click.echo(f"Created: {d}")
    
    config_file = flows_dir / "config.yaml"
    if not config_file.exists():
        import yaml
        config = FlowctlConfig(repo_dir="..")
        with open(config_file, 'w') as f:
            yaml.dump(config.model_dump(), f)
        click.echo(f"Created: {config_file}")
    else:
        click.echo(f"Config exists: {config_file}")
    
    # Create .gitignore in repo root (not in .flows/)
    root_gitignore = base / ".gitignore"
    if not root_gitignore.exists():
        root_gitignore.write_text(
            "# Generated implementation\n"
            "src/\n"
        )
        click.echo(f"Created: {root_gitignore}")
    
    # Create .gitignore in .flows/ with * to ignore all contents
    flows_gitignore = flows_dir / ".gitignore"
    if not flows_gitignore.exists():
        flows_gitignore.write_text("*\n")
        click.echo(f"Created: {flows_gitignore}")
    
    # Copy workflow files from source directory
    if source_workflow_dir:
        source_dir = Path(source_workflow_dir)
        click.echo(f"Copying workflow files from {source_dir}")
        
        # Copy .flows/ directory structure
        for subdir in ["workflows", "prompts", "skills", "scripts"]:
            src_subdir = source_dir / subdir
            if src_subdir.exists():
                dst_subdir = flows_dir / subdir
                for f in src_subdir.glob("*"):
                    if f.is_file():
                        dest = dst_subdir / f.name
                        shutil.copy(f, dest)
                        if subdir == "scripts":
                            dest.chmod(0o755)
                            click.echo(f"  Copied: {subdir}/{f.name} (executable)")
                        else:
                            click.echo(f"  Copied: {subdir}/{f.name}")
        
        # Copy .claude/skills/ for opencode auto-loading
        claude_skills_src = source_dir / ".claude" / "skills"
        if claude_skills_src.exists():
            claude_skills_dst = base / ".claude" / "skills"
            claude_skills_dst.mkdir(parents=True, exist_ok=True)
            
            for skill_dir in claude_skills_src.iterdir():
                if skill_dir.is_dir():
                    dst_skill_dir = claude_skills_dst / skill_dir.name
                    dst_skill_dir.mkdir(parents=True, exist_ok=True)
                    for f in skill_dir.glob("*.md"):
                        shutil.copy(f, dst_skill_dir / f.name)
                        click.echo(f"  Copied: .claude/skills/{skill_dir.name}/{f.name}")
    
    click.echo(f"Initialized {flows_dir} in {base}")