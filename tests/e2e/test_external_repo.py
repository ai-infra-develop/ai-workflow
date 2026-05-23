"""E2E Tests for External Codebase Development Support.

Test IDs covered:
- TC-009: Git Operations Target Correct Repository
- TC-015: Workflow Engine Immutability
- EC-003: Path Boundary Violation Attempt
- EC-011: Git Operation in Non-Git Repository
"""

import pytest
import subprocess
import shutil
from pathlib import Path
from click.testing import CliRunner
from flowctl.cli import main
from flowctl.models import WorkflowDef, Node, Transition
from flowctl.runner import run_workflow
from flowctl.executors import create_default_registry
from flowctl.executors.bash import BashExecutor
from flowctl.executors.base import ExecutorInput


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "scripts"


@pytest.fixture
def workflow_dir_with_scripts(tmp_path):
    workflow_dir = tmp_path / ".flows"
    scripts_dir = workflow_dir / "scripts"
    scripts_dir.mkdir(parents=True)
    shutil.copytree(FIXTURES_DIR, scripts_dir, dirs_exist_ok=True)
    return workflow_dir


@pytest.fixture
def git_repo(tmp_path):
    """Create a real git repository for testing."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True, capture_output=True)
    
    (repo_dir / "README.md").write_text("# Test Repo")
    subprocess.run(["git", "add", "README.md"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True, capture_output=True)
    
    return repo_dir


@pytest.fixture
def workflow_engine_repo(tmp_path):
    """Create a mock workflow engine repository."""
    engine_dir = tmp_path / "engine"
    engine_dir.mkdir()
    
    subprocess.run(["git", "init"], cwd=engine_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "engine@test.com"], cwd=engine_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Engine User"], cwd=engine_dir, check=True, capture_output=True)
    
    flows_dir = engine_dir / ".flows"
    flows_dir.mkdir()
    
    prompts_dir = flows_dir / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "test.md").write_text("# Test Task")
    
    workflows_dir = flows_dir / "workflows"
    workflows_dir.mkdir()
    (workflows_dir / "test.yaml").write_text("""version: "1"
nodes:
  test:
    role: dev
    prompt: prompts/test.md
    executor: echo
    outputs: {result: result.md}
transitions:
  - from: __start__
    to: test
  - from: test
    to: __end__
""")
    
    subprocess.run(["git", "add", ".flows"], cwd=engine_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial workflow"], cwd=engine_dir, check=True, capture_output=True)
    
    return engine_dir


class TestGitOperationsTargetCorrectRepository:
    """TC-009: Git Operations Target Correct Repository"""

    def test_git_branch_created_in_target_repo(self, workflow_dir_with_scripts, git_repo, tmp_path):
        """TC-009: Git operations target REPO_DIR, not workflow engine"""
        scripts_dir = workflow_dir_with_scripts / "scripts"
        
        git_script = scripts_dir / "create_branch.sh"
        git_script.write_text("""#!/bin/bash
set -euo pipefail

cd "$REPO_DIR"
git checkout -b test-feature-branch
echo "test-feature-branch" > "$RUN_DIR/branch.txt"
exit 0
""")
        git_script.chmod(0o755)
        
        run_dir = tmp_path / "runs" / "test"
        run_dir.mkdir(parents=True)
        
        executor = BashExecutor(script_path="create_branch.sh", timeout_seconds=60)
        
        inp = ExecutorInput(
            role="test",
            prompt="Test prompt",
            prompt_path="test.md",
            inputs={},
            outputs={"branch": "branch.txt"},
            run_dir=run_dir,
            workflow_dir=workflow_dir_with_scripts,
            repo_dir=git_repo,
        )
        
        result = executor.execute(inp)
        
        assert result.returncode == 0
        
        branches = subprocess.run(
            ["git", "branch", "--list"],
            cwd=git_repo,
            check=True,
            capture_output=True,
            text=True
        )
        
        assert "test-feature-branch" in branches.stdout
        assert result.outputs["branch"].strip() == "test-feature-branch"

    def test_workflow_engine_repo_unchanged(self, workflow_dir_with_scripts, git_repo, workflow_engine_repo, tmp_path):
        """TC-009: Workflow engine repository unchanged after git operations in target repo"""
        scripts_dir = workflow_dir_with_scripts / "scripts"
        
        git_script = scripts_dir / "modify_repo.sh"
        git_script.write_text("""#!/bin/bash
set -euo pipefail

