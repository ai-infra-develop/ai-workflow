# Flowctl Quickstart Guide

This guide walks you through flowctl's core features in 10 minutes.

## Prerequisites

```bash
# Install flowctl with uv
uv pip install -e .

# Or install with pip
pip install -e .

# Initialize project structure
uv run flowctl init
```

## 1. Basic Workflow Execution

### Understanding Directory Structure

Flowctl uses three directories for file resolution:

| Directory | Purpose | Default |
|-----------|---------|---------|
| `run_dir` | Run-specific artifacts | `.flows/runs/<run-id>/` |
| `workflow_dir` | Shared files across runs | `.flows/` |
| `repo_dir` | Target repository files | CLI `--repo-dir` |

```bash
# Run with specific run-id (for tracking)
uv run flowctl run .flows/workflows/spec-to-code-v2.yaml \
  --run-id issue-42 \
  --repo-dir /path/to/target-repo \
  --executor opencode \
  --issue "https://github.com/owner/repo/issues/42"

# Dry-run to preview without execution
uv run flowctl run .flows/workflows/spec-to-code-v2.yaml \
  --run-id issue-42 \
  --repo-dir /path/to/target-repo \
  --issue "https://github.com/owner/repo/issues/42" \
  --dry-run
```

**What happens:**
1. Creates `.flows/runs/issue-42/` directory
2. Saves execution log to `execution.log`
3. Saves state to `state.json` for resume
4. Node outputs written to run_dir

### Path Prefixes in Workflows

Use prefixes to specify where files are read/written:

```yaml
inputs:
  requirement: requirement.md              # run_dir (default)
  memory: workflow:memory/ba.md            # workflow_dir
  architecture: repo:ARCHITECTURE.md       # repo_dir

outputs:
  design: design.md                        # run_dir (default)
  memory_updated: workflow:memory/ba.md    # workflow_dir
```

## 2. Human Approval Flow

### Defining Human Approval Nodes

```yaml
nodes:
  human_domain_gate:
    role: human
    prompt: prompts/domain-review.md
    executor: human
    inputs: {clarify: clarify.md}
    outputs: {verdict: verdict.txt, domain_review: domain-review.md}
```

Key attributes:
- `executor: human` — Pauses workflow for manual review
- `role: human` — Human reviewer role
- `outputs.verdict` — Approval/rejection result

```bash
# Start workflow with issue URL
uv run flowctl run .flows/workflows/spec-to-code-v2.yaml \
  --run-id issue-42 \
  --repo-dir /path/to/target-repo \
  --executor opencode \
  --issue "https://github.com/owner/repo/issues/42"

# Workflow pauses at human node
# Output shows:
# Status: PAUSED
# Current node: human_domain_gate
# Reject counts: {}
# Approve: uv run flowctl run --resume --approve --run-id issue-42
# Reject: uv run flowctl run --resume --reject --reject-reason "<reason>" --run-id issue-42
```

### Approving or Rejecting

```bash
# Approve - workflow continues to next node
uv run flowctl run .flows/workflows/spec-to-code-v2.yaml \
  --run-id issue-42 \
  --resume \
  --approve

# Reject - workflow returns to revision node with feedback
uv run flowctl run .flows/workflows/spec-to-code-v2.yaml \
  --run-id issue-42 \
  --resume \
  --reject \
  --reject-reason "Domain model missing User entity"
```

**Reject behavior:**
- Writes `reject-reason.txt` to run_dir
- Workflow returns to revision node (e.g., `ba`)
- Revision node reads `reject-reason.txt` and improves output
- Workflow returns to approval node for re-review
- Maximum 5 rejects per node (prevents infinite loops)

## 3. Resume Flow

### Automatic State Persistence

Every workflow run saves state to `.flows/runs/<run-id>/state.json`:

```json
{
  "status": "PAUSED",
  "current_node": "human_domain_gate",
  "context": {
    "issue_url": "https://github.com/owner/repo/issues/42",
    "clarify_md": "clarify.md"
  },
  "iterations": 3,
  "reject_counts": {"human_domain_gate": 1}
}
```

### Resuming Interrupted Workflows

```bash
# Resume latest run
uv run flowctl run .flows/workflows/spec-to-code-v2.yaml --resume

# Resume specific run
uv run flowctl run .flows/workflows/spec-to-code-v2.yaml --run-id issue-42 --resume

# Resume with approval
uv run flowctl run .flows/workflows/spec-to-code-v2.yaml --run-id issue-42 --resume --approve

# Resume with rejection
uv run flowctl run .flows/workflows/spec-to-code-v2.yaml --run-id issue-42 --resume --reject --reject-reason "..."
```

