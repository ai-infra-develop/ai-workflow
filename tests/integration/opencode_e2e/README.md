# Opencode E2E Test Fixture

This directory is a **source workflow_dir** for e2e tests.

Used by: `tests/integration/test_opencode_e2e.py`

## Test Flow

1. Create fresh `target-repo/` (tmp_path)
2. Run `flowctl init --source-workflow-dir .` → copies files into `target-repo/.flows/`
3. Run `flowctl run --executor opencode`
4. Validate results

## Directory Structure (Source)

```
opencode_e2e/                  # This directory (source workflow_dir)
├── workflows/
│   └── workflow.yaml          # Workflow definition
├── prompts/
│   ├── task.md                # Task prompt for opencode
│   └── verify.md              # Verify prompt for echo
├── skills/
│   └── minimal.md             # Skill file
└── scripts/
    └── setup.sh               # Setup script (executable)
```

## After Init (Target Repo)

```
target-repo/                   # repo_dir (tmp_path)
├── src/                       # repo: prefix writes here
│   └── implementation.py      # Opencode output
└── .flows/                    # workflow_dir (copied from source)
    ├── config.yaml            # repo_dir: ..
    ├── workflows/workflow.yaml
    ├── prompts/task.md
    ├── prompts/verify.md
    ├── skills/minimal.md
    ├── scripts/setup.sh
    └── runs/<run-id>/         # run_dir (execution logs)
        ├── execution.log
        ├── setup-output.txt
        └── verified.txt
```

## Workflow Nodes

| Node | Executor | Description |
|------|----------|-------------|
| `setup` | bash | Creates `setup-output.txt` in run_dir |
| `write-code` | opencode | Writes `implementation.py` to repo_dir/src/ |
| `verify` | echo | Reads from repo_dir/src/ and writes `verified.txt` |

## Path Prefixes

| Prefix | Resolves To | Usage |
|--------|-------------|-------|
| `repo:` | `target-repo/` | Opencode writes `repo:src/implementation.py` |
| `run:` | `target-repo/.flows/runs/<run-id>/` | Logs and intermediate files |
| `workflow:` | `target-repo/.flows/` | (not used in this test) |

## Running Tests

```bash
# CI tests (dry-run with echo executor)
pytest tests/integration/test_opencode_e2e.py -v

# Manual test (requires opencode CLI)
pytest tests/integration/test_opencode_e2e.py::test_flowctl_real_opencode --run-skipped -v
```