cd "$REPO_DIR"
echo "# Modified" > "$REPO_DIR/README.md"
git add README.md
git commit -m "Modify README"
exit 0
""")
        git_script.chmod(0o755)
        
        run_dir = tmp_path / "runs" / "test"
        run_dir.mkdir(parents=True)
        
        executor = BashExecutor(script_path="modify_repo.sh", timeout_seconds=60)
        
        inp = ExecutorInput(
            role="test",
            prompt="Test prompt",
            prompt_path="test.md",
            inputs={},
            outputs={},
            run_dir=run_dir,
            workflow_dir=workflow_dir_with_scripts,
            repo_dir=git_repo,
        )
        
        result = executor.execute(inp)
        
        assert result.returncode == 0
        
        engine_log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=workflow_engine_repo,
            check=True,
            capture_output=True,
            text=True
        )
        
        assert "Modify README" not in engine_log.stdout
        assert len(engine_log.stdout.strip().split('\n')) == 1
        
        target_log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_repo,
            check=True,
            capture_output=True,
            text=True
        )
        
        assert "Modify README" in target_log.stdout


class TestWorkflowEngineImmutability:
    """TC-015: Workflow Engine Immutability"""

    def test_workflow_files_not_modified(self, workflow_dir_with_scripts, git_repo, tmp_path):
        """TC-015: Workflow definitions not modified during execution"""
        workflow_dir = workflow_dir_with_scripts
        
        prompts_dir = workflow_dir / "prompts"
        prompts_dir.mkdir()
        original_prompt = prompts_dir / "test.md"
        original_prompt.write_text("# Original Content\n\nDo not modify this.")
        
        workflows_dir = workflow_dir / "workflows"
        workflows_dir.mkdir()
        workflow_file = workflows_dir / "test.yaml"
        workflow_file.write_text("""version: "1"
nodes:
  test:
    role: dev
    prompt: prompts/test.md
    executor: echo
    outputs: {result: result.md}
transitions:
  - from: __start__
    to: test
  - from: test
    to: __end__
""")
        
        run_dir = tmp_path / "runs" / "test"
        run_dir.mkdir(parents=True)
        
        import yaml
        workflow = WorkflowDef.model_validate(yaml.safe_load(workflow_file.read_text()))
        
        registry = create_default_registry()
        
        run_workflow(
            workflow,
            run_dir,
            registry=registry,
            default_executor="echo",
            dry_run=True,
            workflow_dir=workflow_dir,
            repo_dir=git_repo,
        )
        
        assert original_prompt.read_text() == "# Original Content\n\nDo not modify this."
        assert workflow_file.read_text().startswith("version: \"1\"")


class TestPathBoundaryViolation:
    """EC-003: Path Boundary Violation Attempt
    
    Note: Path boundary validation is deferred to executor (design decision).
    Scripts can write outside REPO_DIR if they have filesystem access.
    This is a known limitation documented in the design.
    """

    @pytest.mark.skip(reason="Path boundary validation deferred to executor (design decision). EC-003 documented as known limitation.")
    def test_path_escape_with_dotdot(self, workflow_dir_with_scripts, tmp_path):
        """EC-003: Output path attempting to escape repo_dir fails
        
        NOTE: This test is skipped because the design explicitly defers
        path boundary validation. Scripts can write outside REPO_DIR.
        """
        scripts_dir = workflow_dir_with_scripts / "scripts"
        
        escape_script = scripts_dir / "try_escape.sh"
        escape_script.write_text("""#!/bin/bash
set -euo pipefail

# Try to write outside repo_dir
echo "escaped" > "$REPO_DIR/../outside.txt"
exit 0
""")
        escape_script.chmod(0o755)
        
        run_dir = tmp_path / "runs" / "test"
        run_dir.mkdir(parents=True)
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        
        executor = BashExecutor(script_path="try_escape.sh", timeout_seconds=60)
        
        inp = ExecutorInput(
            role="test",
            prompt="Test prompt",
            prompt_path="test.md",
            inputs={},
            outputs={},
            run_dir=run_dir,
            workflow_dir=workflow_dir_with_scripts,
            repo_dir=repo_dir,
        )
        
        with pytest.raises(RuntimeError):
            executor.execute(inp)


class TestGitOperationInNonGitRepository:
    """EC-011: Git Operation in Non-Git Repository"""

    def test_git_operation_in_non_git_dir(self, workflow_dir_with_scripts, tmp_path):
        """EC-011: Git operation in directory without .git fails"""
        scripts_dir = workflow_dir_with_scripts / "scripts"
        
        git_script = scripts_dir / "git_status.sh"
        git_script.write_text("""#!/bin/bash
set -euo pipefail

cd "$REPO_DIR"
git status
exit 0
""")
        git_script.chmod(0o755)
        
        run_dir = tmp_path / "runs" / "test"
        run_dir.mkdir(parents=True)
        
        non_git_dir = tmp_path / "non_git_repo"
        non_git_dir.mkdir()
        (non_git_dir / "README.md").write_text("# Not a git repo")
        
        executor = BashExecutor(script_path="git_status.sh", timeout_seconds=60)
        
        inp = ExecutorInput(
            role="test",
            prompt="Test prompt",
            prompt_path="test.md",
            inputs={},
            outputs={},
            run_dir=run_dir,
            workflow_dir=workflow_dir_with_scripts,
            repo_dir=non_git_dir,
        )
        
        with pytest.raises(RuntimeError, match="exit code"):
            executor.execute(inp)