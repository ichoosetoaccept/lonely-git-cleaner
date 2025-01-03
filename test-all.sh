#!/bin/bash

# Function to run macOS tests
run_macos_tests() {
    echo "Running tests on macOS (native)..."
    uv run pytest -v -s
}

# Function to run Linux tests
run_linux_tests() {
    echo -e "\nBuilding Linux test container..."
    docker build -t arborist-test -f Dockerfile.test .

    echo -e "\nRunning tests on Linux (Docker)..."
    docker run --rm arborist-test
}

# Check command line arguments
case "${1:-all}" in
    "macos")
        run_macos_tests
        ;;
    "linux")
        run_linux_tests
        ;;
    "all")
        run_macos_tests
        run_linux_tests
        ;;
    *)
        echo "Usage: $0 [platform]"
        echo "Platforms: macos, linux, all (default)"
        exit 1
        ;;
esac
