from pathlib import Path
import time
import yaml
import click
from .models import WorkflowDef, Node, FlowctlConfig
from .executors import ExecutorAdapter, EchoAdapter, ExecutorRegistry, create_default_registry
from .processor import PromptProcessor
from .executors.base import ExecutorInput, ExecutorResult
from .artifact_validator import validate_artifacts
from .logger import WorkflowLogger
from .state import save_state, load_state, has_state, clear_state, WorkflowStatus, WorkflowState

MAX_ITERATIONS = 100
MAX_REJECTS = 5  # Maximum reject attempts per approval node


def resolve_executor(node: Node, default: str, config: FlowctlConfig | None, roles: dict | None = None) -> str:
    if node.executor:
        return node.executor
    if node.role and roles and node.role in roles:
        role_config = roles[node.role]
        if hasattr(role_config, 'executor') and role_config.executor:
            return role_config.executor
    if default:
        return default
    if config and config.preferred_executor:
        return config.preferred_executor
    return "echo"


def resolve_executor_config(node: Node) -> dict:
    """Build executor config from node definition."""
    config = {}
    if node.executor == "bash":
        config["script_path"] = node.command or ""
        config["timeout_seconds"] = node.timeout_seconds or 60
    return config


def get_skipped_nodes(context: dict, state: WorkflowState | None = None) -> list[str] | None:
    skipped = context.get("__skipped_nodes__")
    if skipped:
        return skipped
    if state and state.skipped_nodes:
        return state.skipped_nodes
    return None


def load_flowctl_config(workflow_dir: Path | None) -> FlowctlConfig | None:
    """Load config from workflow_dir/config.yaml."""
    if not workflow_dir:
        return FlowctlConfig()
    
    config_path = workflow_dir / "config.yaml"
    if not config_path.exists():
        return FlowctlConfig()
    
    with open(config_path) as f:
        data = yaml.safe_load(f) or {}
    return FlowctlConfig(**data)


def get_next_transitions(workflow: WorkflowDef, current: str, context: dict) -> list[str]:
    candidates = [t for t in workflow.transitions if t.from_ == current]
    if not candidates:
        return []
    results = []
    for t in candidates:
        if t.when:
            key, _, val = t.when.partition(" == ")
            key = key.strip()
            expected = val.strip().strip('"\'')
            actual = context.get(key)
            if actual and actual.strip().split('\n')[0] == expected:
                results.append(t.to)
            continue
        results.append(t.to)
    return results


