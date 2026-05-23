import tempfile
import pytest
import shutil
from pathlib import Path
from flowctl.executors.bash import BashExecutor
from flowctl.executors.base import ExecutorInput
from flowctl.executors.registry import create_default_registry


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "scripts"


@pytest.fixture
def workflow_dir_with_scripts(tmp_path):
    workflow_dir = tmp_path / ".flows"
    scripts_dir = workflow_dir / "scripts"
    scripts_dir.mkdir(parents=True)
    shutil.copytree(FIXTURES_DIR, scripts_dir, dirs_exist_ok=True)
    return workflow_dir


def test_resolve_script_path_relative():
    executor = BashExecutor(script_path="success.sh")
    workflow_dir = Path("/tmp/.flows")
    resolved = executor._resolve_script_path(workflow_dir)
    assert resolved == workflow_dir / "scripts" / "success.sh"


def test_resolve_script_path_with_prefix():
    executor = BashExecutor(script_path="scripts/success.sh")
    workflow_dir = Path("/tmp/.flows")
    resolved = executor._resolve_script_path(workflow_dir)
    assert resolved == workflow_dir / "scripts" / "success.sh"


def test_resolve_script_path_with_dotdot_raises():
    executor = BashExecutor(script_path="../success.sh")
    workflow_dir = Path("/tmp/.flows")
    with pytest.raises(RuntimeError, match="cannot contain '..'"):
        executor._resolve_script_path(workflow_dir)


def test_resolve_script_path_absolute_raises():
    executor = BashExecutor(script_path="/absolute/path.sh")
    workflow_dir = Path("/tmp/.flows")
    with pytest.raises(RuntimeError, match="must be relative"):
        executor._resolve_script_path(workflow_dir)


def test_validate_script_exists():
    executor = BashExecutor(script_path="success.sh")
    script_file = FIXTURES_DIR / "success.sh"
    executor._validate_script(script_file)


def test_validate_script_not_found():
    executor = BashExecutor(script_path="nonexistent.sh")
    script_file = FIXTURES_DIR / "nonexistent.sh"
    with pytest.raises(RuntimeError, match="Script not found"):
        executor._validate_script(script_file)


def test_validate_script_not_executable():
    executor = BashExecutor(script_path="not_exec.sh")
    with tempfile.TemporaryDirectory() as tmp:
        script_file = Path(tmp) / "not_exec.sh"
        script_file.write_text("#!/bin/bash\necho test")
        with pytest.raises(RuntimeError, match="not executable"):
            executor._validate_script(script_file)


def test_read_inputs_single():
    executor = BashExecutor(script_path="success.sh")
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        (run_dir / "input1.txt").write_text("value1")
        inp = ExecutorInput(
            role="test",
            prompt="Test prompt content",
            prompt_path="test.md",
            skill_paths=[],
            inputs={"input1": "input1.txt"},
            outputs={},
            run_dir=run_dir,
        )
        args = executor._read_inputs(inp)
        assert args == ["value1"]


def test_read_inputs_multiple():
    executor = BashExecutor(script_path="success.sh")
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        (run_dir / "input1.txt").write_text("value1")
        (run_dir / "input2.txt").write_text("value2")
        inp = ExecutorInput(
            role="test",
            prompt="Test prompt content",
            prompt_path="test.md",
            skill_paths=[],
            inputs={"input1": "input1.txt", "input2": "input2.txt"},
            outputs={},
            run_dir=run_dir,
        )
        args = executor._read_inputs(inp)
        assert args == ["value1", "value2"]


def test_read_inputs_missing_file():
    executor = BashExecutor(script_path="success.sh")
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        inp = ExecutorInput(
            role="test",
            prompt="Test prompt content",
            prompt_path="test.md",
            skill_paths=[],
            inputs={"missing": "missing.txt"},
            outputs={},
            run_dir=run_dir,
        )
        args = executor._read_inputs(inp)
        assert args == [""]


def test_read_inputs_empty_file():
    executor = BashExecutor(script_path="success.sh")
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        (run_dir / "empty.txt").write_text("")
        inp = ExecutorInput(
            role="test",
            prompt="Test prompt content",
            prompt_path="test.md",
            skill_paths=[],
            inputs={"empty": "empty.txt"},
            outputs={},
            run_dir=run_dir,
        )
        args = executor._read_inputs(inp)
        assert args == [""]


