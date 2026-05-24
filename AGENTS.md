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

### When to Use Integration Test Workflow

Follow `tests/integration/README.md` when:

1. **Testing flowctl CLI commands** - init, run, status, upgrade
2. **Testing executor behavior** - opencode, bash, echo
3. **Testing path prefix resolution** - `repo:`, `run:`, `workflow:`
4. **Testing skill auto-loading** - `.claude/skills/` copying and opencode loading
5. **Testing workflow execution** - multi-node workflows, transitions, validation

Development flow:

```
1. Create fixture directory: tests/integration/<test_name>/
   ├── workflows/workflow.yaml
   ├── prompts/
   ├── skills/
   ├── scripts/
   └── .claude/skills/   (if testing opencode skills)

2. Write test in: tests/integration/test_<test_name>.py
   - Use tmp_path for isolated test repo
   - Call flowctl init with --source-workflow-dir
   - Call flowctl run with executor
   - Use validators.assert_test_passed()

3. Run tests: pytest tests/integration/ -v

4. Manual real execution: pytest --run-skipped
```

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