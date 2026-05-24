import pytest
from pathlib import Path
from click.testing import CliRunner
from flowctl.cli import main
import tempfile
import yaml
import shutil


def test_full_path_configuration():
    """End-to-end test of configurable paths."""
    runner = CliRunner()
    
    temp_root = Path(tempfile.mkdtemp())
    workflow_dir = temp_root / "workflows"
    run_dir = temp_root / "runs"
    
    workflow_dir.mkdir(parents=True)
    run_dir.mkdir(parents=True)
    
    config_path = temp_root / "my-config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump({
            'preferred_executor': 'echo',
            'run_dir': str(run_dir),
            'workflow_dir': str(workflow_dir),
        }, f)
    
    wf_dir = workflow_dir / "workflows"
    wf_dir.mkdir(parents=True)
    
    hello_world = wf_dir / "hello-world.yaml"
    hello_world.write_text("""version: "1"
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
    
    try:
        result = runner.invoke(main, [
            'run',
            '--config', str(config_path),
            '--dry-run',
            '--run-id', 'integration-test',
            str(hello_world),
        ])
        
        assert result.exit_code == 0
        test_run_dir = run_dir / "integration-test"
        assert test_run_dir.exists()
        
        import json
        state_file = test_run_dir / "state.json"
        if state_file.exists():
            state = json.loads(state_file.read_text())
            assert state.get("status") in ["completed", "running"]
    
    finally:
        shutil.rmtree(temp_root)


def test_backward_compatibility():
    """Default paths work without config changes."""
    runner = CliRunner()
    
    # Create temp directory with hello-world workflow
    temp_root = Path(tempfile.mkdtemp())
    flows_dir = temp_root / ".flows"
    flows_dir.mkdir(parents=True)
    
    workflows_dir = flows_dir / "workflows"
    workflows_dir.mkdir()
    
    prompts_dir = flows_dir / "prompts"
    prompts_dir.mkdir()
    
    hello_world = workflows_dir / "hello-world.yaml"
    hello_world.write_text("""version: "1"
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
    
    hello_prompt = prompts_dir / "hello.md"
    hello_prompt.write_text("# Hello World")
    
    try:
        # Change cwd to temp_root for the test
        import os
        old_cwd = os.getcwd()
        os.chdir(temp_root)
        
        result = runner.invoke(main, [
            'run',
            '--dry-run',
            '.flows/workflows/hello-world.yaml',
        ])
        
        os.chdir(old_cwd)
        
        assert result.exit_code == 0
        assert (flows_dir / "runs" / "latest").exists()
    
    finally:
        shutil.rmtree(temp_root)