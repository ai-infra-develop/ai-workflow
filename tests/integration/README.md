# Integration Tests

E2e tests for flowctl CLI.

## Test Files

| File | Description |
|------|-------------|
| `test_opencode_e2e.py` | Full e2e: `flowctl init` → `flowctl run` → validate |
| `test_path_prefix.py` | Path prefix resolution unit test |
| `validators.py` | Execution result validation helpers |

## Fixture Directory

`tests/integration/opencode_e2e/` - Source workflow_dir for e2e tests.

Contains:
- `workflows/workflow.yaml` - 3-node workflow (setup → write-code → verify)
- `prompts/task.md` - Task prompt for opencode
- `prompts/verify.md` - Verify prompt for echo
- `skills/minimal.md` - Skill file
- `scripts/setup.sh` - Bash setup script
- `.claude/skills/testing/test_skill.md` - Opencode skill (auto-loaded)

See `tests/integration/opencode_e2e/README.md` for details.

## E2e Test Flow

```
1. Create target-repo/ (tmp_path)
2. flowctl init --source-workflow-dir opencode_e2e/
   → Copies workflow files into target-repo/.flows/
3. flowctl run --executor opencode
   → Executes workflow
4. Validate results (execution.log, repo: outputs)
```

## Running Tests

```bash
# All integration tests
pytest tests/integration/ -v

# Specific e2e test
pytest tests/integration/test_opencode_e2e.py -v

# Manual opencode test (requires CLI + API keys)
pytest tests/integration/test_opencode_e2e.py::test_flowctl_real_opencode -v --run-skipped
```

## Directory Structure (After Init)

```
target-repo/                   # repo_dir (tmp_path)
├── src/                       # repo: prefix writes here
│   └── implementation.py      # Opencode output
├── .claude/                   # Skills for opencode auto-loading
│   └── skills/
│       └── testing/
│           └── test_skill.md
└── .flows/                    # workflow_dir (copied from fixture)
    ├── config.yaml            # repo_dir: ..
    ├── workflows/workflow.yaml
    ├── prompts/
    ├── skills/
    ├── scripts/
    └── runs/<run-id>/         # run_dir
        ├── execution.log      # JSON format logs
        ├── setup-output.txt
        └── verified.txt
```

## Validators

`validators.py` provides `assert_test_passed(run_dir, repo_dir)`:

Checks:
- `log_exists` - execution.log exists
- `workflow_completed` - workflow reached `__end__`
- `all_nodes_executed` - all nodes have start/end events
- `executor_logs_valid` - executor logs have required fields
- `no_failures` - no node_failure events
- `repo_structure_valid` - repo/src/ exists with .py files