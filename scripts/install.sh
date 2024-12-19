#!/bin/bash

set -e

# Make the main script executable
SCRIPT_DIR="$(dirname "$0")"
BIN_PATH="$SCRIPT_DIR/../bin/git-cleanup"

chmod +x "$BIN_PATH" 2>/dev/null || {
    echo "Error: chmod failed" >&2
}

# Check if we're running in a global npm install
if [[ "$npm_config_global" == "true" ]]; then
    echo "Installing git-cleanup globally..."
    
    # Create symbolic link in a directory that's typically in PATH
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        INSTALL_PATH="/usr/local/bin/git-cleanup"
    else
        # Linux and others
        INSTALL_PATH="$HOME/.local/bin/git-cleanup"
        mkdir -p "$(dirname "$INSTALL_PATH")" 2>/dev/null || {
            echo "Error: mkdir failed" >&2
        }
    fi
    
    # Create the symlink, overwriting if it exists
    ln -sf "$BIN_PATH" "$INSTALL_PATH" 2>/dev/null || {
        echo "Error: ln failed" >&2
    }
    
    echo "Installation complete! You can now use 'git cleanup' anywhere."
else
    echo "Installing git-cleanup locally..."
    echo "Note: For global installation, use 'npm install -g lonely-git-cleaner'"
fi

# Create default config file if it doesn't exist
CONFIG_FILE="$HOME/.git-cleanuprc"
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Creating default configuration file at $CONFIG_FILE"
    {
        cat > "$CONFIG_FILE" << 'EOL' || echo "Error: write failed" >&2
{
  "protectedBranches": ["main", "master"],
  "dryRunByDefault": false,
  "interactive": false,
  "skipGc": false,
  "reflogExpiry": "90.days"
}
EOL
    }
fi

exit 0
