from click.testing import CliRunner
from flowctl.cli import main
import tempfile
import shutil
from pathlib import Path


def test_init_command():
    runner = CliRunner()
    result = runner.invoke(main, ["init"])
    assert result.exit_code == 0
    assert "Initialized" in result.output
    assert ".flows" in result.output


def test_run_command():
    runner = CliRunner()
    with runner.isolated_filesystem():
        flows_dir = Path(".flows/workflows")
        flows_dir.mkdir(parents=True)
        workflow_file = flows_dir / "default.yaml"
        workflow_file.write_text(
            "version: '1'\n"
            "nodes:\n"
            "  planner:\n"
            "    role: planner\n"
            "    prompt: prompts/plan.md\n"
            "    inputs: {}\n"
            "    outputs: {spec: spec.md}\n"
            "transitions:\n"
            "  - from: __start__\n"
            "    to: planner\n"
            "  - from: planner\n"
            "    to: __end__\n"
        )
        result = runner.invoke(main, ["run", "--dry-run"])
        assert result.exit_code == 0
        assert "Run complete" in result.output
        assert "PROCESSED PROMPT" in result.output


def test_cli_approve_reject_flags():
    runner = CliRunner()
    with runner.isolated_filesystem():
        flows_dir = Path(".flows/workflows")
        flows_dir.mkdir(parents=True)
        workflow_file = flows_dir / "default.yaml"
        workflow_file.write_text(
            "version: '1'\n"
            "nodes:\n"
            "  planner:\n"
            "    role: planner\n"
            "    prompt: prompts/plan.md\n"
            "    inputs: {}\n"
            "    outputs: {spec: spec.md}\n"
            "transitions:\n"
            "  - from: __start__\n"
            "    to: planner\n"
            "  - from: planner\n"
            "    to: __end__\n"
        )
        
        # Test approve flag validation - must use --resume
        result = runner.invoke(main, ["run", ".flows/workflows/default.yaml", "--approve"])
        assert result.exit_code != 0
        assert "must use --resume" in result.output.lower()
        
        # Test both flags error
        result = runner.invoke(main, ["run", ".flows/workflows/default.yaml", "--resume", "--approve", "--reject"])
        assert result.exit_code != 0
        assert "cannot use both" in result.output.lower()


def test_cli_status_command():
    from flowctl.state import save_state, WorkflowStatus
    
    runner = CliRunner()
    with runner.isolated_filesystem():
        run_dir = Path(".flows/runs/test-run")
        run_dir.mkdir(parents=True)
        save_state(run_dir, "human_approval", {"input": "test.md"}, 1,
                   status=WorkflowStatus.PAUSED, pending_approval_for="approved", pending_transition_from="step1")
        
        result = runner.invoke(main, ["status", "--run-id", "test-run"])
        
        assert result.exit_code == 0
        assert "PAUSED" in result.output
        assert "human_approval" in result.output


def test_cli_reject_reason_required():
    runner = CliRunner()
    with runner.isolated_filesystem():
        flows_dir = Path(".flows/workflows")
        flows_dir.mkdir(parents=True)
        workflow_file = flows_dir / "default.yaml"
        workflow_file.write_text(
            "version: '1'\n"
            "nodes:\n"
            "  planner:\n"
            "    role: planner\n"
            "    prompt: prompts/plan.md\n"
            "    inputs: {}\n"
            "    outputs: {spec: spec.md}\n"
            "transitions:\n"
            "  - from: __start__\n"
            "    to: planner\n"
            "  - from: planner\n"
            "    to: __end__\n"
        )
        
        # Test reject without reason - must require reason
        result = runner.invoke(main, ["run", ".flows/workflows/default.yaml", "--resume", "--reject"])
        assert result.exit_code != 0
        assert "reject-reason" in result.output.lower()


def test_cli_reject_reason_with_value():
    runner = CliRunner()
    with runner.isolated_filesystem():
        flows_dir = Path(".flows/workflows")
        flows_dir.mkdir(parents=True)
        workflow_file = flows_dir / "default.yaml"
        workflow_file.write_text(
            "version: '1'\n"
            "nodes:\n"
            "  planner:\n"
            "    role: planner\n"
            "    prompt: prompts/plan.md\n"
            "    inputs: {}\n"
            "    outputs: {spec: spec.md}\n"
            "transitions:\n"
            "  - from: __start__\n"
            "    to: planner\n"
            "  - from: planner\n"
            "    to: __end__\n"
        )
        
        # Test reject with reason - valid
        result = runner.invoke(main, ["run", ".flows/workflows/default.yaml", "--resume", "--reject", "--reject-reason", "Missing details"])
        # May still fail due to no state, but CLI validation should pass
        assert "--reject-reason is required" not in result.output


