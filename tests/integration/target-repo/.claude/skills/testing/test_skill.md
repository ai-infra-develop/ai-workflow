# Skill: test_skill

This is a test skill for verifying opencode skill loading.

## Purpose

Test that opencode can load skills from the target repository.

## Instructions

When this skill is loaded:
1. Acknowledge the skill was loaded
2. Confirm you can read the skill content
3. State: "test_skill loaded successfully"

## Example Usage

```bash
opencode run --dir /path/to/repo --file .claude/skills/testing/test_skill.md
```

## Expected Response

The AI should respond with:
- "test_skill loaded successfully"
- Confirmation of skill instructions understood