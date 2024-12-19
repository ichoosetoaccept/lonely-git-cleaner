#!/bin/bash

# Make the main script executable
chmod +x "$(dirname "$0")/../bin/git-cleanup"

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
        mkdir -p "$(dirname "$INSTALL_PATH")"
    fi
    
    # Create the symlink, overwriting if it exists
    ln -sf "$(dirname "$0")/../bin/git-cleanup" "$INSTALL_PATH"
    
    echo "Installation complete! You can now use 'git cleanup' anywhere."
else
    echo "Installing git-cleanup locally..."
    echo "Note: For global installation, use 'npm install -g lonely-git-cleaner'"
fi

# Create default config file if it doesn't exist
CONFIG_FILE="$HOME/.git-cleanuprc"
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Creating default configuration file at $CONFIG_FILE"
    cat > "$CONFIG_FILE" << EOL
{
  "protectedBranches": ["main", "master"],
  "dryRunByDefault": false,
  "interactive": false,
  "skipGc": false,
  "reflogExpiry": "90.days"
}
EOL
fi

exit 0