def test_run_config_option():
    """--config option loads config from custom path."""
    import yaml
    
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create custom config
        config_dir = Path("custom")
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"
        config_file.write_text(yaml.dump({
            'preferred_executor': 'echo',
            'run_dir': '/custom/runs',
        }))
        
        # Create workflow
        flows_dir = Path(".flows/workflows")
        flows_dir.mkdir(parents=True)
        workflow_file = flows_dir / "default.yaml"
        workflow_file.write_text(
            "version: '1'\n"
            "nodes:\n"
            "  planner:\n"
            "    role: planner\n"
            "    prompt: prompts/plan.md\n"
            "    inputs: {}\n"
            "    outputs: {spec: spec.md}\n"
            "transitions:\n"
            "  - from: __start__\n"
            "    to: planner\n"
            "  - from: planner\n"
            "    to: __end__\n"
        )
        
        # Use --dry-run to avoid actual execution
        result = runner.invoke(main, [
            'run',
            '--config', str(config_file),
            '--dry-run',
            '.flows/workflows/default.yaml',
        ])
        
        # Should not error about config
        assert 'Config not found' not in result.output


def test_run_run_dir_option():
    """--run-dir option overrides config."""
    runner = CliRunner()
    temp_run_dir = tempfile.mkdtemp()
    try:
        with runner.isolated_filesystem():
            # Create workflow
            flows_dir = Path(".flows/workflows")
            flows_dir.mkdir(parents=True)
            workflow_file = flows_dir / "default.yaml"
            workflow_file.write_text(
                "version: '1'\n"
                "nodes:\n"
                "  planner:\n"
                "    role: planner\n"
                "    prompt: prompts/plan.md\n"
                "    inputs: {}\n"
                "    outputs: {spec: spec.md}\n"
                "transitions:\n"
                "  - from: __start__\n"
                "    to: planner\n"
                "  - from: planner\n"
                "    to: __end__\n"
            )
            
            result = runner.invoke(main, [
                'run',
                '--run-dir', temp_run_dir,
                '--dry-run',
                '--run-id', 'test-cli-override',
                '.flows/workflows/default.yaml',
            ])
            
            assert result.exit_code == 0
            # Check that run dir was used
            assert Path(temp_run_dir).joinpath('test-cli-override').exists()
    finally:
        shutil.rmtree(temp_run_dir, ignore_errors=True)


def test_status_run_dir_option():
    """status command uses --run-dir option."""
    import json
    
    runner = CliRunner()
    temp_run_dir = Path(tempfile.mkdtemp()) / "test-status-run"
    temp_run_dir.mkdir(parents=True)
    
    # Create minimal state.json
    state = {
        "current_node": "test_node",
        "context": {},
        "iterations": 0,
        "status": "running"
    }
    (temp_run_dir / "state.json").write_text(json.dumps(state))
    
    result = runner.invoke(main, [
        'status',
        '--run-dir', str(temp_run_dir.parent),
        '--run-id', 'test-status-run',
    ])
    
    assert result.exit_code == 0
    assert 'test-status-run' in result.output
    
    # Cleanup
    shutil.rmtree(temp_run_dir.parent)


def test_cli_skip_node_requires_resume():
    """--skip-node flag must be used with --resume."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        flows_dir = Path(".flows/workflows")
        flows_dir.mkdir(parents=True)
        workflow_file = flows_dir / "default.yaml"
        workflow_file.write_text(
            "version: '1'\n"
            "nodes:\n"
            "  planner:\n"
            "    role: planner\n"
            "    prompt: prompts/plan.md\n"
            "    inputs: {}\n"
            "    outputs: {spec: spec.md}\n"
            "transitions:\n"
            "  - from: __start__\n"
            "    to: planner\n"
            "  - from: planner\n"
            "    to: __end__\n"
        )
        
        result = runner.invoke(main, ["run", ".flows/workflows/default.yaml", "--skip-node"])
        assert result.exit_code != 0
        assert "must use --resume" in result.output.lower()


def test_cli_skip_node_with_resume():
    """--skip-node with --resume should be accepted."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        flows_dir = Path(".flows/workflows")
        flows_dir.mkdir(parents=True)
        workflow_file = flows_dir / "default.yaml"
        workflow_file.write_text(
            "version: '1'\n"
            "nodes:\n"
            "  planner:\n"
            "    role: planner\n"
            "    prompt: prompts/plan.md\n"
            "    inputs: {}\n"
            "    outputs: {spec: spec.md}\n"
            "transitions:\n"
            "  - from: __start__\n"
            "    to: planner\n"
            "  - from: planner\n"
            "    to: __end__\n"
        )
        
        result = runner.invoke(main, ["run", ".flows/workflows/default.yaml", "--resume", "--skip-node"])
        assert "must use --resume" not in result.output