def test_read_inputs_no_inputs():
    executor = BashExecutor(script_path="success.sh")
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        inp = ExecutorInput(
            role="test",
            prompt="Test prompt content",
            prompt_path="test.md",
            skill_paths=[],
            inputs={},
            outputs={},
            run_dir=run_dir,
        )
        args = executor._read_inputs(inp)
        assert args == []


def test_build_command_basic():
    executor = BashExecutor(script_path="success.sh")
    script_file = FIXTURES_DIR / "success.sh"
    cmd = executor._build_command(script_file, ["arg1", "arg2"])
    assert cmd[0] == "/bin/bash"
    assert "success.sh" in cmd[1]
    assert cmd[2] == "arg1"
    assert cmd[3] == "arg2"


def test_build_command_no_args():
    executor = BashExecutor(script_path="success.sh")
    script_file = FIXTURES_DIR / "success.sh"
    cmd = executor._build_command(script_file, [])
    assert cmd[0] == "/bin/bash"
    assert "success.sh" in cmd[1]
    assert len(cmd) == 2


def test_execute_script_success(workflow_dir_with_scripts):
    executor = BashExecutor(script_path="success.sh", timeout_seconds=60)
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        (run_dir / "output.txt").write_text("test")
        inp = ExecutorInput(
            role="test",
            prompt="Test prompt content",
            prompt_path="test.md",
            skill_paths=[],
            inputs={"arg1": "output.txt"},
            outputs={"output": "output.txt"},
            run_dir=run_dir,
            workflow_dir=workflow_dir_with_scripts,
        )
        result = executor.execute(inp)
        assert result.returncode == 0
        assert "output" in result.outputs


def test_execute_script_failure(workflow_dir_with_scripts):
    executor = BashExecutor(script_path="failure.sh", timeout_seconds=60)
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        inp = ExecutorInput(
            role="test",
            prompt="Test prompt content",
            prompt_path="test.md",
            skill_paths=[],
            inputs={},
            outputs={},
            run_dir=run_dir,
            workflow_dir=workflow_dir_with_scripts,
        )
        with pytest.raises(RuntimeError, match="exit code 1"):
            executor.execute(inp)


def test_execute_script_timeout(workflow_dir_with_scripts):
    executor = BashExecutor(script_path="timeout.sh", timeout_seconds=1)
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        inp = ExecutorInput(
            role="test",
            prompt="Test prompt content",
            prompt_path="test.md",
            skill_paths=[],
            inputs={},
            outputs={},
            run_dir=run_dir,
            workflow_dir=workflow_dir_with_scripts,
        )
        with pytest.raises(RuntimeError, match="timed out"):
            executor.execute(inp)


def test_execute_script_run_dir_env(workflow_dir_with_scripts):
    executor = BashExecutor(script_path="check_env.sh", timeout_seconds=60)
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        inp = ExecutorInput(
            role="test",
            prompt="Test prompt content",
            prompt_path="test.md",
            skill_paths=[],
            inputs={},
            outputs={"run_dir_output": "run_dir.txt"},
            run_dir=run_dir,
            workflow_dir=workflow_dir_with_scripts,
        )
        result = executor.execute(inp)
        assert result.returncode == 0
        assert "run_dir_output" in result.outputs
        assert result.outputs["run_dir_output"].strip() == str(run_dir.resolve())


def test_validate_outputs_all_exist():
    executor = BashExecutor(script_path="success.sh")
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        (run_dir / "output1.txt").write_text("value1")
        (run_dir / "output2.txt").write_text("value2")
        inp = ExecutorInput(
            role="test",
            prompt="Test",
            prompt_path="test.md",
            skill_paths=[],
            inputs={},
            outputs={"out1": "output1.txt", "out2": "output2.txt"},
            run_dir=run_dir,
        )
        executor._validate_outputs(inp.outputs, inp)


def test_validate_outputs_missing_one():
    executor = BashExecutor(script_path="success.sh")
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        (run_dir / "output1.txt").write_text("value1")
        inp = ExecutorInput(
            role="test",
            prompt="Test",
            prompt_path="test.md",
            skill_paths=[],
            inputs={},
            outputs={"out1": "output1.txt", "out2": "output2.txt"},
            run_dir=run_dir,
        )
        with pytest.raises(RuntimeError, match="Missing files"):
            executor._validate_outputs(inp.outputs, inp)


def test_validate_outputs_no_outputs():
    executor = BashExecutor(script_path="success.sh")
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        inp = ExecutorInput(
            role="test",
            prompt="Test",
            prompt_path="test.md",
            skill_paths=[],
            inputs={},
            outputs={},
            run_dir=run_dir,
        )
        executor._validate_outputs({}, inp)


