"""Integration tests for external codebase development support.

Test IDs covered:
- TC-001: Path Prefix Resolution (run:)
- TC-002: Path Prefix Resolution (workflow:)
- TC-003: Path Prefix Resolution (repo:)
- TC-005: Environment Variable Injection (REPO_DIR)
- TC-006: Environment Variable Injection (RUN_DIR)
- TC-010: Mixed Path Prefixes in Single Node
- TC-014: Script Portability via Environment Variables
- EC-001: Missing repo_dir with repo: Prefix
- EC-006: Bash Script Receives Undefined Environment Variable
- EC-007: Cross-Context Path Reference
"""

import pytest
import shutil
from pathlib import Path
from flowctl.models import WorkflowDef, Node, Transition
from flowctl.runner import run_workflow
from flowctl.executors import create_default_registry
from flowctl.executors.bash import BashExecutor
from flowctl.executors.base import ExecutorInput
from flowctl.processor import PromptProcessor


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "scripts"


@pytest.fixture
def workflow_dir_with_scripts(tmp_path):
    workflow_dir = tmp_path / ".flows"
    scripts_dir = workflow_dir / "scripts"
    scripts_dir.mkdir(parents=True)
    shutil.copytree(FIXTURES_DIR, scripts_dir, dirs_exist_ok=True)
    return workflow_dir


class TestEnvironmentVariableInjection:
    """TC-005, TC-006: Environment Variable Injection"""

    def test_repo_dir_env_var_injected(self, workflow_dir_with_scripts):
        """TC-005: Bash executor receives REPO_DIR environment variable"""
        executor = BashExecutor(script_path="check_repo_env.sh", timeout_seconds=60)
        
        run_dir = workflow_dir_with_scripts.parent / "runs" / "test"
        run_dir.mkdir(parents=True)
        
        repo_dir = workflow_dir_with_scripts.parent / "repo"
        repo_dir.mkdir()
        
        inp = ExecutorInput(
            role="test",
            prompt="Test prompt",
            prompt_path="test.md",
            inputs={},
            outputs={"repo_dir_output": "repo_dir.txt"},
            run_dir=run_dir,
            workflow_dir=workflow_dir_with_scripts,
            repo_dir=repo_dir,
        )
        
        result = executor.execute(inp)
        
        assert result.returncode == 0
        assert "repo_dir_output" in result.outputs
        assert result.outputs["repo_dir_output"].strip() == str(repo_dir.resolve())

    def test_run_dir_env_var_injected(self, workflow_dir_with_scripts):
        """TC-006: Bash executor receives RUN_DIR environment variable"""
        executor = BashExecutor(script_path="check_env.sh", timeout_seconds=60)
        
        run_dir = workflow_dir_with_scripts.parent / "runs" / "test"
        run_dir.mkdir(parents=True)
        
        inp = ExecutorInput(
            role="test",
            prompt="Test prompt",
            prompt_path="test.md",
            inputs={},
            outputs={"run_dir_output": "run_dir.txt"},
            run_dir=run_dir,
            workflow_dir=workflow_dir_with_scripts,
        )
        
        result = executor.execute(inp)
        
        assert result.returncode == 0
        assert "run_dir_output" in result.outputs
        assert result.outputs["run_dir_output"].strip() == str(run_dir.resolve())

    def test_repo_dir_defaults_to_run_dir(self, workflow_dir_with_scripts):
        """EC-006: Bash Script Receives Undefined Environment Variable (defaults to RUN_DIR)"""
        executor = BashExecutor(script_path="check_repo_env.sh", timeout_seconds=60)
        
        run_dir = workflow_dir_with_scripts.parent / "runs" / "test"
        run_dir.mkdir(parents=True)
        
        inp = ExecutorInput(
            role="test",
            prompt="Test prompt",
            prompt_path="test.md",
            inputs={},
            outputs={"repo_dir_output": "repo_dir.txt"},
            run_dir=run_dir,
            workflow_dir=workflow_dir_with_scripts,
            repo_dir=None,
        )
        
        result = executor.execute(inp)
        
        assert result.returncode == 0
        assert "repo_dir_output" in result.outputs
        assert result.outputs["repo_dir_output"].strip() == str(run_dir.resolve())


