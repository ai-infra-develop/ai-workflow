# Flowctl Quickstart Guide

This guide walks you through flowctl's core features in 10 minutes.

## Prerequisites

```bash
# Install flowctl
pip install -e .

# Initialize project structure
flowctl init
```

## 1. Basic Workflow Execution

### Understanding Directory Structure

Flowctl uses three directories for file resolution:

| Directory | Purpose | Default |
|-----------|---------|---------|
| `run_dir` | Run-specific artifacts | `.flows/runs/<run-id>/` |
| `workflow_dir` | Shared files across runs | `.flows/` |
| `repo_dir` | Target repository files | CLI `--repo-dir` |

### Running a Workflow

```bash
# Run with specific run-id (for tracking)
flowctl run .flows/workflows/simple-issue-pr.yaml --run-id issue-42 --dry-run

# Run with repo-dir to access repository files
flowctl run .flows/workflows/spec-to-code-v2.yaml \
  --run-id feature-x \
  --repo-dir /path/to/target-repo \
  --executor opencode
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

### Workflow Execution with Approval

```bash
# Start workflow
flowctl run .flows/workflows/spec-to-code-v2.yaml \
  --run-id feature-x \
  --executor opencode

# Workflow pauses at human node
# Output shows:
# Status: PAUSED
# Current node: human_domain_gate
# Reject counts: {}
# Approve: flowctl run --resume --approve --run-id feature-x
# Reject: flowctl run --resume --reject --reject-reason "<reason>" --run-id feature-x
```

### Approving or Rejecting

```bash
# Approve - workflow continues to next node
flowctl run .flows/workflows/spec-to-code-v2.yaml \
  --run-id feature-x \
  --resume \
  --approve

# Reject - workflow returns to revision node with feedback
flowctl run .flows/workflows/spec-to-code-v2.yaml \
  --run-id feature-x \
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
  "context": {"clarify_md": "clarify.md"},
  "iterations": 3,
  "reject_counts": {"human_domain_gate": 1}
}
```

### Resuming Interrupted Workflows

```bash
# Resume latest run
flowctl run .flows/workflows/spec-to-code-v2.yaml --resume

# Resume specific run
flowctl run .flows/workflows/spec-to-code-v2.yaml --run-id feature-x --resume

# Resume with approval
flowctl run .flows/workflows/spec-to-code-v2.yaml --run-id feature-x --resume --approve

# Resume with rejection
flowctl run .flows/workflows/spec-to-code-v2.yaml --run-id feature-x --resume --reject --reject-reason "..."
```

### Checking Workflow State

```bash
# View state file
cat .flows/runs/feature-x/state.json

# View execution log
cat .flows/runs/feature-x/execution.log

# View artifacts
ls .flows/runs/feature-x/
```

## Complete Example

### Example Workflow: Code Review Pipeline

Create `.flows/workflows/code-review.yaml`:

```yaml
version: "1"

nodes:
  analyze:
    role: developer
    prompt: prompts/analyze.md
    executor: opencode
    inputs:
      code: repo:src/main.py
      architecture: repo:ARCHITECTURE.md
    outputs:
      analysis: analysis.md

  human_review:
    role: human
    prompt: prompts/review-checklist.md
    executor: human
    inputs:
      analysis: analysis.md
    outputs:
      verdict: verdict.txt
      review_comments: review-comments.md

  fix_issues:
    role: developer
    prompt: prompts/fix.md
    executor: opencode
    inputs:
      analysis: analysis.md
      review_comments: review-comments.md
      reject_reason: reject-reason.txt
    outputs:
      fixes: fixes.md

  write_code:
    role: developer
    executor: bash
    command: scripts/apply-fixes.sh
    inputs:
      fixes: fixes.md
      repo_root: repo-root.txt
    outputs:
      result: result.txt

transitions:
  - from: __start__
    to: analyze
  - from: analyze
    to: human_review
  - from: human_review
    to: write_code
    when: verdict == "approved"
  - from: human_review
    to: fix_issues
    when: verdict == "rejected"
  - from: fix_issues
    to: human_review
  - from: write_code
    to: __end__
```

### Running the Example

```bash
# Step 1: Initialize
flowctl init

# Step 2: Create prompts
mkdir -p .flows/prompts
echo "Analyze the code for issues. Output: analysis.md" > .flows/prompts/analyze.md
echo "Review analysis. Write 'approved' or 'rejected' to verdict.txt" > .flows/prompts/review-checklist.md
echo "Fix issues based on review comments" > .flows/prompts/fix.md

# Step 3: Run workflow (dry-run first)
flowctl run .flows/workflows/code-review.yaml \
  --run-id review-1 \
  --repo-dir /path/to/your/repo \
  --dry-run

# Step 4: Run with opencode executor
flowctl run .flows/workflows/code-review.yaml \
  --run-id review-1 \
  --repo-dir /path/to/your/repo \
  --executor opencode

# Step 5: Review output, approve or reject
# Workflow pauses at human_review node

# Approve:
flowctl run .flows/workflows/code-review.yaml --run-id review-1 --resume --approve

# Reject with feedback:
flowctl run .flows/workflows/code-review.yaml \
  --run-id review-1 \
  --resume \
  --reject \
  --reject-reason "Missing error handling in analyze.md"

# Step 6: Check final state
cat .flows/runs/review-1/state.json
cat .flows/runs/review-1/result.txt
```

## Quick Reference

| Command | Description |
|---------|-------------|
| `flowctl init` | Initialize `.flows/` structure |
| `flowctl run <workflow> --dry-run` | Mock execution |
| `flowctl run <workflow> --run-id <id>` | Named run for tracking |
| `flowctl run <workflow> --repo-dir <path>` | Target repository path |
| `flowctl run <workflow> --resume` | Resume interrupted workflow |
| `flowctl run <workflow> --resume --approve` | Approve pending node |
| `flowctl run <workflow> --resume --reject --reject-reason "<text>"` | Reject with feedback |

## Next Steps

- Read [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design
- Explore [spec-to-code-v2.yaml](.flows/workflows/spec-to-code-v2.yaml) for full workflow example
- Check [TEST-ARCHITECTURE.md](docs/sdet/TEST-ARCHITECTURE.md) for testing guide