# lonely-git-cleaner 🧹

A comprehensive Git repository cleanup tool that safely removes stale branches and optimizes repository performance.

## Features

- 🧼 Removes merged branches
- 🔍 Detects and removes branches with gone remotes
- 🗑️ Performs garbage collection and pruning
- 🛡️ Protects main/master branches
- ⚡ Optimizes repository performance
- 🔄 Automatic remote pruning

## Installation

### Using npm (Recommended)
```bash
npm install -g lonely-git-cleaner
```

### Manual Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/lonely-git-cleaner.git

# Make the script executable
chmod +x ./lonely-git-cleaner/bin/git-cleanup

# Create a symbolic link to make it available globally
ln -s "$(pwd)/lonely-git-cleaner/bin/git-cleanup" /usr/local/bin/
```

## Usage

```bash
# Basic cleanup
git-cleanup

# With dry run (shows what would be deleted without actually deleting)
git-cleanup --dry-run

# Interactive mode (asks before each deletion)
git-cleanup --interactive

# Skip garbage collection
git-cleanup --no-gc

# Specify protected branches (default: main,master)
git-cleanup --protect "main,develop,staging"
```

## How It Works

1. **Fetch and Prune**: Updates repository state and removes references to deleted remote branches
2. **Clean Gone Branches**: Removes local branches whose remote tracking branches no longer exist
3. **Clean Merged Branches**: Removes local branches that have been fully merged into protected branches
4. **Optimize Repository**: Runs garbage collection and pruning to maintain repository health

## Safety Features

- Never deletes protected branches (main/master by default)
- Only deletes branches that are fully merged or have gone remotes
- Provides dry-run mode to preview changes
- Interactive mode for controlled cleanup
- Maintains Git's reflog for recovery (default: 90 days)

## Recovery

If you accidentally delete a branch, you can recover it within Git's reflog expiry period (default: 90 days):

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
  "protectedBranches": ["main", "master", "develop"],
  "dryRunByDefault": false,
  "interactive": false,
  "skipGc": false,
  "reflogExpiry": "90.days"
}
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - feel free to use this in your own projects!