def run_workflow(
    workflow: WorkflowDef,
    run_dir: Path,
    adapter: ExecutorAdapter | None = None,
    registry: ExecutorRegistry | None = None,
    default_executor: str = "echo",
    executor_config: dict[str, dict] | None = None,
    dry_run: bool = False,
    initial_context: dict[str, str] | None = None,
    workflow_dir: Path | None = None,
    repo_dir: Path | None = None,
    log_level: str = "INFO",
    log_format: str = "json",
    resume: bool = False,
    approval_decision: str | None = None,
    reject_reason: str | None = None,
    skip_node: bool = False,
) -> dict[str, str]:
    config = load_flowctl_config(workflow_dir)
    processor = PromptProcessor()
    
    if adapter is None:
        registry = registry or create_default_registry()
    
    context: dict[str, str] = initial_context or {}
    current = "__start__"
    iterations = 0
    
    run_id = run_dir.name
    logger = WorkflowLogger(run_id, run_dir, log_level, log_format)
    executor_name = adapter.__class__.__name__ if adapter else default_executor
    logger.log_workflow_start(workflow=str(workflow_dir) if workflow_dir else "unknown", executor=executor_name, initial_context=initial_context)

    if resume and has_state(run_dir):
        state = load_state(run_dir)
        if state:
            if skip_node and state.status != WorkflowStatus.PAUSED:
                skipped_nodes = state.skipped_nodes or []
                if state.current_node not in ["__start__", "__end__"]:
                    skipped_nodes.append(state.current_node)
                    logger.log_skip(state.current_node)
                    click.echo(f"Skipped node: {state.current_node}")
                context = state.context
                context["__skipped_nodes__"] = skipped_nodes
                current = state.current_node
                iterations = state.iterations
                reject_counts_dict = context.get("__reject_counts__") or {}
                if not dry_run:
                    save_state(run_dir, current, context, iterations, skipped_nodes=skipped_nodes, reject_counts=reject_counts_dict)
            elif state.status == WorkflowStatus.PAUSED:
                if not approval_decision:
                    click.echo(f"Error: Workflow paused at '{state.current_node}'. Use --approve or --reject", err=True)
                    raise click.Abort()
                
                node_def = workflow.nodes.get(state.current_node)
                if not node_def:
                    raise RuntimeError(f"Node '{state.current_node}' not found")
                
                approval_key = state.pending_approval_for
                output_path = node_def.outputs.get(approval_key) if approval_key else None
                
                context = state.context
                
                # Handle reject - always track count
                if approval_decision == "no":
                    reject_counts = state.reject_counts or {}
                    approval_node = state.current_node
                    count = reject_counts.get(approval_node, 0) + 1
                    
                    if count > MAX_REJECTS:
                        click.echo(f"Error: Reject count exceeded ({count}/{MAX_REJECTS}) for node '{approval_node}'", err=True)
                        raise click.Abort()
                    
                    reject_counts[approval_node] = count
                    context["__reject_counts__"] = reject_counts
                    
                    # Handle reject_reason if provided
                    if reject_reason is not None:
                        reject_reason_path = run_dir / "reject-reason.txt"
                        reject_reason_path.write_text(reject_reason)
                        
                        content = reject_reason_path.read_text().strip()
                        if not content:
                            click.echo("Error: reject-reason.txt is empty", err=True)
                            raise click.Abort()
                
                if approval_key and output_path:
                    artifact_path = run_dir / output_path
                    artifact_path.parent.mkdir(parents=True, exist_ok=True)
                    artifact_path.write_text(approval_decision)
                    context[approval_key] = artifact_path.read_text()
                    click.echo(f"Resuming from '{state.current_node}' with decision: {approval_decision}")
                
                if state.skipped_nodes:
                    context["__skipped_nodes__"] = state.skipped_nodes
                
                current = state.current_node
                iterations = state.iterations
            else:
                current = state.current_node
                context = state.context
                iterations = state.iterations
                if state.skipped_nodes:
                    context["__skipped_nodes__"] = state.skipped_nodes

    run_dir.mkdir(parents=True, exist_ok=True)

    while current != "__end__":
        iterations += 1
        if iterations > MAX_ITERATIONS:
            raise RuntimeError(f"Workflow exceeded {MAX_ITERATIONS} iterations - possible cycle")

        next_nodes = get_next_transitions(workflow, current, context)
        if not next_nodes:
            logger.log_error(RuntimeError(f"No valid transitions from '{current}'"))
            raise RuntimeError(f"No valid transitions from '{current}'")

        next_node = next_nodes[0]

        for i, candidate in enumerate([t for t in workflow.transitions if t.from_ == current]):
            logger.log_transition(current, candidate.to, candidate.when, matched=(i == 0))

        if next_node == "__end__":
            break

        node_def = workflow.nodes.get(next_node)
        if not node_def:
            logger.log_error(RuntimeError(f"Node '{next_node}' not found"))
            raise RuntimeError(f"Node '{next_node}' not found in workflow definition")

        # Load prompt file
        prompt_content = ""
        if node_def.prompt:
            if workflow_dir:
                prompt_file = workflow_dir / node_def.prompt
            else:
                prompt_file = run_dir / node_def.prompt

            if prompt_file.exists():
                prompt_content = prompt_file.read_text()
            else:
                logger.log_warning(f"Prompt file not found: {prompt_file}")
                prompt_content = ""

        # Process prompt
        process_context = {
            "node": node_def,
            "run_dir": run_dir,
            "workflow_dir": workflow_dir,
            "repo_dir": repo_dir,
        }
        processed_prompt = processor.process(prompt_content, process_context)

        inp = ExecutorInput(
            role=node_def.role,
            prompt=processed_prompt,
            prompt_path=node_def.prompt,
            skill_paths=node_def.skills,
            inputs=node_def.inputs,
            outputs=node_def.outputs,
            run_dir=run_dir,
            workflow_dir=workflow_dir,
            repo_dir=repo_dir,
            node=node_def,
        )

        logger.log_node_start(next_node, node_def.role, node_def.prompt, node_def.skills, node_def.inputs)

        executor_name = resolve_executor(node_def, default_executor, config, workflow.roles) if adapter is None else adapter.__class__.__name__
        
        # Skip human node if we just resumed with approval
        if executor_name == "human" and approval_decision and current == next_node:
            current = next_node
            if not dry_run:
                reject_counts_dict = context.get("__reject_counts__") or (state.reject_counts if resume and state else {})
                skipped_nodes_list = get_skipped_nodes(context, state if resume else None)
                save_state(run_dir, current, context, iterations, status=WorkflowStatus.RUNNING, reject_counts=reject_counts_dict, skipped_nodes=skipped_nodes_list)
            continue

        if executor_name == "human" and not dry_run:
            approval_key = list(node_def.outputs.keys())[0] if node_def.outputs else None
            prev_node = current
            reject_counts_dict = context.get("__reject_counts__") or (state.reject_counts if resume and state else {})
            skipped_nodes_list = get_skipped_nodes(context, state if resume else None)
            save_state(
                run_dir, next_node, context, iterations,
                status=WorkflowStatus.PAUSED,
                pending_approval_for=approval_key,
                pending_transition_from=prev_node,
                reject_counts=reject_counts_dict,
                skipped_nodes=skipped_nodes_list,
            )
            logger.log_pause(next_node, node_def.inputs or {})
            click.echo(f"Workflow paused at '{next_node}'. Approve: flowctl run --resume --approve | Reject: flowctl run --resume --reject")
            return context

        if dry_run:
            echo_adapter = registry.get("echo")
            executor_start = time.time()
            result = echo_adapter.execute(inp)
            executor_duration_ms = int((time.time() - executor_start) * 1000)
            logger.log_executor(
                next_node,
                "echo",
                result.command or "",
                result.returncode,
                result.stdout,
                result.stderr,
                executor_duration_ms,
            )
            if result.stdout:
                click.echo(result.stdout)
        else:
            if adapter is not None:
                node_adapter = adapter
            else:
                base_cfg = executor_config.get(executor_name, {}) if executor_config else {}
                node_cfg = resolve_executor_config(node_def)
                cfg = {**base_cfg, **node_cfg}
                node_adapter = registry.get(executor_name, **cfg)
            executor_start = time.time()
            result = node_adapter.execute(inp)
            executor_duration_ms = int((time.time() - executor_start) * 1000)
            logger.log_executor(
                next_node,
                executor_name,
                result.command or "",
                result.returncode,
                result.stdout,
                result.stderr,
                executor_duration_ms,
            )

        errors = validate_artifacts(node_def.outputs, run_dir, workflow_dir, repo_dir)
        logger.log_validation(next_node, errors)
        
        if errors and not dry_run:
            logger.log_node_failure(next_node, RuntimeError(f"Artifact validation failed: {'; '.join(errors)}"))
            raise RuntimeError(f"Artifact validation failed: {'; '.join(errors)}")

        logger.log_node_end(next_node, "completed", result.outputs)

        if result.outputs:
            context.update(result.outputs)

        current = next_node
        
        if not dry_run:
            reject_counts_dict = context.get("__reject_counts__") or {}
            skipped_nodes_list = get_skipped_nodes(context, state if resume else None)
            save_state(run_dir, current, context, iterations, reject_counts=reject_counts_dict, skipped_nodes=skipped_nodes_list)

    if not dry_run:
        reject_counts_dict = context.get("__reject_counts__") or {}
        skipped_nodes_list = get_skipped_nodes(context, state if resume else None)
        save_state(run_dir, "__end__", context, iterations, status=WorkflowStatus.COMPLETED, reject_counts=reject_counts_dict, skipped_nodes=skipped_nodes_list)

    logger.log_workflow_end("completed")
    return context