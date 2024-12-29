#!/bin/bash

# Exit on error
set -e

# Create and activate virtual environment
echo "🔧 Creating virtual environment..."
uv venv .venv

# Install in development mode
echo "🔧 Installing package in development mode..."
source .venv/bin/activate
uv pip install -e ".[dev]"

# Install pre-commit hooks
echo "🔧 Installing pre-commit hooks..."
pre-commit install

echo "✅ Development environment setup complete!"
echo "🔧 The arb command is now available globally"
echo "📝 Run 'source .venv/bin/activate' to activate the virtual environment for development"
