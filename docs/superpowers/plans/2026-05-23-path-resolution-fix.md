# Path Resolution Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable running flowctl from outside the target repo with correct path resolution, and eliminate code duplication across executors.

**Architecture:** Create shared `path_utils.py` module for prefix parsing. Modify `path_resolver.py` to resolve relative paths from `repo_dir`. Update all executors and processors to use shared utility.

**Tech Stack:** Python 3.11+, pathlib, pytest

---

## File Structure

| File | Action | Purpose |
|------|--------|---------|
| `src/flowctl/path_utils.py` | Create | Shared prefix parsing utility |
| `src/flowctl/path_resolver.py` | Modify | Fix relative path resolution from repo_dir |
| `src/flowctl/executors/bash.py` | Modify | Add prefix handling, use path_utils |
| `src/flowctl/executors/opencode.py` | Modify | Remove duplicate, use path_utils |
| `src/flowctl/executors/echo.py` | Modify | Remove duplicate, use path_utils |
| `src/flowctl/processor.py` | Modify | Remove duplicate, use path_utils |
| `src/flowctl/artifact_validator.py` | Modify | Remove duplicate, use path_utils |
| `tests/test_path_utils.py` | Create | Tests for path_utils module |
| `tests/test_path_resolver.py` | Modify | Add repo_dir-anchored tests |
| `tests/test_bash_executor.py` | Modify | Add prefix handling tests |

---

### Task 1: Create path_utils.py Module

**Files:**
- Create: `src/flowctl/path_utils.py`
- Test: `tests/test_path_utils.py`

- [ ] **Step 1: Write failing tests for parse_path_prefix**

```python
# tests/test_path_utils.py
import pytest
from pathlib import Path
from flowctl.path_utils import parse_path_prefix, resolve_prefixed_path


def test_parse_path_prefix_no_prefix():
    assert parse_path_prefix("file.md") == ("run:", "file.md")


def test_parse_path_prefix_run_prefix():
    assert parse_path_prefix("run:file.md") == ("run:", "file.md")


def test_parse_path_prefix_workflow_prefix():
    assert parse_path_prefix("workflow:memory/ba.md") == ("workflow:", "memory/ba.md")


def test_parse_path_prefix_repo_prefix():
    assert parse_path_prefix("repo:ARCHITECTURE.md") == ("repo:", "ARCHITECTURE.md")


def test_parse_path_prefix_nested_path():
    assert parse_path_prefix("workflow:memory/sub/ba.md") == ("workflow:", "memory/sub/ba.md")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_path_utils.py::test_parse_path_prefix_no_prefix -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'flowctl.path_utils'"

- [ ] **Step 3: Create path_utils.py with parse_path_prefix**

```python
# src/flowctl/path_utils.py
from pathlib import Path

PREFIX_RUN = "run:"
PREFIX_WORKFLOW = "workflow:"
PREFIX_REPO = "repo:"
DEFAULT_PREFIX = PREFIX_RUN


def parse_path_prefix(filename: str) -> tuple[str, str]:
    """Extract prefix and relative path from filename.
    
    Args:
        filename: Filename with optional prefix (e.g., "run:file.md", "workflow:mem/ba.md")
        
    Returns:
        Tuple of (prefix, relative_path)
        prefix is one of: "run:", "workflow:", "repo:"
    """
    if filename.startswith(PREFIX_WORKFLOW):
        return PREFIX_WORKFLOW, filename[len(PREFIX_WORKFLOW):]
    elif filename.startswith(PREFIX_REPO):
        return PREFIX_REPO, filename[len(PREFIX_REPO):]
    elif filename.startswith(PREFIX_RUN):
        return PREFIX_RUN, filename[len(PREFIX_RUN):]
    return DEFAULT_PREFIX, filename
```

- [ ] **Step 4: Run tests to verify parse_path_prefix passes**

Run: `uv run pytest tests/test_path_utils.py -v -k parse_path_prefix`
Expected: All 5 tests PASS

- [ ] **Step 5: Write failing tests for resolve_prefixed_path**

```python
# tests/test_path_utils.py (append)
def test_resolve_prefixed_path_run_default():
    run_dir = Path("/tmp/run")
    result = resolve_prefixed_path("file.md", run_dir)
    assert result == run_dir / "file.md"


