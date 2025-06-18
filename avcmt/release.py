# File: avcmt/release.py
# Final Revision v5 - Adding pre-flight checks and enhanced changelog with commit links.

import os
import re
import subprocess
from collections import defaultdict
from datetime import datetime
from typing import Any

import toml

# Impor absolut dari dalam package Anda adalah best practice
from avcmt.utils import setup_logging

logger = setup_logging("log/semantic_release.log")


class ReleaseFailedError(Exception):
    """Custom exception for failures during the release process."""

    pass


class ReleaseManager:
    """
    Manages the entire semantic release process by orchestrating stateless git
    utilities and stateful versioning logic.
    """

    def __init__(self, config_path: str = "pyproject.toml"):
        """Initializes the manager by loading configuration."""
        self.config = ReleaseManager._load_config(config_path)
        self.old_version: str | None = None
        self.new_version: str | None = None
        self.commits: list[dict[str, str]] = []

    # --- Static Methods (Stateless Utilities) ---

    @staticmethod
    def _load_config(path: str) -> dict[str, Any]:
        """Loads release configuration from pyproject.toml."""
        try:
            pyproject = toml.load(path)
            config = pyproject.get("tool", {}).get("avcmt", {}).get("release", {})
            return {
                "version_path": config.get(
                    "version_path", "pyproject.toml:tool.poetry.version"
                ),
                "changelog_file": config.get("changelog_file", "CHANGELOG.md"),
                "branch": config.get("branch", "main"),
                "repo_url": config.get("repo_url"),  # URL for commit links
                "publish_to_pypi": config.get("publish_to_pypi", False),
            }
        except FileNotFoundError:
            raise ReleaseFailedError(f"Configuration file not found at: {path}")
        except Exception as e:
            raise ReleaseFailedError(f"Failed to parse configuration: {e}") from e

    @staticmethod
    def _run_command(command: list[str], sensitive_output: bool = False):
        """Helper to run any command and handle errors."""
        try:
            process = subprocess.run(
                command, check=True, capture_output=True, text=True, encoding="utf-8"
            )
            if not sensitive_output:
                logger.debug(f"Command stdout: {process.stdout.strip()}")
            return process.stdout.strip()
        except subprocess.CalledProcessError as e:
            error_message = f"Command '{' '.join(e.cmd)}' failed: {e.stderr.strip()}"
            logger.error(error_message)
            raise ReleaseFailedError(error_message) from e

    @staticmethod
    def _get_latest_tag() -> str:
        """Gets the latest git tag, defaulting to v0.0.0 if none exists."""
        try:
            return ReleaseManager._run_command(
                ["git", "describe", "--tags", "--abbrev=0"]
            )
        except ReleaseFailedError:
            logger.warning("No tag found. Defaulting to v0.0.0.")
            return "v0.0.0"

    @staticmethod
    def _get_commits_since_tag(tag: str) -> list[dict[str, str]]:
        """Gets all commit hashes and subjects since a given tag."""
        # Use a delimiter that is unlikely to be in a commit message
        delimiter = "|||---|||"
        output = ReleaseManager._run_command(
            ["git", "log", f"{tag}..HEAD", f"--pretty=%h{delimiter}%s"]
        )
        if not output:
            return []

        commits = []
        for line in output.split("\n"):
            if delimiter in line:
                hash_val, subject = line.split(delimiter, 1)
                commits.append({"hash": hash_val.strip(), "subject": subject.strip()})
        return commits

    @staticmethod
    def _push_changes():
        """Pushes commits and tags to the remote repository."""
        ReleaseManager._run_command(["git", "push"])
        ReleaseManager._run_command(["git", "push", "--tags"])
        logger.info("Successfully pushed commits and tags.")

    # --- Instance Methods (Stateful Workflow) ---

    def _pre_flight_checks(self):
        """Performs checks to ensure the repository is in a clean state for release."""
        logger.info("Performing pre-flight checks...")

        # 1. Check for uncommitted changes
        status_output = self._run_command(["git", "status", "--porcelain"])
        if status_output:
            raise ReleaseFailedError(
                "Uncommitted changes found in the working directory. "
                "Please commit or stash them before releasing."
            )

        # 2. Check if on the correct release branch
        current_branch = self._run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        if current_branch != self.config["branch"]:
            raise ReleaseFailedError(
                f"Not on the release branch '{self.config['branch']}'. "
                f"Currently on '{current_branch}'."
            )

        logger.info("Pre-flight checks passed successfully.")

    def _detect_bump(self) -> str | None:
        """Detects version bump type based on instance's commit messages."""
        bump_type: str | None = None
        for c in self.commits:
            subject = c["subject"]
            if "BREAKING CHANGE" in subject or re.search(r"\w+\(.*\)!:", subject):
                return "major"
            if subject.startswith("feat"):
                bump_type = "minor"
            elif subject.startswith("fix") and bump_type is None:
                bump_type = "patch"
        return bump_type

    def _bump_version(self, bump_type: str) -> str:
        """Bumps the version based on the old version stored in the instance."""
        major, minor, patch = map(int, self.old_version.strip("v").split("."))
        if bump_type == "major":
            major, minor, patch = major + 1, 0, 0
        elif bump_type == "minor":
            minor, patch = minor + 1, 0
        elif bump_type == "patch":
            patch += 1
        return f"v{major}.{minor}.{patch}"

    def _update_version_file(self):
        """Updates the version in the file specified in the instance's config."""
        path, key_path = self.config["version_path"].split(":", 1)
        keys = key_path.split(".")
        try:
            with open(path, "r+", encoding="utf-8") as f:
                data = toml.load(f)
                # Traverse to update the version
                temp_data = data
                for key in keys[:-1]:
                    temp_data = temp_data[key]
                temp_data[keys[-1]] = self.new_version.strip("v")

                # Write back to file
                f.seek(0)
                toml.dump(data, f)
                f.truncate()
            logger.info(f"Updated version in {path} to {self.new_version.strip('v')}")
        except (FileNotFoundError, KeyError, Exception) as e:
            raise ReleaseFailedError(
                f"Failed to update version file {path}: {e}"
            ) from e

    def _generate_formatted_changelog_section(self) -> str:
        """
        Parses conventional commits and generates a formatted changelog section with commit links.
        """
        grouped_commits = defaultdict(list)
        commit_pattern = re.compile(r"^(\w+)(?:\((.+)\))?!?: (.*)")
        repo_url = self.config.get("repo_url")

        for commit in self.commits:
            subject = commit["subject"]
            match = commit_pattern.match(subject)
            if match:
                commit_type = match.group(1)
                grouped_commits[commit_type].append(commit)
            else:
                grouped_commits["chore"].append(commit)

        section_headers = {
            "feat": "### Features",
            "fix": "### Bug Fixes",
            "perf": "### Performance Improvements",
            "refactor": "### Refactoring",
            "docs": "### Documentation",
            "style": "### Styles",
            "test": "### Tests",
            "build": "### Build System",
            "ci": "### Continuous Integration",
            "chore": "### Chores",
        }

        new_section_parts = []
        dt = datetime.now().strftime("%Y-%m-%d")
        new_section_parts.append(f"## {self.new_version} ({dt})\n")

        for type_key, header in section_headers.items():
            if commits_list := grouped_commits.get(type_key):
                new_section_parts.append(header)
                for c in commits_list:
                    commit_link = ""
                    if repo_url:
                        commit_link = (
                            f" ([`{c['hash']}`]({repo_url}/commit/{c['hash']}))"
                        )
                    new_section_parts.append(f"- {c['subject']}{commit_link}")
                new_section_parts.append("")

        return "\n".join(new_section_parts)

    def _update_changelog(self):
        """
        Updates the changelog file by inserting the new formatted section
        at the correct position using a precise split method.
        """
        path = self.config["changelog_file"]
        new_section = self._generate_formatted_changelog_section()
        marker = "<!-- version list -->"

        try:
            content = ""
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    content = f.read()
            else:
                logger.info(f"Changelog file not found at {path}. Creating a new one.")
                content = f"# CHANGELOG\n\n{marker}\n"

            if marker in content:
                parts = content.split(marker, 1)
                final_content = f"{parts[0]}{marker}\n\n{new_section}{parts[1]}"
            else:
                logger.warning(
                    f"Marker '{marker}' not found in {path}. Prepending content."
                )
                final_content = f"{new_section}\n{content}"

            with open(path, "w", encoding="utf-8") as f:
                f.write(final_content)
            logger.info(f"Updated {path} with version {self.new_version}")
        except Exception as e:
            raise ReleaseFailedError(f"Failed to write to changelog {path}: {e}") from e

    def _commit_and_tag(self):
        """Commits and tags the new version."""
        files_to_add = [
            self.config["version_path"].split(":")[0],
            self.config["changelog_file"],
        ]
        self._run_command(["git", "add", *files_to_add])
        self._run_command(
            ["git", "commit", "-m", f"chore(release): {self.new_version}"]
        )
        self._run_command(["git", "tag", self.new_version])
        logger.info(f"Successfully committed and tagged {self.new_version}.")

    @staticmethod
    def _publish_to_pypi():
        """Builds and publishes the package to PyPI."""
        logger.info("Starting PyPI publishing process...")
        pypi_token = os.getenv("PYPI_TOKEN")
        if not pypi_token:
            raise ReleaseFailedError("PYPI_TOKEN environment variable is not set.")

        logger.info("Building the package with 'poetry build'...")
        ReleaseManager._run_command(["poetry", "build"])

        logger.info("Publishing the package to PyPI...")
        ReleaseManager._run_command(
            ["poetry", "publish", "--username", "__token__", "--password", pypi_token],
            sensitive_output=True,
        )
        logger.info("Successfully published to PyPI.")

    def run(self, dry_run: bool = False, push: bool = False):
        """Main method to execute the entire release workflow."""
        logger.info("--- ReleaseManager: Starting Release Process ---")

        if not dry_run:
            self._pre_flight_checks()

        self.old_version = self._get_latest_tag()
        self.commits = self._get_commits_since_tag(self.old_version)

        if not self.commits:
            logger.info("No new commits found. Nothing to release.")
            return

        bump_type = self._detect_bump()
        if not bump_type:
            logger.info("No relevant semantic commits found. Nothing to release.")
            return

        self.new_version = self._bump_version(bump_type)

        if dry_run:
            logger.info("--- [DRY RUN MODE] ---")
            logger.info(f"Next version would be: {self.new_version}")
            logger.info(f"Commits found: {len(self.commits)}")
            logger.info("Changelog section that would be generated:")
            print(self._generate_formatted_changelog_section())
            logger.info("No files will be changed.")
            return

        # Live Run
        self._update_version_file()
        self._update_changelog()
        self._commit_and_tag()

        if push:
            self._push_changes()

        if self.config.get("publish_to_pypi", False):
            ReleaseManager._publish_to_pypi()

        logger.info(f"🚀 Release {self.new_version} completed successfully!")

        return self.new_version
