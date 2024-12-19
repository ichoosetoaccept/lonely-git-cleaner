#!/bin/bash

# Exit on error
set -e

# Create and activate virtual environment
echo "Creating virtual environment..."
uv venv .venv
source .venv/bin/activate

# Install in development mode with dev dependencies
echo "Installing development dependencies..."
uv pip install -e ".[dev]"

# Install globally for testing
echo "Installing globally for development..."
uv pip install -e .

echo "✨ Development environment ready!"
echo "🔧 The git-cleanup command is now available globally"
echo "🧪 Run tests with: source .venv/bin/activate && pytest"
echo "📝 Make changes in src/git_cleanup/ - they'll be reflected globally"
