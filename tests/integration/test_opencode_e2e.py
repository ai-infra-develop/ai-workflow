"""
E2e test for flowctl CLI.

Test flow:
1. Create target repo
2. Run `flowctl init --source-workflow-dir FIXTURE_DIR` 
3. Run `flowctl run --executor opencode`
4. Validate results (input/output)

Source workflow_dir: tests/integration/opencode_e2e/
Contains: workflow.yaml, prompts/, skills/, scripts/

Target repo_dir (tmp_path):
    target-repo/
    ├── src/                        # repo: prefix writes here
    └── .flows/                     # workflow_dir (copied from source)
        ├── config.yaml             # repo_dir: ..
        ├── workflows/workflow.yaml
        ├── prompts/
        ├── skills/
        ├── scripts/
        └── runs/<run-id>/          # run_dir (logs)
"""

import pytest
import subprocess
from pathlib import Path
from tests.integration.validators import assert_test_passed


FIXTURE_DIR = Path(__file__).parent / "opencode_e2e"


def test_flowctl_init_with_source(tmp_path):
    """
    Test flowctl init --source-workflow-dir.
    
    Verifies:
    - .flows/ created in target repo
    - workflow files copied from source
    - config.yaml has repo_dir: ..
    - scripts are executable
    """
    
    repo_dir = tmp_path / "target-repo"
    repo_dir.mkdir()
    (repo_dir / "src").mkdir()
    
    result = subprocess.run(
        [
            "uv", "run", "flowctl", "init",
            "--target", str(repo_dir),
            "--source-workflow-dir", str(FIXTURE_DIR),
        ],
        cwd=str(repo_dir),
        capture_output=True,
        text=True,
    )
    
    assert result.returncode == 0, f"flowctl init failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    
    workflow_dir = repo_dir / ".flows"
    
    # Check structure
    assert workflow_dir.exists()
    assert (workflow_dir / "config.yaml").exists()
    assert (workflow_dir / "workflows").is_dir()
    assert (workflow_dir / "prompts").is_dir()
    assert (workflow_dir / "skills").is_dir()
    assert (workflow_dir / "scripts").is_dir()
    assert (workflow_dir / "runs").is_dir()
    
    # Check workflow files copied
    assert (workflow_dir / "workflows" / "workflow.yaml").exists()
    assert (workflow_dir / "prompts" / "task.md").exists()
    assert (workflow_dir / "prompts" / "verify.md").exists()
    assert (workflow_dir / "skills" / "minimal.md").exists()
    assert (workflow_dir / "scripts" / "setup.sh").exists()
    
    # Check script is executable
    script_file = workflow_dir / "scripts" / "setup.sh"
    assert script_file.stat().st_mode & 0o111
    
    # Check config has repo_dir: ..
    config = workflow_dir / "config.yaml"
    config_content = config.read_text()
    assert "repo_dir: .." in config_content


def test_flowctl_init_invalid_source(tmp_path):
    """
    Test flowctl init with invalid source directory.
    
    Source missing workflows/ subdirectory should fail.
    """
    
    # Create invalid source (missing workflows/)
    invalid_source = tmp_path / "invalid-source"
    invalid_source.mkdir()
    (invalid_source / "prompts").mkdir()
    (invalid_source / "prompts" / "test.md").write_text("test")
    
    repo_dir = tmp_path / "target-repo"
    repo_dir.mkdir()
    
    result = subprocess.run(
        [
            "uv", "run", "flowctl", "init",
            "--target", str(repo_dir),
            "--source-workflow-dir", str(invalid_source),
        ],
        cwd=str(repo_dir),
        capture_output=True,
        text=True,
    )
    
    assert result.returncode != 0, "Should fail with invalid source"
    assert "workflows" in result.stderr, "Error should mention missing workflows/"
    
    # .flows should NOT be created when validation fails
    assert not (repo_dir / ".flows").exists(), ".flows should not be created on validation failure"


def test_flowctl_dry_run_after_init(tmp_path):
    """
    Test flowctl run after init with source workflow.
    
    Flow: init -> run (dry_run) -> validate
    """
    
    repo_dir = tmp_path / "target-repo"
    repo_dir.mkdir()
    (repo_dir / "src").mkdir()
    
    # Step 1: Init with source workflow
    result = subprocess.run(
        [
            "uv", "run", "flowctl", "init",
            "--target", str(repo_dir),
            "--source-workflow-dir", str(FIXTURE_DIR),
        ],
        cwd=str(repo_dir),
        capture_output=True,
        text=True,
    )
    
    assert result.returncode == 0
    
    workflow_dir = repo_dir / ".flows"
    config_file = workflow_dir / "config.yaml"
    workflow_path = workflow_dir / "workflows" / "workflow.yaml"
    
    import uuid
    run_id = f"dry-{uuid.uuid4().hex[:8]}"
    
    # Step 2: Run (dry_run)
    result = subprocess.run(
        [
            "uv", "run", "flowctl", "run",
            "--config", str(config_file),
            "--dry-run",
            "--executor", "echo",
            "--run-id", run_id,
            "--log-format", "json",
            str(workflow_path),
        ],
        cwd=str(repo_dir),
        capture_output=True,
        text=True,
    )
    
    assert result.returncode == 0, f"flowctl run failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    
    # Step 3: Validate
    run_dir = workflow_dir / "runs" / run_id
    assert_test_passed(run_dir, repo_dir)
    
    # Check repo: output (echo executor writes mock artifact)
    implementation = repo_dir / "src" / "implementation.py"
    assert implementation.exists()


@pytest.mark.skip(reason="Manual test - requires opencode CLI and API keys")
def test_flowctl_real_opencode(tmp_path):
    """
    Test real opencode execution.
    
    Flow: init -> run (opencode) -> validate
    """
    
    repo_dir = tmp_path / "target-repo"
    repo_dir.mkdir()
    (repo_dir / "src").mkdir()
    
    # Step 1: Init
    result = subprocess.run(
        [
            "uv", "run", "flowctl", "init",
            "--target", str(repo_dir),
            "--source-workflow-dir", str(FIXTURE_DIR),
        ],
        cwd=str(repo_dir),
        capture_output=True,
        text=True,
    )
    
    assert result.returncode == 0
    
    workflow_dir = repo_dir / ".flows"
    config_file = workflow_dir / "config.yaml"
    workflow_path = workflow_dir / "workflows" / "workflow.yaml"
    
    import uuid
    run_id = f"real-{uuid.uuid4().hex[:8]}"
    
    # Step 2: Run with opencode
    result = subprocess.run(
        [
            "uv", "run", "flowctl", "run",
            "--config", str(config_file),
            "--executor", "opencode",
            "--run-id", run_id,
            "--log-format", "json",
            str(workflow_path),
        ],
        cwd=str(repo_dir),
        capture_output=True,
        text=True,
        timeout=120,
    )
    
    assert result.returncode == 0, f"flowctl run failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    
    # Step 3: Validate
    run_dir = workflow_dir / "runs" / run_id
    assert_test_passed(run_dir, repo_dir)
    
    # Check repo: output - opencode writes to repo_dir/src/
    implementation = repo_dir / "src" / "implementation.py"
    assert implementation.exists()
    content = implementation.read_text()
    assert len(content) > 50
    assert "def " in content or "class " in content