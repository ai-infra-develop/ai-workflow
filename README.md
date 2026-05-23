# Flowctl

A node-graph workflow engine that takes a software spec and produces a code change.

## Installation

```bash
pip install -e .
```

## Quick Start

### Initialize a project

```bash
flowctl init
```

Creates `.flows/` directory structure:
- `.flows/config.yaml` - Framework configuration
- `.flows/workflows/` - Workflow definitions
- `.flows/prompts/` - Prompt templates
- `.flows/roles/` - Role configurations

### Run a workflow

```bash
# Dry run (mock execution)
uv run flowctl run .flows/workflows/hello-world.yaml --dry-run

# Run with opencode executor on a GitHub issue
uv run flowctl run --executor opencode --issue "https://github.com/ccijunk/ai-workflow/issues/10" --run-id issue-10 .flows/workflows/spec-to-code.yaml
```

### Resume a workflow

If a workflow was interrupted, you can resume from where it stopped:

```bash
# Resume latest run
flowctl run .flows/workflows/spec-to-code.yaml --executor opencode --resume

# Resume specific run
flowctl run .flows/workflows/spec-to-code.yaml --executor opencode --run-id my-run --resume
```

### Logging

Workflow execution is logged to `.flows/runs/<run-id>/execution.log`:

```bash
# JSON format (default)
flowctl run .flows/workflows/spec-to-code.yaml --log-format json

# Text format
flowctl run .flows/workflows/spec-to-code.yaml --log-format text

# Debug level
flowctl run .flows/workflows/spec-to-code.yaml --log-level DEBUG
```

## CLI Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Mock execution, creates placeholder artifacts |
| `--executor` | Executor type: `echo` (mock) or `opencode` |
| `--model` | Model override for opencode executor |
| `--agent` | Agent name for opencode executor |
| `--run-id` | Run identifier (default: `latest`) |
| `--issue` | GitHub issue URL to process |
| `--resume` | Resume from saved state |
| `--log-level` | Log level: DEBUG, INFO, WARNING, ERROR |
| `--log-format` | Log format: `json` or `text` |

### Path Configuration

By default, flowctl uses `.flows/` for workflow definitions and `.flows/runs/` for run artifacts.

You can customize these paths:

**Config file:**

```yaml
# .flows/config.yaml
run_dir: .flows/runs
workflow_dir: .flows
```

**CLI options:**

```bash
# Use custom config location
flowctl run --config ~/my-config.yaml

# Override run directory
flowctl run --run-dir ~/runs

# Override workflow directory
flowctl run --workflow-dir ~/shared-workflows
```

**Precedence:** CLI options > config values > defaults

**Relative paths** are resolved from `repo_dir` when set, otherwise from current working directory where `flowctl` is executed.

### Path Prefixes for Input/Output Resolution

Workflow nodes can specify file locations using path prefixes to control where files are read from or written to:

| Prefix | Directory | Description |
|--------|-----------|-------------|
| `run:` (default) | `run_dir` | Files in the current run directory (`.flows/runs/<run-id>/`) |
| `workflow:` | `workflow_dir` | Shared files in the workflow directory (`.flows/`) |
| `repo:` | `repo_dir` | Files in the repository root (configured via `--repo-dir`) |

**Syntax:**

```yaml
inputs:
  requirement: requirement.md              # Default: run_dir
  memory: workflow:memory/ba.md            # workflow_dir
  architecture: repo:ARCHITECTURE.md      # repo_dir

outputs:
  design: design.md                       # Default: run_dir
  memory_updated: workflow:memory/ba.md    # workflow_dir
```

**Example from spec-to-code-v2.yaml:**

```yaml
nodes:
  architect:
    inputs:
      clarify: clarify.md                           # run_dir (default)
      memory_architect: workflow:memory/architect.md  # workflow_dir
      repo_architecture: repo:ARCHITECTURE.md        # repo_dir
    outputs:
      design_md: design.md                          # run_dir (default)

  reflect:
    inputs:
      memory_ba: workflow:memory/ba.md               # workflow_dir
      memory_architect: workflow:memory/architect.md # workflow_dir
    outputs:
      memory_ba_updated: workflow:memory/ba.md       # workflow_dir (update shared memory)
```

**Use cases:**

- `run:` — Run-specific artifacts (requirements, designs, reviews)
- `workflow:` — Shared memory files persisted across runs (agent memory, templates)
- `repo:` — Repository files (ARCHITECTURE.md, docs/, existing source code)

**Note:** Omitting a prefix defaults to `run:` for backward compatibility.

### Running from Outside the Target Repo

Flowctl can run from anywhere, targeting a specific repository:

```bash
# Running from ai-workflow tool directory
flowctl run --repo-dir /abs/path/to/target-repo .flows/workflows/spec-to-code.yaml
```

**Path Resolution Logic:**

1. **repo_dir** is resolved first:
   - CLI `--repo-dir` (absolute): used as-is
   - CLI `--repo-dir` (relative): resolved from cwd
   - Config `repo_dir` (relative): resolved from config file's parent directory

2. **run_dir** and **workflow_dir** resolve from `repo_dir` (when set), otherwise from cwd:

| Scenario | run_dir resolves to | workflow_dir resolves to |
|----------|--------------------|-------------------------| 
| `--repo-dir /path/to/repo` | `/path/to/repo/.flows/runs` | `/path/to/repo/.flows` |
| Config: `repo_dir: ..` (in `.flows/config.yaml`) | `repo/.flows/runs` | `repo/.flows` |
| No repo_dir set | `cwd/.flows/runs` | `cwd/.flows` |

**Example Directory Structure:**

```
target-repo/                     # --repo-dir
├── src/                         # user's actual source code
├── ARCHITECTURE.md              # repo: prefix reads this
├── .flows/                      # workflow_dir
│   ├── config.yaml              # contains: repo_dir: ..
│   ├── workflows/
│   ├── prompts/
│   ├── memory/                  # workflow: prefix writes here
│   └── runs/                    # run_dir
│       └── issue-10/            # run: prefix writes here
│           ├── requirement.md
│           └── design.md
└── .gitignore                   # should include .flows/
```

## Workflow Structure

Workflows are defined in YAML with nodes and transitions:

```yaml
version: "1"

nodes:
  fetch_issue:
    role: fetcher
    prompt: prompts/fetch-issue.md
    executor: opencode
    inputs: {issue_url: issue-url.txt}
    outputs: {requirement: requirement.md}

  create_branch:
    role: pr-creator
    prompt: prompts/create-branch-issue.md
    executor: opencode
    inputs: {requirement: requirement.md, issue_url: issue-url.txt}
    outputs: {branch_name: branch-name.txt}

transitions:
  - from: __start__
    to: fetch_issue
  - from: fetch_issue
    to: create_branch
  - from: create_branch
    to: __end__
```

### Conditional Transitions

```yaml
transitions:
  - from: testing
    to: review
    when: pass == "yes"
  - from: testing
    to: fix_test
    when: pass == "no"
```

## Run Directory

Each workflow run creates artifacts in `.flows/runs/<run-id>/`:

- `execution.log` - Execution log (JSON or text)
- `state.json` - Saved state for resume (current_node, context, iterations)
- `*.txt`, `*.md` - Output artifacts from nodes

## Tests

```bash
uv run pytest tests/ -v
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation.