# Arborist

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/ichoosetoaccept/arborist/actions/workflows/test.yml/badge.svg)](https://github.com/ichoosetoaccept/arborist/actions/workflows/test.yml)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-✓-green.svg)](https://conventionalcommits.org)
[![SemVer](https://img.shields.io/badge/SemVer-✓-blue.svg)](https://semver.org/)

A CLI tool to clean up Git branches. Like a skilled arborist pruning trees, this tool helps you maintain a clean Git branch structure by removing merged and stale branches while protecting important ones.

## Features

- 🧼 Safely Removes merged branches
- 🔍 Detects and removes branches with gone remotes
- 🗑️ Performs garbage collection and pruning
- 🛡️ Protects main branch
- ⚡ Optimizes repository performance
- 🔄 Automatic remote pruning

## Installation

### Global Installation (Recommended for Users)

This installs the tool globally on your system, making it available in any terminal session:

```bash
uv pip install git+https://github.com/ichoosetoaccept/arborist.git
```

After installation:
- The `arb` command will be available globally
- No need to activate any virtual environment
- Works in any terminal session or directory
- Persists after terminal restarts

### Development Installation

This sets up a development environment for contributing to the project:

```bash
# Clone the repository
git clone https://github.com/ichoosetoaccept/arborist.git
cd arborist

# Run the development setup script
./scripts/install-dev.sh
```

The install script will:
1. Create a virtual environment for development
2. Install all development dependencies
3. Make the development version available globally

After installation:
- The `arb` command will be available globally
- Changes you make to the code will be reflected immediately
- Run tests with: `source .venv/bin/activate && pytest`
- The virtual environment is only needed for running tests and development tools

## Usage

```bash
# Install the package
uv pip install arborist

# Show help
arb --help

# Run in dry-run mode (no changes made)
arb --dry-run

# Run interactively (default)
arb

# Run non-interactively
arb --no-interactive

# Skip repository optimization
arb --skip-gc
```

## How It Works

1. **Fetch and Prune**: Updates repository state and removes references to deleted remote branches
2. **Clean Gone Branches**: Removes local branches whose remote tracking branches no longer exist
3. **Clean Merged Branches**: Removes local branches that have been fully merged into protected branches
4. **Optimize Repository**: Runs garbage collection and pruning to maintain repository health

## Safety Features

- Interactive by default - asks for confirmation before deleting branches
- Never deletes protected branches (main by default)
- Only deletes branches that are fully merged or have gone remotes
- Provides dry-run mode to preview changes
- Maintains Git's reflog for recovery (default: 90 days)

## Recovery

If you accidentally delete a branch, you can recover it within Git's reflog expiry period
(default: 90 days):

```bash
# See the reflog entries
git reflog

# Recover a branch (replace SHA with the commit hash from reflog)
git branch <branch-name> <SHA>
```

## Configuration

You can configure default behavior by creating a `.arboristrc` file in your home directory:

```json
{
  "protectedBranches": ["main", "develop"],
  "dryRunByDefault": false,
  "interactive": false,
  "skipGc": false,
  "reflogExpiry": "90.days"
}
```

## Development

### Requirements

- Python 3.12 or higher
- uv package manager

### Running Tests

```bash
# Activate the development environment
source .venv/bin/activate

# Run tests with coverage
pytest  # Coverage config is in pyproject.toml

# Run linting
ruff check .

# Run formatting
ruff format .
```

Test coverage includes:
- CLI functionality and options
- Git operations and error handling
- Progress bars and visual feedback
- Configuration management

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Pull Request Process

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Ensure tests pass (`pytest`)
5. Commit your changes using conventional commits
6. Push to your fork
7. Open a Pull Request

### Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/) format. Each commit message should follow this format:

```
<type>(<scope>): <description>

[optional body]
```

Where:
- `type` is one of:
  - `feat`: A new feature
  - `fix`: A bug fix
  - `docs`: Documentation only changes
  - `style`: Changes that don't affect the code's meaning
  - `refactor`: Code changes that neither fix a bug nor add a feature
  - `perf`: Performance improvements
  - `test`: Adding or fixing tests
  - `chore`: Changes to build process or auxiliary tools
- `scope` is optional and indicates the area of change
- `description` is a short description of the change

Example:
```
feat(cli): add support for remote branch cleanup

Add functionality to clean up merged remote branches.
This helps keep the remote repository clean by removing
branches that have been merged into the main branch.
```

### Release Process

Releases are automated through GitHub Actions using semantic versioning rules. The version number is automatically determined based on the changes in each Pull Request:

1. MAJOR version (X.0.0) is bumped when:
   - PR has the `breaking-change` label
   - Changes include backwards-incompatible updates

2. MINOR version (0.X.0) is bumped when:
   - PR has the `enhancement` or `feature` label
   - New features are added in a backwards-compatible manner

3. PATCH version (0.0.X) is bumped when:
   - PR has `bug`, `bugfix`, or `fix` labels
   - Backwards-compatible bug fixes are made
   - Documentation or maintenance changes are made

The release process is fully automated:

1. Create a Pull Request with your changes
2. Apply appropriate labels to your PR:
   - `enhancement`, `feature`: For new features
   - `bug`, `bugfix`, `fix`: For bug fixes
   - `breaking-change`: For breaking changes
   - `documentation`: For documentation updates
   - `performance`: For performance improvements
   - `maintenance`, `dependencies`: For maintenance work

3. When your PR is merged to main:
   - A new version number is automatically determined
   - A new tag is created and pushed
   - The release workflow creates a GitHub release
   - Release notes are automatically generated based on PR labels

The release notes will be automatically organized into categories based on the labels used in Pull Requests.

## License

MIT License - feel free to use this in your own projects!
