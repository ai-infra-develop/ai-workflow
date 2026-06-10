# Fix Issues

Apply fixes based on the analysis and review feedback.

## Input

- analysis: Read from analysis.md (run_dir)
- review_comments: Read from review-comments.md (run_dir)
- reject_reason: Read from reject-reason.txt (run_dir, optional - only present after rejection)

## Output

Write to `fixes.md`:
1. List of specific fixes to apply
2. Code snippets showing the changes
3. Explanation of each fix