class TestPathPrefixResolution:
    """TC-001, TC-002, TC-003: Path Prefix Resolution"""

    def test_run_prefix_resolution(self, tmp_path):
        """TC-001: Input/output paths with run: prefix resolve to run_dir"""
        processor = PromptProcessor()
        
        run_dir = tmp_path / "runs" / "test"
        workflow_dir = tmp_path / "flows"
        repo_dir = tmp_path / "repo"
        
        node = Node(
            role="dev",
            prompt="test.md",
            inputs={"clarify": "run:clarify.md"},
            outputs={"design": "run:design.md"},
        )
        
        context = {
            "node": node,
            "run_dir": run_dir,
            "workflow_dir": workflow_dir,
            "repo_dir": repo_dir,
        }
        
        result = processor.process("# Task", context)
        
        assert "run_dir:" in result
        assert str(run_dir / "clarify.md") in result
        assert str(run_dir / "design.md") in result

    def test_workflow_prefix_resolution(self, tmp_path):
        """TC-002: Input/output paths with workflow: prefix resolve to workflow_dir"""
        processor = PromptProcessor()
        
        run_dir = tmp_path / "runs" / "test"
        workflow_dir = tmp_path / "flows"
        repo_dir = tmp_path / "repo"
        
        node = Node(
            role="dev",
            prompt="test.md",
            inputs={"memory": "workflow:memory/architect.md"},
            outputs={"memory_update": "workflow:memory/ba.md"},
        )
        
        context = {
            "node": node,
            "run_dir": run_dir,
            "workflow_dir": workflow_dir,
            "repo_dir": repo_dir,
        }
        
        result = processor.process("# Task", context)
        
        assert "workflow_dir:" in result
        assert str(workflow_dir / "memory" / "architect.md") in result
        assert str(workflow_dir / "memory" / "ba.md") in result

    def test_repo_prefix_resolution(self, tmp_path):
        """TC-003: Input/output paths with repo: prefix resolve to repo_dir"""
        processor = PromptProcessor()
        
        run_dir = tmp_path / "runs" / "test"
        workflow_dir = tmp_path / "flows"
        repo_dir = tmp_path / "repo"
        
        node = Node(
            role="dev",
            prompt="test.md",
            inputs={"architecture": "repo:ARCHITECTURE.md"},
            outputs={"main_file": "repo:src/main.py"},
        )
        
        context = {
            "node": node,
            "run_dir": run_dir,
            "workflow_dir": workflow_dir,
            "repo_dir": repo_dir,
        }
        
        result = processor.process("# Task", context)
        
        assert "repo_dir:" in result
        assert str(repo_dir / "ARCHITECTURE.md") in result
        assert str(repo_dir / "src" / "main.py") in result

    def test_repo_prefix_fallback_to_run_dir(self, tmp_path):
        """EC-001: Missing repo_dir with repo: Prefix (falls back to RUN_DIR)"""
        processor = PromptProcessor()
        
        run_dir = tmp_path / "runs" / "test"
        workflow_dir = tmp_path / "flows"
        
        node = Node(
            role="dev",
            prompt="test.md",
            inputs={"architecture": "repo:ARCHITECTURE.md"},
            outputs={},
        )
        
        context = {
            "node": node,
            "run_dir": run_dir,
            "workflow_dir": workflow_dir,
            "repo_dir": None,
        }
        
        result = processor.process("# Task", context)
        
        assert "repo_dir:" in result
        assert str(run_dir / "ARCHITECTURE.md") in result


class TestMixedPathPrefixes:
    """TC-010: Mixed Path Prefixes in Single Node"""

    def test_single_node_with_multiple_prefixes(self, tmp_path):
        """TC-010: Single node with inputs/outputs from multiple contexts"""
        processor = PromptProcessor()
        
        run_dir = tmp_path / "runs" / "test"
        workflow_dir = tmp_path / "flows"
        repo_dir = tmp_path / "repo"
        
        node = Node(
            role="dev",
            prompt="test.md",
            inputs={
                "clarify": "run:clarify.md",
                "memory": "workflow:memory/architect.md",
                "architecture": "repo:ARCHITECTURE.md",
            },
            outputs={
                "design": "run:design.md",
                "memory_update": "workflow:memory/ba.md",
                "src_file": "repo:src/main.py",
            },
        )
        
        context = {
            "node": node,
            "run_dir": run_dir,
            "workflow_dir": workflow_dir,
            "repo_dir": repo_dir,
        }
        
        result = processor.process("# Task", context)
        
        assert "run_dir:" in result
        assert "workflow_dir:" in result
        assert "repo_dir:" in result
        assert str(run_dir / "clarify.md") in result
        assert str(workflow_dir / "memory" / "architect.md") in result
        assert str(repo_dir / "ARCHITECTURE.md") in result
        assert str(run_dir / "design.md") in result
        assert str(workflow_dir / "memory" / "ba.md") in result
        assert str(repo_dir / "src" / "main.py") in result


