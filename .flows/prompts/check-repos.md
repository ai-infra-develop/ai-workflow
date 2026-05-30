# CVE Fixer — Check Repositories

## Input
- Repository list: `reponame` (file containing repo URLs)

## Task
Check if repositories listed in `reponame` exist and are accessible:

1. **Read reponame file:**
   - Parse repository URLs from the file
   - Each line contains a git repository URL

2. **Check repository existence:**
   - For each repo URL, verify if it's accessible:
     - Use `git ls-remote <url>` to check if repo exists
     - Or use `gh repo view` for GitHub repos
   - Record status for each repo

3. **Generate status report:**
   - List repos that exist
   - List repos that are missing/inaccessible
   - Provide error messages for failed checks

## Output
Write `repo-status.md` with:

```markdown
# Repository Status Check

## Repositories Checked
| Repo URL | Status | Notes |
|----------|--------|-------|
| ... | exists/missing | ... |

## Summary
- **Total repos**: N
- **Accessible**: N
- **Inaccessible**: N

## Action Required
[List of repos that need to be cloned or fixed]

## Selected Repository
[Choose the repo to fix CVE in, or ask user to specify]
```

If all repos are accessible, proceed to next node.
If any repos are missing, report the issue and ask user for guidance.