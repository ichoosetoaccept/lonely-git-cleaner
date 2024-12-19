# git-cleanup 🧹

A comprehensive Git repository cleanup tool that safely removes stale branches and optimizes repository
performance.

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
uv pip install git+https://github.com/yourusername/git-cleanup.git
```

After installation:
- The `git-cleanup` command will be available globally
- No need to activate any virtual environment
- Works in any terminal session or directory
- Persists after terminal restarts

### Development Installation

This sets up a development environment for contributing to the project:

```bash
# Clone the repository
git clone https://github.com/yourusername/git-cleanup.git
cd git-cleanup

# Create and activate virtual environment
uv venv .venv
source .venv/bin/activate

# Install in development mode with dev dependencies
uv pip install -e ".[dev]"
```

Important notes about development installation:
- The virtual environment must be activated to run tests and development tools
- You'll need to reactivate the virtual environment in new terminal sessions
- The tool is only available while the virtual environment is active
- To make development changes available globally, use the global installation method above

If you see "command not found" errors:
1. Check if you're in the right directory
2. Make sure the virtual environment is activated
3. Try reactivating: `source .venv/bin/activate`

## Usage (when in a git repository)

```bash
# Basic cleanup
git-cleanup

# With dry run (shows what would be deleted without actually deleting)
git-cleanup --dry-run

# Interactive mode (asks before each deletion)
git-cleanup --interactive

# Skip garbage collection
git-cleanup --no-gc

# Specify protected branches (default: main)
git-cleanup --protect "main,develop,staging"
```

## How It Works

1. **Fetch and Prune**: Updates repository state and removes references to deleted remote branches
2. **Clean Gone Branches**: Removes local branches whose remote tracking branches no longer exist
3. **Clean Merged Branches**: Removes local branches that have been fully merged into protected branches
4. **Optimize Repository**: Runs garbage collection and pruning to maintain repository health

## Safety Features

- Never deletes protected branches (main by default)
- Only deletes branches that are fully merged or have gone remotes
- Provides dry-run mode to preview changes
- Interactive mode for controlled cleanup
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

You can configure default behavior by creating a `.git-cleanuprc` file in your home directory:

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
# Ensure virtual environment is activated
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

## License

MIT License - feel free to use this in your own projects!
