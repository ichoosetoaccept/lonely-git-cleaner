"""Test CLI error handling."""

from arborist.cli import app
from typer.testing import CliRunner


# def test_clean_command_git_error(temp_repo):
#     """Test clean command with Git errors."""
#     runner = CliRunner()

#     # Create an unmerged branch
#     unmerged = temp_repo.create_head("unmerged")
#     unmerged.checkout()

#     # Create some changes
#     with open(temp_repo.working_dir + "/unmerged.txt", "w") as f:
#         f.write("unmerged")
#     temp_repo.index.add(["unmerged.txt"])
#     temp_repo.index.commit("Unmerged commit")

#     # Create additional uncommitted changes
#     with open(temp_repo.working_dir + "/uncommitted.txt", "w") as f:
#         f.write("uncommitted")

#     # Switch back to main
#     temp_repo.heads["main"].checkout()

#     # Try to delete the unmerged branch with force
#     result = runner.invoke(
#         app,
#         ["clean", "--path", temp_repo.working_dir, "--protect", "main", "--force", "--no-interactive"]
#     )
#     assert "failed to delete" in result.stdout.lower()
#     assert result.exit_code == 1


def test_list_command_invalid_repo():
    """Test list command with invalid repository path."""
    runner = CliRunner()

    # Try to list branches in a non-existent repository
    result = runner.invoke(app, ["list", "--path", "/nonexistent/path"])
    assert "not a git repository" in result.stdout.lower()
    assert result.exit_code == 1


# def test_clean_command_with_invalid_config(temp_repo):
#     """Test clean command with invalid configuration."""
#     runner = CliRunner()

#     # Create a branch that matches the invalid pattern
#     invalid = temp_repo.create_head("invalid/branch")
#     invalid.checkout()

#     # Create some changes and commit
#     with open(temp_repo.working_dir + "/invalid.txt", "w") as f:
#         f.write("invalid")
#     temp_repo.index.add(["invalid.txt"])
#     temp_repo.index.commit("Invalid commit")

#     # Switch back to main and merge the branch
#     temp_repo.heads["main"].checkout()
#     temp_repo.git.merge("invalid/branch", "--no-ff")

#     # Try to delete the branch with an invalid protect pattern
#     result = runner.invoke(
#         app,
#         ["clean", "--path", temp_repo.working_dir, "--protect", "[", "--no-interactive"]
#     )
#     assert "invalid pattern" in result.stdout.lower()
#     assert result.exit_code == 1
