# Branching Strategy

This repository follows a strict branching strategy to maintain code quality and ensure proper review processes.

## Branch Types

- `main`: Production-ready code
- `feature/*`: New features and non-emergency bug fixes
- `bugfix/*`: Bug fixes
- `release/*`: Release preparation
- `hotfix/*`: Emergency production fixes

## Branch Protection

The `main` branch is protected with the following rules:
- No direct commits allowed
- Pull request required for all changes
- At least one review approval required
- Status checks must pass
- Branch must be up to date before merging
- Linear history required (no merge commits)

## Workflow

1. **Feature Development**
   - Create a new branch from `main`: `feature/your-feature-name`
   - Make your changes
   - Keep branch up to date with `main`
   - Create a pull request when ready

2. **Bug Fixes**
   - For non-critical bugs: `bugfix/bug-description`
   - For critical production bugs: `hotfix/bug-description`

3. **Code Review**
   - All changes require at least one approval
   - Address review comments
   - Status checks must pass
   - Branch must be up to date with `main`

4. **Merging**
   - Squash and merge to maintain clean history
   - Delete branch after merging
   - Keep commit messages clear and descriptive

## Best Practices

- Keep branches short-lived
- One feature/fix per branch
- Regularly sync with `main`
- Write meaningful commit messages
- Reference issues in commits and PRs
- Delete merged branches