def test_resolve_prefixed_path_run_explicit():
    run_dir = Path("/tmp/run")
    result = resolve_prefixed_path("run:file.md", run_dir)
    assert result == run_dir / "file.md"


def test_resolve_prefixed_path_workflow():
    run_dir = Path("/tmp/run")
    workflow_dir = Path("/tmp/workflow")
    result = resolve_prefixed_path("workflow:memory/ba.md", run_dir, workflow_dir)
    assert result == workflow_dir / "memory/ba.md"


def test_resolve_prefixed_path_repo():
    run_dir = Path("/tmp/run")
    repo_dir = Path("/tmp/repo")
    result = resolve_prefixed_path("repo:ARCHITECTURE.md", run_dir, repo_dir=repo_dir)
    assert result == repo_dir / "ARCHITECTURE.md"


def test_resolve_prefixed_path_workflow_fallback_to_run():
    run_dir = Path("/tmp/run")
    result = resolve_prefixed_path("workflow:file.md", run_dir, workflow_dir=None)
    assert result == run_dir / "file.md"


def test_resolve_prefixed_path_repo_fallback_to_run():
    run_dir = Path("/tmp/run")
    result = resolve_prefixed_path("repo:file.md", run_dir, repo_dir=None)
    assert result == run_dir / "file.md"
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `uv run pytest tests/test_path_utils.py::test_resolve_prefixed_path_run_default -v`
Expected: FAIL with "NameError: name 'resolve_prefixed_path' is not defined"

- [ ] **Step 7: Add resolve_prefixed_path to path_utils.py**

```python
# src/flowctl/path_utils.py (append)
def resolve_prefixed_path(
    filename: str,
    run_dir: Path,
    workflow_dir: Path | None = None,
    repo_dir: Path | None = None,
) -> Path:
    """Resolve a prefixed filename to absolute path.
    
    Args:
        filename: Filename with optional prefix
        run_dir: Base directory for run: prefix (and fallback)
        workflow_dir: Base directory for workflow: prefix (optional)
        repo_dir: Base directory for repo: prefix (optional)
        
    Returns:
        Resolved absolute Path
    """
    prefix, rel_path = parse_path_prefix(filename)
    
    if prefix == PREFIX_WORKFLOW:
        base_dir = workflow_dir or run_dir
    elif prefix == PREFIX_REPO:
        base_dir = repo_dir or run_dir
    else:
        base_dir = run_dir
    
    return base_dir / rel_path
```

- [ ] **Step 8: Run tests to verify resolve_prefixed_path passes**

Run: `uv run pytest tests/test_path_utils.py -v -k resolve_prefixed_path`
Expected: All 6 tests PASS

- [ ] **Step 9: Run all path_utils tests**

Run: `uv run pytest tests/test_path_utils.py -v`
Expected: All 11 tests PASS

- [ ] **Step 10: Commit path_utils module**

```bash
git add src/flowctl/path_utils.py tests/test_path_utils.py
git commit -m "feat: add path_utils module for shared prefix parsing"
```

---

### Task 2: Fix path_resolver.py

**Files:**
- Modify: `src/flowctl/path_resolver.py`
- Test: `tests/test_path_resolver.py`

- [ ] **Step 1: Write failing tests for repo_dir-anchored resolution**

```python
# tests/test_path_resolver.py (append)
import tempfile


def test_relative_paths_resolve_from_repo_dir():
    """When repo_dir is set via CLI, relative run_dir/workflow_dir resolve from it."""
    run_dir, workflow_dir, repo_dir = resolve_paths(
        ".flows/config.yaml", None, None, repo_dir_override="/tmp/my-repo"
    )
    assert run_dir == Path("/tmp/my-repo/.flows/runs")
    assert workflow_dir == Path("/tmp/my-repo/.flows")
    assert repo_dir == Path("/tmp/my-repo")


def test_config_repo_dir_relative_resolves_from_config_parent():
    """Config repo_dir: .. resolves from config file's parent directory."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_dir = Path(tmp)
        flows_dir = repo_dir / ".flows"
        flows_dir.mkdir()
        config_file = flows_dir / "config.yaml"
        config_file.write_text("repo_dir: ..\nrun_dir: .flows/runs\nworkflow_dir: .flows\n")
        
        run_dir, workflow_dir, repo_dir_resolved = resolve_paths(
            str(config_file), None, None, None
        )
        
        assert repo_dir_resolved == repo_dir.resolve()
        assert run_dir == repo_dir.resolve() / ".flows" / "runs"
        assert workflow_dir == repo_dir.resolve() / ".flows"


def test_cli_repo_dir_relative_resolves_from_cwd():
    """CLI --repo-dir with relative path resolves from cwd."""
    run_dir, workflow_dir, repo_dir = resolve_paths(
        ".flows/config.yaml", None, None, repo_dir_override="relative-repo"
    )
    assert repo_dir == Path.cwd() / "relative-repo"
    assert run_dir == repo_dir / ".flows" / "runs"
    assert workflow_dir == repo_dir / ".flows"


def test_relative_paths_fallback_to_cwd_without_repo_dir():
    """When repo_dir not set, relative paths still resolve from cwd."""
    run_dir, workflow_dir, repo_dir = resolve_paths(
        ".flows/config.yaml", None, None, None
    )
    assert repo_dir is None
    assert run_dir == Path.cwd() / ".flows" / "runs"
    assert workflow_dir == Path.cwd() / ".flows"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_path_resolver.py::test_relative_paths_resolve_from_repo_dir -v`
