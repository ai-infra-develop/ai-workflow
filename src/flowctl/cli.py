import click
from pathlib import Path
from .init_cmd import run_init
from .loader import load_workflow, validate_workflow
from .runner import run_workflow
from .executors import create_default_registry
from .path_resolver import resolve_paths


@click.group()
def main():
    pass


@main.command()
@click.option("--target", default=None, help="Target directory")
@click.option("--config", default=None, help="Config file path (only used when target not specified)")
@click.option("--source-workflow-dir", default=None, help="Source workflow directory to copy")
def init(target, config, source_workflow_dir):
    """Bootstrap .flows/ directory in the target project.
    
    If --source-workflow-dir is provided, workflow files are copied into target/.flows/
    """
    run_init(target, config, source_workflow_dir)


@main.command()
@click.option("--target", default=None)
@click.option("--config", default=".flows/config.yaml", help="Config file path")
def upgrade(target, config):
    """Reconcile .flows/config.yaml schema for new framework versions."""
    from .upgrade_cmd import run_upgrade
    run_upgrade(target, config)


@main.command()
@click.option("--config", default=".flows/config.yaml", help="Config file path")
@click.option("--run-dir", default=None, help="Override run directory")
@click.option("--run-id", default=None)
def status(config, run_dir, run_id):
    """Show workflow run status."""
    from pathlib import Path
    from .state import load_state, WorkflowStatus
    from .runner import MAX_REJECTS
    from .path_resolver import resolve_paths
    
    resolved_run_dir, _, _ = resolve_paths(config, run_dir, None, None)
    
    run_dir_path = resolved_run_dir / (run_id or "latest")
    
    if not run_dir_path.exists():
        click.echo(f"Run directory not found: {run_dir_path}", err=True)
        raise click.Abort()
    
    state = load_state(run_dir_path)
    if not state:
        click.echo(f"No state found in: {run_dir_path}")
        return
    
    click.echo(f"Run: {run_dir_path.name}")
    click.echo(f"Status: {state.status.value.upper()}")
    click.echo(f"Node: {state.current_node}")
    
    if state.reject_counts:
        for node, count in state.reject_counts.items():
            click.echo(f"Reject count ({node}): {count}/{MAX_REJECTS}")
    
    if state.status == WorkflowStatus.PAUSED:
        if state.pending_approval_for:
            click.echo(f"Pending approval: {state.pending_approval_for}")
        click.echo(f"Approve: flowctl run --resume --approve --run-id {run_dir_path.name}")
        click.echo(f"Reject: flowctl run --resume --reject --reject-reason \"<reason>\" --run-id {run_dir_path.name}")


@main.command()
@click.option("--config", default=".flows/config.yaml", help="Config file path")
@click.option("--dry-run", is_flag=True)
@click.option("--executor", default="echo", help="Executor: echo, opencode")
@click.option("--model", default=None, help="Model for executor (e.g., alibaba-cn/glm-5)")
@click.option("--agent", default=None, help="Agent name for executor")
@click.option("--run-dir", default=None, help="Override run directory")
@click.option("--workflow-dir", default=None, help="Override workflow directory")
@click.option("--repo-dir", default=None, help="Target repository directory")
@click.option("--run-id", default=None)
@click.option("--issue", default=None, help="GitHub issue URL to process")
@click.option("--log-level", default="INFO", help="Log level: DEBUG, INFO, WARNING, ERROR")
@click.option("--log-format", default="json", help="Log format: json, text")
@click.option("--resume", is_flag=True, help="Resume from saved state in run directory")
@click.option("--approve", is_flag=True, help="Approve pending human node")
@click.option("--reject", is_flag=True, help="Reject pending human node")
@click.option("--reject-reason", default=None, help="Reason for rejection (required with --reject)")
@click.option("--skip-node", is_flag=True, help="Skip current node during workflow execution")
@click.argument("workflow", default=".flows/workflows/default.yaml")
def run(config, dry_run, executor, model, agent, run_dir, workflow_dir, repo_dir, workflow, run_id, issue, log_level, log_format, resume, approve, reject, reject_reason, skip_node):
    wf_path = Path(workflow)
    if not wf_path.exists():
        click.echo(f"Workflow not found: {wf_path}", err=True)
        raise click.Abort()

    wf = load_workflow(wf_path)
    errors = validate_workflow(wf)
    if errors:
        for e in errors:
            click.echo(f"Validation error: {e}", err=True)
        raise click.Abort()
    
    if (approve or reject) and not resume:
        click.echo("Error: Must use --resume with --approve/--reject", err=True)
        raise click.Abort()
    
    if approve and reject:
        click.echo("Error: Cannot use both --approve and --reject", err=True)
        raise click.Abort()
    
    if reject and not reject_reason:
        click.echo("Error: --reject-reason is required when using --reject", err=True)
        raise click.Abort()
    
    if skip_node and not resume:
        click.echo("Error: Must use --resume with --skip-node", err=True)
        raise click.Abort()

    # Resolve paths from config + CLI overrides
    resolved_run_dir, resolved_workflow_dir, resolved_repo_dir = resolve_paths(config, run_dir, workflow_dir, repo_dir)
    
    # Override run_id in run_dir if specified
    if run_id:
        resolved_run_dir = resolved_run_dir / run_id
    else:
        resolved_run_dir = resolved_run_dir / "latest"
    
    resolved_run_dir.mkdir(parents=True, exist_ok=True)

    registry = create_default_registry()
    
    if executor not in registry.list_available():
        click.echo(f"Unknown executor: {executor}", err=True)
        click.echo(f"Available: {', '.join(registry.list_available())}", err=True)
        raise click.Abort()

    executor_config = {}
    if model or agent:
        executor_config["opencode"] = {}
        if model:
            executor_config["opencode"]["model"] = model
        if agent:
            executor_config["opencode"]["agent"] = agent

    initial_context = {}
    if issue:
        initial_context["issue_url"] = issue
        issue_file = resolved_run_dir / "issue-url.txt"
        issue_file.write_text(issue)
    
    approval_decision = None
    if approve:
        approval_decision = "yes"
    elif reject:
        approval_decision = "no"

    result = run_workflow(
        wf, resolved_run_dir,
        registry=registry,
        default_executor=executor,
        executor_config=executor_config,
        dry_run=dry_run,
        initial_context=initial_context,
        workflow_dir=resolved_workflow_dir,
        repo_dir=resolved_repo_dir,
        log_level=log_level,
        log_format=log_format,
        resume=resume,
        approval_decision=approval_decision,
        reject_reason=reject_reason,
        skip_node=skip_node,
    )
    click.echo(f"Run complete. Context: {result}")