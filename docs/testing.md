# Testing

This project uses pytest for testing. The tests are organized into unit tests and integration tests.

## Running Tests

To run the tests:

```bash
uv run pytest -v                  # Run tests with verbose output
uv run pytest -v -s              # Run tests with verbose output and print statements
uv run pytest -v --cov           # Run tests with coverage report
```

## Test Organization

The tests are organized into the following categories:

### Unit Tests
- `tests/test_git.py`: Tests for individual git operations and utilities
- Located in the `tests/` directory
- Focus on testing individual functions and classes in isolation
- Use fixtures to set up test environments

### Integration Tests
- `tests/test_git_integration.py`: Tests for CLI operations and end-to-end workflows
- Test multiple components working together
- Use the CLI runner to test command-line interface
- Verify complete workflows like branch cleanup

## Test Environment

Tests use the `GitHubTestEnvironment` class from `tests/git_test_env.py` to create isolated git repositories for testing. This ensures tests don't interfere with each other or with the actual git repository.

The test environment:
- Creates temporary directories for test repositories
- Sets up a bare origin repository and a working clone
- Provides utility methods for creating branches, commits, etc.
- Cleans up temporary directories after tests complete

## Cross-Platform Testing

The project includes a Docker setup for testing on Linux while developing on macOS:

```bash
./test-all.sh  # Runs tests on both macOS and Linux (via Docker)
```

This ensures compatibility across different platforms.

## Writing Tests

When writing new tests:

1. Use the `git_env` fixture to get a clean test environment
2. Follow the existing test patterns for consistency
3. Add docstrings to test functions explaining what they test
4. Use descriptive test names that indicate the functionality being tested
5. Clean up any resources created during tests

Example test:
```python
def test_feature(git_env):
    """Test description of what this test verifies."""
    # Setup
    git_env.create_branch("feature", "test commit")

    # Exercise
    result = some_operation()

    # Verify
    assert result == expected
```

## Coverage Requirements

The project requires a minimum of 85% test coverage. Run tests with coverage reporting to ensure adequate coverage:

```bash
uv run pytest -v --cov
```