Expected: FAIL - paths resolve from cwd, not repo_dir

- [ ] **Step 3: Update path_resolver.py to resolve from repo_dir**

Replace the entire `resolve_paths` function:

```python
# src/flowctl/path_resolver.py
from pathlib import Path
from .models import FlowctlConfig


def resolve_paths(
    config_path: str,
    run_dir_override: str | None,
    workflow_dir_override: str | None,
    repo_dir_override: str | None = None,
) -> tuple[Path, Path, Path | None]:
    """Resolve run_dir, workflow_dir, and repo_dir from config + CLI overrides.
    
    Precedence: CLI > config > defaults
    Resolution order: repo_dir first, then run_dir/workflow_dir from repo_dir or cwd
    
    Returns:
        Tuple of (run_dir, workflow_dir, repo_dir or None)
    """
    config = _load_config(config_path)
    config_file_dir = Path(config_path).parent.resolve()
    
    run_dir = run_dir_override or config.run_dir or ".flows/runs"
    workflow_dir = workflow_dir_override or config.workflow_dir or ".flows"
    repo_dir = repo_dir_override or config.repo_dir
    
    repo_dir_path: Path | None = None
    if repo_dir:
        repo_dir_path = Path(repo_dir)
        if not repo_dir_path.is_absolute():
            if repo_dir_override:
                repo_dir_path = (Path.cwd() / repo_dir_path).resolve()
            else:
                repo_dir_path = (config_file_dir / repo_dir_path).resolve()
    
    base_dir = repo_dir_path or Path.cwd()
    
    run_dir_path = Path(run_dir)
    workflow_dir_path = Path(workflow_dir)
    
    if not run_dir_path.is_absolute():
        run_dir_path = (base_dir / run_dir_path).resolve()
    if not workflow_dir_path.is_absolute():
        workflow_dir_path = (base_dir / workflow_dir_path).resolve()
    
    return run_dir_path, workflow_dir_path, repo_dir_path


def _load_config(config_path: str) -> FlowctlConfig:
    """Load config from file, return defaults if not found."""
    path = Path(config_path)
    if path.exists():
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return FlowctlConfig(**data)
    return FlowctlConfig()
```

- [ ] **Step 4: Run new tests to verify they pass**

Run: `uv run pytest tests/test_path_resolver.py -v -k repo_dir`
Expected: All 4 new tests PASS

- [ ] **Step 5: Run all path_resolver tests to check for breakage**

