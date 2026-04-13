# Git Workflow

## Standard Flow

1. Create a short-lived branch.
2. Update contracts or docs first.
3. Implement the smallest useful slice.
4. Add tests.
5. Update docs.
6. Open a PR.
7. Merge back to `main` after review.

## Required Checks

- tests pass
- documentation updated
- contracts updated if required
- screenshots attached when UI changes
- rollback path considered

## Review Expectations

- Focus on correctness first.
- Call out traceability gaps.
- Reject undocumented schema changes.
- Reject black-box behavior without evidence.

