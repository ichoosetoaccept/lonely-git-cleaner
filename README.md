# lonely-git-cleaner 🧹

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

### Using uv (Recommended)

```bash
uv pip install git+https://github.com/yourusername/lonely-git-cleaner.git
```

### Development Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/lonely-git-cleaner.git
cd lonely-git-cleaner

# Install in development mode with dev dependencies
uv pip install -e ".[dev]"
```

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
# Run tests with coverage
pytest

# Run linting
ruff check .

# Run formatting
ruff format .
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - feel free to use this in your own projects!