Run: `uv run pytest tests/test_path_resolver.py -v`
Expected: All tests PASS (existing tests should still work - they don't use repo_dir)

- [ ] **Step 6: Commit path_resolver fix**

```bash
git add src/flowctl/path_resolver.py tests/test_path_resolver.py
git commit -m "fix: resolve relative paths from repo_dir when set"
```

---

### Task 3: Update artifact_validator.py to use path_utils

**Files:**
- Modify: `src/flowctl/artifact_validator.py`

- [ ] **Step 1: Replace duplicate prefix parsing with path_utils import**

```python
# src/flowctl/artifact_validator.py
from pathlib import Path
from flowctl.path_utils import resolve_prefixed_path


def validate_artifacts(
    outputs: dict[str, str],
    run_dir: Path,
    workflow_dir: Path | None = None,
    repo_dir: Path | None = None,
) -> list[str]:
    """Validate output artifacts exist at resolved paths."""
    errors: list[str] = []
    for key, filename in outputs.items():
        resolved_path = resolve_prefixed_path(filename, run_dir, workflow_dir, repo_dir)
        
        if not resolved_path.exists():
            errors.append(f"Output '{key}' missing: {resolved_path}")
        elif resolved_path.stat().st_size == 0:
            errors.append(f"Output '{key}' is empty: {resolved_path}")
    return errors
```

- [ ] **Step 2: Run artifact_validator tests**

Run: `uv run pytest tests/test_artifact_validator.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit artifact_validator refactor**

```bash
git add src/flowctl/artifact_validator.py
git commit -m "refactor: artifact_validator use path_utils"
```

---

### Task 4: Update processor.py to use path_utils

**Files:**
- Modify: `src/flowctl/processor.py`

- [ ] **Step 1: Replace duplicate prefix parsing with path_utils import**

```python
# src/flowctl/processor.py
from typing import Protocol
import re
import logging
from pathlib import Path
from flowctl.path_utils import parse_path_prefix, resolve_prefixed_path
from flowctl.models import Node

logger = logging.getLogger(__name__)


class Processor(Protocol):
    """Interface for prompt/content processors."""
    
    def process(self, content: str, context: dict) -> str:
        """Transform content before execution."""
        ...


class PromptProcessor:
    """Processor that injects I/O sections from node definitions."""
    
    def process(self, content: str, context: dict) -> str:
        if not isinstance(content, str):
            return content
        
        node = context.get("node")
        if not node:
            return content
        
        if node.executor == "bash":
            return content
        
        try:
            cleaned = self._remove_existing_sections(content)
            input_section = self._generate_input_section(node.inputs, context)
            output_section = self._generate_output_section(node.outputs, context)
            
            sections = []
            if input_section:
                sections.append(input_section)
            if output_section:
                sections.append(output_section)
            
            if sections:
                header = "\n\n".join(sections)
                return f"{header}\n\n{cleaned}"
            
            return cleaned
        except Exception as e:
            logger.warning(f"Processor failed for node: {e}")
            return content
    
    def _remove_existing_sections(self, content: str) -> str:
        try:
            input_pattern = r'(?i)^## input.*?(?=^## |\Z)'
            output_pattern = r'(?i)^## output.*?(?=^## |\Z)'
            
            cleaned = re.sub(input_pattern, '', content, flags=re.MULTILINE | re.DOTALL)
            cleaned = re.sub(output_pattern, '', cleaned, flags=re.MULTILINE | re.DOTALL)
            
            if cleaned != content:
                return cleaned.strip()
            return content
        except Exception as e:
            logger.warning(f"Failed to remove sections: {e}")
            return content
    
    def _generate_input_section(self, inputs: dict[str, str], context: dict) -> str:
        if not inputs:
            return ""
        
        run_dir = context.get("run_dir")
        workflow_dir = context.get("workflow_dir")
        repo_dir = context.get("repo_dir")
        
        lines = ["## Input", ""]
        for key, filename in inputs.items():
            prefix, rel_path = parse_path_prefix(filename)
            abs_path = resolve_prefixed_path(filename, run_dir, workflow_dir, repo_dir)
            lines.append(f"- {key}: Read from {rel_path} ({prefix}_dir: {abs_path})")
        
        return "\n".join(lines)
    
    def _generate_output_section(self, outputs: dict[str, str], context: dict) -> str:
        if not outputs:
            return ""
        
        run_dir = context.get("run_dir")
        workflow_dir = context.get("workflow_dir")
        repo_dir = context.get("repo_dir")
        
        lines = ["## Output", ""]
        for key, filename in outputs.items():
            prefix, rel_path = parse_path_prefix(filename)
            abs_path = resolve_prefixed_path(filename, run_dir, workflow_dir, repo_dir)
            lines.append(f"- {key}: Write to {rel_path} ({prefix}_dir: {abs_path})")
        
        return "\n".join(lines)
```

- [ ] **Step 2: Run processor tests**

Run: `uv run pytest tests/test_processor.py -v`
Expected: All tests PASS

- [ ] **Step 3: Run SDET processor tests**

Run: `uv run pytest tests/sdet/test_processor_unit.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit processor refactor**

```bash
git add src/flowctl/processor.py
git commit -m "refactor: processor use path_utils"
```

---

### Task 5: Update opencode.py to use path_utils

**Files:**
- Modify: `src/flowctl/executors/opencode.py`

- [ ] **Step 1: Replace duplicate prefix parsing with path_utils import**

```python
# src/flowctl/executors/opencode.py
import subprocess
import json
from pathlib import Path
from .base import ExecutorAdapter, ExecutorInput, ExecutorResult
from flowctl.path_utils import resolve_prefixed_path


class OpencodeAdapter(ExecutorAdapter):
    def __init__(self, model: str = None, agent: str = None):
        self.model = model
        self.agent = agent

    def execute(self, inp: ExecutorInput) -> ExecutorResult:
        prompt_content = self._load_prompt(inp)
        
        cmd = ["opencode", "run"]
        abs_run_dir = inp.run_dir.resolve()
        cmd.extend(["--dir", str(abs_run_dir)])
        cmd.extend(["--format", "json"])

        if self.model:
            cmd.extend(["--model", self.model])
        if self.agent:
            cmd.extend(["--agent", self.agent])

        for skill_path in inp.skill_paths:
            if inp.workflow_dir:
                src_skill = inp.workflow_dir / skill_path
            else:
                src_skill = Path(skill_path)
            skill_file = inp.run_dir / Path(skill_path).name
            if src_skill.exists():
                skill_file.write_text(src_skill.read_text())
            cmd.extend(["--file", str(skill_file)])

        proc = subprocess.run(
            cmd,
            input=prompt_content,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(abs_run_dir),
        )

        outputs = {}
        session_id = None

        if proc.returncode == 0:
            session_id = self._extract_session_id(proc.stdout) or self._extract_session_id(proc.stderr)
            self._extract_and_write_outputs(proc.stdout, inp.outputs, inp.run_dir)
            for key, filename in inp.outputs.items():
                artifact_path = resolve_prefixed_path(filename, inp.run_dir, inp.workflow_dir, inp.repo_dir)
                if artifact_path.exists():
                    outputs[key] = artifact_path.read_text()

        if session_id:
            self._delete_session(session_id)

        return ExecutorResult(
            outputs=outputs,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )

    def _extract_session_id(self, stdout: str) -> str | None:
        for line in stdout.splitlines():
            try:
                event = json.loads(line)
                if "sessionID" in event:
                    return event["sessionID"]
            except json.JSONDecodeError:
                continue
        return None

    def _delete_session(self, session_id: str):
        subprocess.run(
            ["opencode", "session", "delete", session_id],
            capture_output=True,
            text=True,
        )

    def _load_prompt(self, inp: ExecutorInput) -> str:
        if inp.prompt:
            return inp.prompt
        
        prompt_lines = [f"Role: {inp.role}"]
        if inp.prompt_path:
            prompt_lines.append(f"Prompt file: {inp.prompt_path}")
        return "\n".join(prompt_lines)

    def _extract_and_write_outputs(self, stdout: str, expected_outputs: dict, run_dir: Path):
        pass
```

- [ ] **Step 2: Run opencode executor tests**

Run: `uv run pytest tests/test_executors.py -v -k opencode`
Expected: All tests PASS

- [ ] **Step 3: Commit opencode refactor**

```bash
git add src/flowctl/executors/opencode.py
git commit -m "refactor: opencode executor use path_utils"
```

---

### Task 6: Update echo.py to use path_utils

**Files:**
- Modify: `src/flowctl/executors/echo.py`

- [ ] **Step 1: Replace duplicate prefix parsing with path_utils import**

```python
# src/flowctl/executors/echo.py
from pathlib import Path
from .base import ExecutorAdapter, ExecutorInput, ExecutorResult
from flowctl.path_utils import resolve_prefixed_path


class EchoAdapter(ExecutorAdapter):
    def execute(self, inp: ExecutorInput) -> ExecutorResult:
        stdout_lines = [
            f"Role: {inp.role}",
            f"Prompt Path: {inp.prompt_path}",
            "",
            "=" * 60,
            "PROCESSED PROMPT",
            "=" * 60,
            inp.prompt,
            "=" * 60,
            "",
            "=" * 60,
            "RESOLVED PATHS",
            "=" * 60,
        ]
        
        if inp.inputs:
            stdout_lines.append("Inputs:")
            for key, filename in inp.inputs.items():
                resolved = resolve_prefixed_path(filename, inp.run_dir, inp.workflow_dir, inp.repo_dir)
                stdout_lines.append(f"  {key}: {filename} -> {resolved}")
        
        if inp.outputs:
            stdout_lines.append("Outputs:")
            for key, filename in inp.outputs.items():
                resolved = resolve_prefixed_path(filename, inp.run_dir, inp.workflow_dir, inp.repo_dir)
                stdout_lines.append(f"  {key}: {filename} -> {resolved}")
        
        stdout_lines.append("=" * 60)
        
        outputs = {}
        for key, filename in inp.inputs.items():
            resolved = resolve_prefixed_path(filename, inp.run_dir, inp.workflow_dir, inp.repo_dir)
            if resolved.exists():
                outputs[key] = resolved.read_text()
        
        for key, filename in inp.outputs.items():
            resolved = resolve_prefixed_path(filename, inp.run_dir, inp.workflow_dir, inp.repo_dir)
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(f"echo: mock artifact for {key}")
            outputs[key] = str(resolved)
        
        return ExecutorResult(
            outputs=outputs,
            returncode=0,
            stdout="\n".join(stdout_lines),
            stderr="",
        )
```

- [ ] **Step 2: Run echo executor tests**

Run: `uv run pytest tests/test_executors.py -v -k echo`
Expected: All tests PASS

- [ ] **Step 3: Commit echo refactor**

```bash
git add src/flowctl/executors/echo.py
git commit -m "refactor: echo executor use path_utils"
```

---

### Task 7: Update bash.py to use path_utils (NEW prefix handling)

**Files:**
- Modify: `src/flowctl/executors/bash.py`
- Test: `tests/test_bash_executor.py`

- [ ] **Step 1: Write failing tests for bash prefix handling**

```python
# tests/test_bash_executor.py (append)
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_bash_executor.py::test_read_inputs_with_run_prefix -v`
Expected: FAIL - bash executor doesn't handle prefixes

- [ ] **Step 3: Update bash.py to use path_utils**

```python
# src/flowctl/executors/bash.py
import subprocess
import os
from pathlib import Path
from typing import Optional
from .base import ExecutorAdapter, ExecutorInput, ExecutorResult
from flowctl.path_utils import resolve_prefixed_path


class BashExecutor(ExecutorAdapter):
    """
    Executes shell scripts for deterministic operations.

    Scripts are located in .flows/scripts/ and receive inputs as positional
    arguments. The RUN_DIR environment variable points to the run directory
    where outputs should be written.
    """

    def __init__(self, script_path: str, timeout_seconds: int = 60):
        self.script_path = script_path
        self.timeout_seconds = timeout_seconds

    def execute(self, inp: ExecutorInput) -> ExecutorResult:
        """
        Execute the bash script with inputs as positional arguments.

        Args:
            inp: ExecutorInput containing inputs, outputs, and run_dir

        Returns:
            ExecutorResult with outputs, returncode, stdout, stderr

        Raises:
            RuntimeError: If script fails validation or execution
        """
        script_file = self._resolve_script_path(inp.workflow_dir)
        self._validate_script(script_file)
        args = self._read_inputs(inp)
        cmd = self._build_command(script_file, args)
        result = self._execute_script(cmd, inp.run_dir)

        if result.returncode != 0:
            raise RuntimeError(
                f"Script execution failed with exit code {result.returncode}\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )

        self._validate_outputs(inp.outputs, inp)
        outputs = self._read_outputs(inp.outputs, inp)

        return ExecutorResult(
            outputs=outputs,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    def _resolve_script_path(self, workflow_dir: Optional[Path]) -> Path:
        """Resolve script path relative to .flows/scripts/"""
        if not self.script_path:
            raise RuntimeError("No script path specified")

        script_rel = self.script_path
        if script_rel.startswith("scripts/"):
            script_rel = script_rel[len("scripts/"):]

        if ".." in script_rel:
            raise RuntimeError(f"Script path cannot contain '..': {self.script_path}")

        if script_rel.startswith("/") or (len(script_rel) > 1 and script_rel[1] == ":"):
            raise RuntimeError(f"Script path must be relative: {self.script_path}")

        if workflow_dir:
            return workflow_dir / "scripts" / script_rel
        else:
            return Path("scripts") / script_rel

    def _validate_script(self, script_file: Path) -> None:
        """Validate script exists and is executable."""
        if not script_file.exists():
            raise RuntimeError(f"Script not found: {script_file}")

        if not script_file.is_file():
            raise RuntimeError(f"Script path is not a file: {script_file}")

        if not script_file.stat().st_mode & 0o111:
            raise RuntimeError(f"Script is not executable: {script_file}")

    def _read_inputs(self, inp: ExecutorInput) -> list[str]:
        """Read input file contents as strings for positional arguments."""
        args = []

        for key, path_str in inp.inputs.items():
            input_path = resolve_prefixed_path(path_str, inp.run_dir, inp.workflow_dir, inp.repo_dir)

            if input_path.exists():
                args.append(input_path.read_text().rstrip('\n'))
            else:
                args.append("")

        return args

    def _build_command(self, script_file: Path, args: list[str]) -> list[str]:
        """Build command with properly escaped arguments."""
        cmd = ["/bin/bash", str(script_file.resolve())]
        cmd.extend(args)
        return cmd

    def _execute_script(
        self, cmd: list[str], run_dir: Path
    ) -> subprocess.CompletedProcess:
        """Execute script with RUN_DIR environment variable."""
        env = {
            **os.environ,
            "RUN_DIR": str(run_dir.resolve()),
        }

        try:
            return subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(run_dir.resolve()),
                env=env,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"Script execution timed out after {self.timeout_seconds}s: {cmd[1]}"
            )

    def _validate_outputs(self, outputs: dict[str, str], inp: ExecutorInput) -> None:
        """Validate all output files exist."""
        if not outputs:
            return

        missing = []
        for key, path_str in outputs.items():
            output_path = resolve_prefixed_path(path_str, inp.run_dir, inp.workflow_dir, inp.repo_dir)
            if not output_path.exists():
                missing.append(f"{key}: {output_path}")

        if missing:
            raise RuntimeError(
                f"Output validation failed. Missing files:\n" +
                "\n".join(f"  - {m}" for m in missing)
            )

    def _read_outputs(self, outputs: dict[str, str], inp: ExecutorInput) -> dict[str, str]:
        """Read output file contents."""
        result = {}
        for key, path_str in outputs.items():
            output_path = resolve_prefixed_path(path_str, inp.run_dir, inp.workflow_dir, inp.repo_dir)
            if output_path.exists():
                result[key] = output_path.read_text()
        return result
```

- [ ] **Step 4: Run new bash prefix tests**

Run: `uv run pytest tests/test_bash_executor.py -v -k prefix`
Expected: All 5 new tests PASS

- [ ] **Step 5: Run all bash executor tests**

Run: `uv run pytest tests/test_bash_executor.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit bash executor refactor**

```bash
git add src/flowctl/executors/bash.py tests/test_bash_executor.py
git commit -m "feat: bash executor add prefix handling via path_utils"
```

---

### Task 8: Run Full Test Suite

- [ ] **Step 1: Run all tests**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Run integration tests**

Run: `uv run pytest tests/integration/ -v`
Expected: All tests PASS

- [ ] **Step 3: Verify no regressions with mixed executor tests**

Run: `uv run pytest tests/test_mixed_executors.py -v`
Expected: All tests PASS

---

### Task 9: Update Documentation

- [ ] **Step 1: Update README.md path resolution section**

Change line 105 from:
```
Relative paths are resolved from current working directory where `flowctl` is executed.
```

To:
```
Relative paths are resolved from `repo_dir` when set, otherwise from current working directory where `flowctl` is executed.
```

- [ ] **Step 2: Commit documentation update**

```bash
git add README.md
git commit -m "docs: update path resolution documentation"
```

---

### Task 10: Final Verification and Push

- [ ] **Step 1: Run complete test suite one more time**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Verify lint passes**

Run: `uv run ruff check src/`
Expected: No errors

- [ ] **Step 3: Push all commits**

```bash
git push origin main
```

---

## Self-Review Checklist

- [x] Spec coverage: All requirements from design doc have corresponding tasks
- [x] Placeholder scan: No TBD, TODO, or vague instructions
- [x] Type consistency: All function signatures match across tasks
- [x] File structure: All files listed with exact paths
- [x] Test coverage: Each new feature has tests before implementation
- [x] Commit granularity: Each task results in one logical commit