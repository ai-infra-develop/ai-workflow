# Design: Fix Path Resolution for External Repo Execution

## Problem

Flowctl cannot run from outside the target repo because relative `run_dir` and `workflow_dir` paths resolve from `Path.cwd()` instead of `repo_dir`.

### Example

```bash
# Running from /home/user/ai-workflow
flowctl run --repo-dir /abs/path/to/repo .flows/workflows/spec-to-code.yaml

# Current behavior (broken):
workflow_dir → /home/user/ai-workflow/.flows
run_dir → /home/user/ai-workflow/.flows/runs

# Expected behavior:
workflow_dir → /abs/path/to/repo/.flows
run_dir → /abs/path/to/repo/.flows/runs
```

### Secondary Issue

`src/flowctl/executors/bash.py` lacks path prefix handling (`repo:`, `workflow:`, `run:`). The `_parse_prefix`/`_resolve_path` pattern is duplicated across 4 files (processor.py, artifact_validator.py, opencode.py, echo.py).

## Solution

Full refactor with shared utility module.

## Architecture

```
src/flowctl/
├── path_utils.py          # NEW: shared prefix parsing utility
├── path_resolver.py       # MODIFIED: use repo_dir as base for relative paths
├── processor.py           # MODIFIED: use path_utils
├── artifact_validator.py  # MODIFIED: use path_utils
└── executors/
    ├── bash.py            # MODIFIED: add prefix handling, use path_utils
    ├── opencode.py        # MODIFIED: use path_utils
    └── echo.py            # MODIFIED: use path_utils
```

### Data Flow

```
CLI (--repo-dir) → path_resolver.py → ExecutorInput (repo_dir field)
                                        ↓
                         path_utils.resolve_prefixed_path()
                                        ↓
                         Correct path resolution for all executors
```

## Component Details

### 1. path_utils.py (New Module)

```python
PREFIX_RUN = "run:"
PREFIX_WORKFLOW = "workflow:"
PREFIX_REPO = "repo:"
DEFAULT_PREFIX = PREFIX_RUN

def parse_path_prefix(filename: str) -> tuple[str, str]:
    """Extract prefix and relative path from filename.
    
    Returns: (prefix, relative_path)
    
    Examples:
        "file.md" → ("run:", "file.md")
        "workflow:memory/ba.md" → ("workflow:", "memory/ba.md")
        "repo:ARCHITECTURE.md" → ("repo:", "ARCHITECTURE.md")
    """
    if filename.startswith(PREFIX_WORKFLOW):
        return PREFIX_WORKFLOW, filename[len(PREFIX_WORKFLOW):]
    elif filename.startswith(PREFIX_REPO):
        return PREFIX_REPO, filename[len(PREFIX_REPO):]
    elif filename.startswith(PREFIX_RUN):
        return PREFIX_RUN, filename[len(PREFIX_RUN):]
    return DEFAULT_PREFIX, filename

def resolve_prefixed_path(
    filename: str,
    run_dir: Path,
    workflow_dir: Path | None = None,
    repo_dir: Path | None = None,
) -> Path:
    """Resolve a prefixed filename to absolute path.
    
    Prefixes:
        run: → run_dir (default)
        workflow: → workflow_dir
        repo: → repo_dir
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

### 2. path_resolver.py Changes

Replace lines 27-30 with repo_dir-aware resolution:

```python
def resolve_paths(...) -> tuple[Path, Path, Path | None]:
    config = _load_config(config_path)
    config_file_dir = Path(config_path).parent.resolve()
    
    # Extract values (CLI > config > defaults)
    run_dir = run_dir_override or config.run_dir or ".flows/runs"
    workflow_dir = workflow_dir_override or config.workflow_dir or ".flows"
    repo_dir = repo_dir_override or config.repo_dir
    
    # Resolve repo_dir FIRST
    repo_dir_path: Path | None = None
    if repo_dir:
        repo_dir_path = Path(repo_dir)
        if not repo_dir_path.is_absolute():
            if repo_dir_override:
                # CLI override: resolve from cwd (user's perspective)
                repo_dir_path = (Path.cwd() / repo_dir_path).resolve()
            else:
                # Config value: resolve from config file's parent
                repo_dir_path = (config_file_dir / repo_dir_path).resolve()
    
    # Use repo_dir as base, fallback to cwd
    base_dir = repo_dir_path or Path.cwd()
    
    run_dir_path = Path(run_dir)
    workflow_dir_path = Path(workflow_dir)
    
    if not run_dir_path.is_absolute():
        run_dir_path = (base_dir / run_dir_path).resolve()
    if not workflow_dir_path.is_absolute():
        workflow_dir_path = (base_dir / workflow_dir_path).resolve()
    
    return run_dir_path, workflow_dir_path, repo_dir_path