def test_read_outputs_success():
    executor = BashExecutor(script_path="success.sh")
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        (run_dir / "output.txt").write_text("test content")
        inp = ExecutorInput(
            role="test",
            prompt="Test",
            prompt_path="test.md",
            skill_paths=[],
            inputs={},
            outputs={"output": "output.txt"},
            run_dir=run_dir,
        )
        outputs = executor._read_outputs(inp.outputs, inp)
        assert outputs == {"output": "test content"}


def test_registry_has_bash_executor():
    registry = create_default_registry()
    assert "bash" in registry.list_available()


def test_registry_create_bash_executor():
    registry = create_default_registry()
    executor = registry.get("bash", script_path="test.sh", timeout_seconds=30)
    assert isinstance(executor, BashExecutor)
    assert executor.script_path == "test.sh"
    assert executor.timeout_seconds == 30


def test_full_execution_with_workflow_dir(workflow_dir_with_scripts):
    executor = BashExecutor(script_path="success.sh", timeout_seconds=60)
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        
        (run_dir / "input.txt").write_text("test input")
        
        inp = ExecutorInput(
            role="test",
            prompt="Test prompt content",
            prompt_path="test.md",
            skill_paths=[],
            inputs={"input": "input.txt"},
            outputs={"output": "output.txt"},
            run_dir=run_dir,
            workflow_dir=workflow_dir_with_scripts,
        )
        
        result = executor.execute(inp)
        
        assert result.returncode == 0
        assert "output" in result.outputs
        assert (run_dir / "output.txt").exists()
        assert "test output" in result.outputs["output"]


def test_read_inputs_with_run_prefix():
    executor = BashExecutor(script_path="success.sh")
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        (run_dir / "input.txt").write_text("run_value")
        inp = ExecutorInput(
            role="test",
            prompt="Test",
            prompt_path="test.md",
            skill_paths=[],
            inputs={"input": "run:input.txt"},
            outputs={},
            run_dir=run_dir,
        )
        args = executor._read_inputs(inp)
        assert args == ["run_value"]


def test_read_inputs_with_workflow_prefix():
    executor = BashExecutor(script_path="success.sh")
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        workflow_dir = Path(tmp) / "workflow"
        workflow_dir.mkdir()
        (workflow_dir / "shared.txt").write_text("workflow_value")
        inp = ExecutorInput(
            role="test",
            prompt="Test",
            prompt_path="test.md",
            skill_paths=[],
            inputs={"input": "workflow:shared.txt"},
            outputs={},
            run_dir=run_dir,
            workflow_dir=workflow_dir,
        )
        args = executor._read_inputs(inp)
        assert args == ["workflow_value"]


def test_read_inputs_with_repo_prefix():
    executor = BashExecutor(script_path="success.sh")
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        repo_dir = Path(tmp) / "repo"
        repo_dir.mkdir()
        (repo_dir / "ARCHITECTURE.md").write_text("repo_content")
        inp = ExecutorInput(
            role="test",
            prompt="Test",
            prompt_path="test.md",
            skill_paths=[],
            inputs={"arch": "repo:ARCHITECTURE.md"},
            outputs={},
            run_dir=run_dir,
            repo_dir=repo_dir,
        )
        args = executor._read_inputs(inp)
        assert args == ["repo_content"]


def test_validate_outputs_with_workflow_prefix():
    executor = BashExecutor(script_path="success.sh")
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        workflow_dir = Path(tmp) / "workflow"
        workflow_dir.mkdir()
        (workflow_dir / "output.txt").write_text("result")
        inp = ExecutorInput(
            role="test",
            prompt="Test",
            prompt_path="test.md",
            skill_paths=[],
            inputs={},
            outputs={"output": "workflow:output.txt"},
            run_dir=run_dir,
            workflow_dir=workflow_dir,
        )
        executor._validate_outputs(inp.outputs, inp)


def test_read_outputs_with_repo_prefix():
    executor = BashExecutor(script_path="success.sh")
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        repo_dir = Path(tmp) / "repo"
        repo_dir.mkdir()
        (repo_dir / "artifact.md").write_text("repo_artifact")
        inp = ExecutorInput(
            role="test",
            prompt="Test",
            prompt_path="test.md",
            skill_paths=[],
            inputs={},
            outputs={"artifact": "repo:artifact.md"},
            run_dir=run_dir,
            repo_dir=repo_dir,
        )
        outputs = executor._read_outputs(inp.outputs, inp)
        assert outputs == {"artifact": "repo_artifact"}