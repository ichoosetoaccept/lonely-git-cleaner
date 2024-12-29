#!/bin/bash

# Exit on error
set -e

# Create and activate virtual environment
echo "🔧 Creating virtual environment..."
uv venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install in development mode
echo "🔧 Installing package in development mode..."
uv pip install -e ".[dev]"

# Install pre-commit and its hooks
echo "🔧 Setting up pre-commit hooks..."
uv pip install pre-commit
pre-commit install --install-hooks
pre-commit install --hook-type commit-msg  # For gitlint

echo "✅ Development environment setup complete!"
echo "🔧 The arb command is now available globally"
echo "📝 Run 'source .venv/bin/activate' to activate the virtual environment for development"