```

Key changes:
1. Resolve `repo_dir` first, before other paths
2. Config-relative `repo_dir` resolves from config file's parent
3. CLI-relative `repo_dir` resolves from cwd
4. `run_dir`/`workflow_dir` use `repo_dir` as base when set

### 3. Executor Changes

Replace inline prefix parsing with `path_utils` imports:

```python
from flowctl.path_utils import resolve_prefixed_path

def _resolve_output_path(self, filename: str, inp: ExecutorInput) -> Path:
    return resolve_prefixed_path(
        filename,
        inp.run_dir,
        inp.workflow_dir,
        inp.repo_dir,
    )
```

**bash.py changes (currently has NO prefix handling):**

```python
# _read_inputs
def _read_inputs(self, inp: ExecutorInput) -> list[str]:
    args = []
    for key, path_str in inp.inputs.items():
        input_path = resolve_prefixed_path(path_str, inp.run_dir, inp.workflow_dir, inp.repo_dir)
        # ...

# _validate_outputs
def _validate_outputs(self, outputs: dict, inp: ExecutorInput) -> None:
    for key, path_str in outputs.items():
        output_path = resolve_prefixed_path(path_str, inp.run_dir, inp.workflow_dir, inp.repo_dir)
        # ...

# _read_outputs
def _read_outputs(self, outputs: dict, inp: ExecutorInput) -> dict:
    for key, path_str in outputs.items():
        output_path = resolve_prefixed_path(path_str, inp.run_dir, inp.workflow_dir, inp.repo_dir)
        # ...
```

## Test Changes

### test_path_resolver.py

Update 3 tests asserting `Path.cwd()` in expected values.

Add new tests:

```python
def test_relative_paths_resolve_from_repo_dir():
    """When repo_dir is set, relative run_dir/workflow_dir resolve from it."""
    run_dir, workflow_dir, repo_dir = resolve_paths(
        ".flows/config.yaml", None, None, repo_dir_override="/tmp/my-repo"
    )
    assert run_dir == Path("/tmp/my-repo/.flows/runs")
    assert workflow_dir == Path("/tmp/my-repo/.flows")

def test_config_repo_dir_resolves_from_config_parent():
    """Config repo_dir: .. resolves from config file's parent."""
    with open("/tmp/repo/.flows/config.yaml", "w") as f:
        f.write("repo_dir: ..\n")
    run_dir, workflow_dir, repo_dir = resolve_paths(
        "/tmp/repo/.flows/config.yaml", None, None, None
    )
    assert repo_dir == Path("/tmp/repo")

def test_fallback_to_cwd_when_no_repo_dir():
    """When repo_dir not set, relative paths resolve from cwd."""
    run_dir, workflow_dir, repo_dir = resolve_paths(
        ".flows/config.yaml", None, None, None
    )
    assert run_dir == Path.cwd() / ".flows" / "runs"
    assert workflow_dir == Path.cwd() / ".flows"
```

### test_bash_executor.py

Add tests for prefix handling:

```python
def test_bash_executor_handles_repo_prefix():
    """Bash executor resolves repo: prefixed inputs."""
    
def test_bash_executor_handles_workflow_prefix():
    """Bash executor resolves workflow: prefixed outputs."""
```

## Acceptance Criteria

- [ ] `path_utils.py` created with `parse_path_prefix` and `resolve_prefixed_path`
- [ ] Relative `run_dir` and `workflow_dir` resolve from `repo_dir` when set
- [ ] Config-relative `repo_dir: ..` resolves from config file's parent directory
- [ ] All executors use `path_utils` (bash, opencode, echo)
- [ ] `processor.py` and `artifact_validator.py` use `path_utils`
- [ ] All existing tests pass
- [ ] New tests verify `repo_dir`-anchored resolution
- [ ] Bash executor handles path prefixes

## Files Modified

| File | Change |
|------|--------|
| `src/flowctl/path_utils.py` | NEW |
| `src/flowctl/path_resolver.py` | Fix relative path resolution |
| `src/flowctl/executors/bash.py` | Add prefix handling, use path_utils |
| `src/flowctl/executors/opencode.py` | Use path_utils |
| `src/flowctl/executors/echo.py` | Use path_utils |
| `src/flowctl/processor.py` | Use path_utils |
| `src/flowctl/artifact_validator.py` | Use path_utils |
| `tests/test_path_resolver.py` | Update assertions, add new tests |
| `tests/test_bash_executor.py` | Add prefix handling tests |

## Related

GitHub Issue: https://github.com/ai-infra-develop/ai-workflow/issues/6