class TestScriptPortability:
    """TC-014: Script Portability via Environment Variables"""

    def test_script_portability_with_different_repo_dirs(self, workflow_dir_with_scripts):
        """TC-014: Scripts use environment variables instead of hardcoded paths"""
        executor = BashExecutor(script_path="check_repo_env.sh", timeout_seconds=60)
        
        run_dir1 = workflow_dir_with_scripts.parent / "runs" / "test1"
        run_dir1.mkdir(parents=True)
        repo_dir1 = workflow_dir_with_scripts.parent / "repo1"
        repo_dir1.mkdir()
        
        inp1 = ExecutorInput(
            role="test",
            prompt="Test prompt",
            prompt_path="test.md",
            inputs={},
            outputs={"output": "repo_dir.txt"},
            run_dir=run_dir1,
            workflow_dir=workflow_dir_with_scripts,
            repo_dir=repo_dir1,
        )
        
        result1 = executor.execute(inp1)
        assert result1.outputs["output"].strip() == str(repo_dir1.resolve())
        
        run_dir2 = workflow_dir_with_scripts.parent / "runs" / "test2"
        run_dir2.mkdir(parents=True)
        repo_dir2 = workflow_dir_with_scripts.parent / "repo2"
        repo_dir2.mkdir()
        
        inp2 = ExecutorInput(
            role="test",
            prompt="Test prompt",
            prompt_path="test.md",
            inputs={},
            outputs={"output": "repo_dir.txt"},
            run_dir=run_dir2,
            workflow_dir=workflow_dir_with_scripts,
            repo_dir=repo_dir2,
        )
        
        result2 = executor.execute(inp2)
        assert result2.outputs["output"].strip() == str(repo_dir2.resolve())


class TestCrossContextPathReference:
    """EC-007: Cross-Context Path Reference"""

    def test_input_from_workflow_output_to_repo(self, tmp_path):
        """EC-007: Input from workflow: context, output to repo: context"""
        processor = PromptProcessor()
        
        run_dir = tmp_path / "runs" / "test"
        workflow_dir = tmp_path / "flows"
        repo_dir = tmp_path / "repo"
        
        node = Node(
            role="dev",
            prompt="test.md",
            inputs={"memory": "workflow:memory/architect.md"},
            outputs={"src_file": "repo:src/main.py"},
        )
        
        context = {
            "node": node,
            "run_dir": run_dir,
            "workflow_dir": workflow_dir,
            "repo_dir": repo_dir,
        }
        
        result = processor.process("# Task", context)
        
        assert "workflow_dir:" in result
        assert "repo_dir:" in result
        assert str(workflow_dir / "memory" / "architect.md") in result
        assert str(repo_dir / "src" / "main.py") in result


class TestWorkflowIntegration:
    """Integration tests for full workflow execution"""

    def test_workflow_with_repo_dir(self, tmp_path):
        """Integration: Full workflow with repo_dir set"""
        workflow_dir = tmp_path / "flows"
        workflow_dir.mkdir()
        run_dir = tmp_path / "runs" / "test"
        run_dir.mkdir(parents=True)
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        
        memory_dir = workflow_dir / "memory"
        memory_dir.mkdir()
        (memory_dir / "architect.md").write_text("# Architect Memory")
        
        (repo_dir / "ARCHITECTURE.md").write_text("# Repo Architecture")
        
        prompt_dir = workflow_dir / "prompts"
        prompt_dir.mkdir()
        (prompt_dir / "test.md").write_text("# Test Task")
        
        workflow = WorkflowDef(
            version="1",
            nodes={
                "start": Node(
                    role="dev",
                    prompt="prompts/test.md",
                    inputs={
                        "memory": "workflow:memory/architect.md",
                        "repo": "repo:ARCHITECTURE.md",
                    },
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
            repo_dir=repo_dir,
        )
        
        assert result is not None