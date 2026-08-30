"""Tests for git integration."""

import subprocess
from pathlib import Path

import pytest

from polydiff.core.git_integration import (
    DRIVER_MAPPING,
    get_git_root,
    install_polydiff,
    parse_diff_driver_args,
    setup_git_config,
    write_gitattributes,
)


@pytest.fixture
def tmp_repo(tmp_path):
    """Create a temporary git repository."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    return repo_dir


class TestGitIntegration:
    def test_get_git_root(self, tmp_repo):
        """Test finding git root."""
        # Create a subdirectory
        subdir = tmp_repo / "subdir"
        subdir.mkdir()

        # Should find repo root from subdirectory
        root = get_git_root(subdir)
        assert root == tmp_repo

    def test_get_git_root_not_in_repo(self, tmp_path):
        """Test that get_git_root returns None outside a repo."""
        root = get_git_root(tmp_path)
        assert root is None

    def test_write_gitattributes(self, tmp_repo):
        """Test writing .gitattributes entries."""
        added = write_gitattributes(tmp_repo)

        # Should have added entries
        assert len(added) > 0

        # Check file was created
        gitattributes = tmp_repo / ".gitattributes"
        assert gitattributes.exists()

        content = gitattributes.read_text()
        assert "polydiff-image" in content
        assert "polydiff-pdf" in content
        assert "polydiff-xlsx" in content

    def test_write_gitattributes_no_duplicates(self, tmp_repo):
        """Test that duplicate entries are not added."""
        write_gitattributes(tmp_repo)
        added_again = write_gitattributes(tmp_repo)

        # Should not add duplicates
        assert len(added_again) == 0

    def test_write_gitattributes_specific_extensions(self, tmp_repo):
        """Test writing only specific extensions."""
        added = write_gitattributes(tmp_repo, extensions=[".png", ".pdf"])

        assert len(added) == 2
        assert any(".png" in line for line in added)
        assert any(".pdf" in line for line in added)

    def test_write_gitattributes_dry_run(self, tmp_repo):
        """Test dry run mode."""
        added = write_gitattributes(tmp_repo, dry_run=True)

        # Should return what would be added
        assert len(added) > 0

        # File should not exist
        gitattributes = tmp_repo / ".gitattributes"
        assert not gitattributes.exists()

    def test_setup_git_config_local(self, tmp_repo):
        """Test local git config setup."""
        commands = setup_git_config(scope="local", repo_root=tmp_repo)

        # Should have executed commands
        assert len(commands) > 0

        # Verify config was set
        result = subprocess.run(
            ["git", "config", "--local", "diff.polydiff-image.command"],
            cwd=tmp_repo,
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "polydiff diff-driver"

    def test_setup_git_config_dry_run(self, tmp_repo):
        """Test dry run mode for git config."""
        commands = setup_git_config(scope="local", repo_root=tmp_repo, dry_run=True)

        # Should return commands that would be run
        assert len(commands) > 0

        # Config should not be set
        result = subprocess.run(
            ["git", "config", "--local", "diff.polydiff-image.command"],
            cwd=tmp_repo,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0  # Config should not exist

    def test_parse_diff_driver_args(self):
        """Test parsing git diff driver arguments."""
        args = [
            "image.png",  # path
            "/tmp/old.png",  # old-file
            "abc123",  # old-hex
            "100644",  # old-mode
            "/tmp/new.png",  # new-file
            "def456",  # new-hex
            "100644",  # new-mode
        ]

        old_file, new_file = parse_diff_driver_args(args)

        assert old_file == Path("/tmp/old.png")
        assert new_file == Path("/tmp/new.png")

    def test_parse_diff_driver_args_too_few(self):
        """Test that too few arguments raises error."""
        with pytest.raises(ValueError, match="Expected at least 7"):
            parse_diff_driver_args(["a", "b", "c"])

    def test_install_polydiff(self, tmp_repo):
        """Test full installation."""
        result = install_polydiff(scope="local", repo_root=tmp_repo)

        assert result["repo_root"] == str(tmp_repo)
        assert result["scope"] == "local"
        assert len(result["gitattributes_added"]) > 0
        assert len(result["config_commands"]) > 0

        # Verify .gitattributes was created
        gitattributes = tmp_repo / ".gitattributes"
        assert gitattributes.exists()

        # Verify git config was set
        for driver in set(DRIVER_MAPPING.values()):
            result = subprocess.run(
                ["git", "config", "--local", f"diff.{driver}.command"],
                cwd=tmp_repo,
                capture_output=True,
                text=True,
            )
            assert result.stdout.strip() == "polydiff diff-driver"

    def test_driver_mapping_coverage(self):
        """Test that all expected extensions are covered."""
        expected_extensions = [
            ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif",
            ".pdf",
            ".xlsx", ".xlsm",
        ]

        for ext in expected_extensions:
            assert ext in DRIVER_MAPPING, f"Extension {ext} not in DRIVER_MAPPING"
