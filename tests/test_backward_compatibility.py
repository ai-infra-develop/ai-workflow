"""Backward Compatibility Tests.

Test IDs covered:
- TC-007: Default Repository Behavior
"""

import pytest
from pathlib import Path
from click.testing import CliRunner
from flowctl.cli import main
import tempfile
import yaml
import shutil
from flowctl.models import WorkflowDef, Node, Transition
from flowctl.runner import run_workflow
from flowctl.executors import create_default_registry
from flowctl.executors.bash import BashExecutor
from flowctl.executors.base import ExecutorInput


class TestBackwardCompatibility:
    """TC-007: Default Repository Behavior"""

    def test_workflow_without_repo_dir(self, tmp_path):
        """TC-007: REPO_DIR defaults to RUN_DIR when --repo-dir not provided"""
        workflow_dir = tmp_path / "flows"
        workflow_dir.mkdir()
        run_dir = tmp_path / "runs" / "test"
        run_dir.mkdir(parents=True)
        
        prompt_dir = workflow_dir / "prompts"
        prompt_dir.mkdir()
        (prompt_dir / "test.md").write_text("# Test Task")
        
        workflow = WorkflowDef(
            version="1",
            nodes={
                "start": Node(
                    role="dev",
                    prompt="prompts/test.md",
                    inputs={},
                    outputs={"result": "result.md"},
                ),
            },
            transitions=[
                Transition(from_="__start__", to="start"),
                Transition(from_="start", to="__end__"),
            ],
        )
        
        registry = create_default_registry()
        
        result = run_workflow(
            workflow,
            run_dir,
            registry=registry,
            default_executor="echo",
            dry_run=True,
            workflow_dir=workflow_dir,
            repo_dir=None,
        )
        
        assert result is not None
        assert (run_dir / "result.md").exists()

    def test_cli_without_repo_dir_flag(self):
        """TC-007: CLI works without --repo-dir flag (backward compatible)"""
        runner = CliRunner()
        
        result = runner.invoke(main, [
            'run',
            '--dry-run',
            '.flows/workflows/hello-world.yaml',
        ])
        
        assert result.exit_code == 0
        assert Path(".flows/runs/latest").exists()

    def test_existing_workflow_yaml_compatible(self, tmp_path):
        """TC-007: Existing workflow definitions continue working"""
        workflow_dir = tmp_path / "flows"
        workflow_dir.mkdir()
        
        workflows_dir = workflow_dir / "workflows"
        workflows_dir.mkdir()
        
        workflow_file = workflows_dir / "legacy.yaml"
        workflow_file.write_text("""version: "1"
nodes:
  hello:
    role: greeter
    prompt: prompts/hello.md
    executor: echo
    outputs: {greeting: greeting.txt}
transitions:
  - from: __start__
    to: hello
  - from: hello
    to: __end__
""")
        
        prompts_dir = workflow_dir / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "hello.md").write_text("# Hello Task")
        
        run_dir = tmp_path / "runs" / "legacy-test"
        run_dir.mkdir(parents=True)
        
        registry = create_default_registry()
        workflow = WorkflowDef.model_validate(yaml.safe_load(workflow_file.read_text()))
        
        result = run_workflow(
            workflow,
            run_dir,
            registry=registry,
            default_executor="echo",
            dry_run=True,
            workflow_dir=workflow_dir,
            repo_dir=None,
        )
        
        assert result is not None

    def test_repo_prefix_without_repo_dir_fallback(self, tmp_path):
        """TC-007: repo: prefix works with fallback to run_dir"""
        workflow_dir = tmp_path / "flows"
        workflow_dir.mkdir()
        run_dir = tmp_path / "runs" / "test"
        run_dir.mkdir(parents=True)
        
        prompt_dir = workflow_dir / "prompts"
        prompt_dir.mkdir()
        (prompt_dir / "test.md").write_text("# Test Task")
        
        (run_dir / "ARCHITECTURE.md").write_text("# Architecture")
        
        workflow = WorkflowDef(
            version="1",
            nodes={
                "start": Node(
                    role="dev",
                    prompt="prompts/test.md",
                    inputs={"arch": "repo:ARCHITECTURE.md"},
                    outputs={},
                ),
            },
            transitions=[
                Transition(from_="__start__", to="start"),
                Transition(from_="start", to="__end__"),
            ],
        )
        
        registry = create_default_registry()
        
        result = run_workflow(
            workflow,
            run_dir,
            registry=registry,
            default_executor="echo",
            dry_run=True,
            workflow_dir=workflow_dir,
            repo_dir=None,
        )
        
        assert result is not None

    def test_bash_executor_repo_dir_defaults_to_run_dir(self, tmp_path):
        """TC-007: Bash executor REPO_DIR defaults to RUN_DIR"""
        import shutil
        from pathlib import Path
        
        FIXTURES_DIR = Path(__file__).parent / "fixtures" / "scripts"
        
        workflow_dir = tmp_path / ".flows"
        scripts_dir = workflow_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        shutil.copytree(FIXTURES_DIR, scripts_dir, dirs_exist_ok=True)
        
        run_dir = tmp_path / "runs" / "test"
        run_dir.mkdir(parents=True)
        
        executor = BashExecutor(script_path="check_repo_env.sh", timeout_seconds=60)
        
        inp = ExecutorInput(
            role="test",
            prompt="Test prompt",
            prompt_path="test.md",
            inputs={},
            outputs={"output": "repo_dir.txt"},
            run_dir=run_dir,
            workflow_dir=workflow_dir,
            repo_dir=None,
        )
        
        result = executor.execute(inp)
        
        assert result.returncode == 0
        assert result.outputs["output"].strip() == str(run_dir.resolve())