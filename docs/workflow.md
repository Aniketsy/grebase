# Workflow

## Standard rebase
1. validate repository
2. detect current branch and target
3. git fetch origin (if remote exists)
4. git rebase target
5. resolve conflicts when safe

## Conflict handling
- parse conflict markers
- classify conflict type
- auto-resolve deterministic cases
- auto-regenerate lockfiles when possible
- prompt user for semantic conflicts

## Abort and recovery
- grebase --abort to cancel rebase
- grebase --continue after manual fixes
