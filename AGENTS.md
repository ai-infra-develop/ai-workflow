# Agent Instructions

Before starting any task, read README.md to understand how to use flowctl CLI and workflow structure.

## Test Cases

All tests are in `tests/` directory:

### Integration Tests (E2E)

Location: `tests/integration/`

- **Fixture directory**: `tests/integration/opencode_e2e/`
  - Source workflow_dir for e2e tests
  - Contains: `workflows/`, `prompts/`, `skills/`, `scripts/`, `.claude/skills/`
  
- **Target repo demo**: `tests/integration/target-repo/` (gitignored)
  - Created by `flowctl init --source-workflow-dir opencode_e2e/`
  - Structure: `repo/.flows/` and `repo/.claude/skills/`

- **Test file**: `tests/integration/test_opencode_e2e.py`
  - Tests: init validation, dry run, real opencode execution
  - Validator: `tests/integration/validators.py`

### Running Tests

```bash
# All tests
pytest tests/ -v

# Integration tests only
pytest tests/integration/ -v

# Specific e2e test
pytest tests/integration/test_opencode_e2e.py -v

# Run with real opencode (manual)
pytest tests/integration/test_opencode_e2e.py::test_flowctl_real_opencode -v --run-skipped
```

### Test Flow

1. `flowctl init --source-workflow-dir opencode_e2e/` → copies to target-repo/.flows/
2. `flowctl run --executor opencode` → executes workflow
3. Validator checks: execution.log, repo: outputs, all nodes executed

### Key Files

| File | Purpose |
|------|---------|
| `tests/integration/opencode_e2e/workflows/workflow.yaml` | Workflow definition |
| `tests/integration/opencode_e2e/.claude/skills/testing/test_skill.md` | Opencode skill (auto-loaded) |
| `tests/integration/validators.py` | Validation helpers |
| `tests/integration/README.md` | Integration test documentation |