### Checking Workflow State

```bash
# View state file
cat .flows/runs/issue-42/state.json

# View execution log
cat .flows/runs/issue-42/execution.log

# View artifacts
ls .flows/runs/issue-42/
```

## Complete Example: Spec-to-Code Workflow

This example uses the built-in `spec-to-code-v2.yaml` workflow to transform a GitHub issue into a complete PR.

### Workflow Overview

The `spec-to-code-v2.yaml` workflow:

```yaml
nodes:
  fetch_issue:        # Fetch issue from GitHub URL
    executor: bash
    inputs: {issue_url: issue-url.txt}
    outputs: {requirement: requirement.md, repo_root: repo-root.txt}

  ba:                 # Business analyst clarifies requirements
    executor: opencode
    inputs:
      requirement: requirement.md
      memory_ba: workflow:memory/ba.md
    outputs: {clarify_md: clarify.md}

  human_domain_gate:  # Human reviews domain model
    executor: human
    inputs: {clarify: clarify.md}
    outputs: {verdict: verdict.txt}

  architect:          # Architect designs solution
    executor: opencode
    inputs:
      clarify: clarify.md
      repo_architecture: repo:ARCHITECTURE.md    # Read from target repo
    outputs: {design_md: design.md}

  human_testability_gate:  # Human reviews design
    executor: human

  developer:          # Developer implements code
    executor: opencode

  human_code_review:  # Human reviews code
    executor: human

  test_developer:     # Test developer writes tests
    executor: opencode

  human_test_review:  # Human reviews tests
    executor: human

  create_pr:          # Create GitHub PR
    executor: bash
```

### Running with GitHub Issue

```bash
# Step 1: Run workflow with GitHub issue URL
uv run flowctl run .flows/workflows/spec-to-code-v2.yaml \
  --run-id issue-42 \
  --repo-dir /path/to/target-repo \
  --executor opencode \
  --issue "https://github.com/owner/repo/issues/42"

# This writes issue URL to .flows/runs/issue-42/issue-url.txt
# Workflow starts at fetch_issue node
```

### Human Approval Flow

The workflow has 4 human approval gates:

```bash
# Workflow pauses at human_domain_gate
# Output shows:
# Status: PAUSED
# Current node: human_domain_gate

# Approve domain model:
uv run flowctl run .flows/workflows/spec-to-code-v2.yaml \
  --run-id issue-42 \
  --resume \
  --approve

# Reject with feedback (workflow returns to ba node):
uv run flowctl run .flows/workflows/spec-to-code-v2.yaml \
  --run-id issue-42 \
  --resume \
  --reject \
  --reject-reason "Missing User entity in domain model"
```

### Resume After Interruption

```bash
# Workflow was interrupted (e.g., at human_testability_gate)
# Check current state:
cat .flows/runs/issue-42/state.json

# Resume workflow:
uv run flowctl run .flows/workflows/spec-to-code-v2.yaml \
  --run-id issue-42 \
  --resume

# Resume with approval:
uv run flowctl run .flows/workflows/spec-to-code-v2.yaml \
  --run-id issue-42 \
  --resume \
  --approve
```

### Check Final Results

```bash
# View final state
cat .flows/runs/issue-42/state.json

# View PR URL (final output)
cat .flows/runs/issue-42/pr-url.txt

# View all artifacts
ls .flows/runs/issue-42/
# clarify.md       - Domain model
# design.md        - Architecture design
# implementation.md - Code implementation
# test-results.md  - Test report
# final-review.md  - Final review
# reflect.md       - Reflection/learnings
```

## Quick Reference

| Command | Description |
|---------|-------------|
| `uv run flowctl init` | Initialize `.flows/` structure |
| `uv run flowctl run <workflow> --dry-run` | Mock execution |
| `uv run flowctl run <workflow> --run-id <id>` | Named run for tracking |
| `uv run flowctl run <workflow> --repo-dir <path>` | Target repository path |
| `uv run flowctl run <workflow> --issue <url>` | GitHub issue URL to process |
| `uv run flowctl run <workflow> --resume` | Resume interrupted workflow |
| `uv run flowctl run <workflow> --resume --approve` | Approve pending node |
| `uv run flowctl run <workflow> --resume --reject --reject-reason "<text>"` | Reject with feedback |

## Next Steps

- Read [ARCHITECTURE.md](../ARCHITECTURE.md) for detailed design
- Explore [spec-to-code-v2.yaml](../.flows/workflows/spec-to-code-v2.yaml) for full workflow
- Check [TEST-ARCHITECTURE.md](../docs/sdet/TEST-ARCHITECTURE.md) for testing guide