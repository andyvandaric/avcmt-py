# CHANGELOG

<!-- avcmt-release-marker -->

## v1.6.0 (2025-06-20)

### 🚀 Features
- **feat(avcmt modules):** enhance commit handling with remote sync awareness and smarter state checks ([`9a88061`](https://github.com/andyvandaric/avcmt-py/commit/9a88061))
- **feat(avcmt):** improve logging setup with handler clearing and detailed formatter ([`e7d4dd2`](https://github.com/andyvandaric/avcmt-py/commit/e7d4dd2))

### 🐛 Bug Fixes
- **fix(commit):** fix staging logic for multi-group commits ([`351c65b`](https://github.com/andyvandaric/avcmt-py/commit/351c65b))

### 🧹 Chores
- **chore(avcmt/modules):** refactor commit generation process for better readability and robustness ([`4aede0d`](https://github.com/andyvandaric/avcmt-py/commit/4aede0d))
- **chore(avcmt/cli):** add comment line to commit.py file ([`ad804ba`](https://github.com/andyvandaric/avcmt-py/commit/ad804ba))

### 📦 Others
- **other:** Merge pull request #6 from andyvandaric/fix/commit-group-staging ([`f8ba6d6`](https://github.com/andyvandaric/avcmt-py/commit/f8ba6d6))
## v1.5.1 (2025-06-19)

### 🐛 Bug Fixes
- **fix(release_manager):** improve version file and changelog handling with validation and backward compatibility ([`a9fcadd`](https://github.com/andyvandaric/avcmt-py/commit/a9fcadd))
- **fix(avcmt):** remove redundant render_prompt function and centralize Jinja2 environment setup ([`e896361`](https://github.com/andyvandaric/avcmt-py/commit/e896361))

### 🧹 Chores
- **chore(avcmt/modules):** fix changelog update to handle empty marker correctly ([`e8d280d`](https://github.com/andyvandaric/avcmt-py/commit/e8d280d))

### 📦 Others
- **other:** Merge pull request #5 from andyvandaric/fix/release_manager ([`fff2cc9`](https://github.com/andyvandaric/avcmt-py/commit/fff2cc9))
- **other:** Merge pull request #4 from andyvandaric/feature/changelog ([`88b079f`](https://github.com/andyvandaric/avcmt-py/commit/88b079f))
## v1.5.0 (2025-06-19)

### Features
- feat(avcmt/modules): improve changed files detection to include deleted files and handle removals correctly ([`90bd4c5`](https://github.com/andyvandaric/avcmt-py/commit/90bd4c5))

### Chores
- Merge branch 'main' of https://github.com/andyvandaric/avcmt-py ([`e2c742d`](https://github.com/andyvandaric/avcmt-py/commit/e2c742d))
- chore: unused script ([`a5de3bf`](https://github.com/andyvandaric/avcmt-py/commit/a5de3bf))
- Merge branch 'main' of https://github.com/andyvandaric/avcmt-py ([`c58c560`](https://github.com/andyvandaric/avcmt-py/commit/c58c560))
- chore: unused script ([`7931c7d`](https://github.com/andyvandaric/avcmt-py/commit/7931c7d))


## v1.4.1 (2025-06-19)

### Bug Fixes
- fix(cli): simplify version output in release process ([`216f28c`](https://github.com/andyvandaric/avcmt-py/commit/216f28c))


## v1.4.0 (2025-06-19)

### Features
- feat(cli): introduce 'release' command with 'run' sub-command for project release management ([`16da695`](https://github.com/andyvandaric/avcmt-py/commit/16da695))
- feat(cli): add release sub-command with semantic release functionality ([`67e1a6a`](https://github.com/andyvandaric/avcmt-py/commit/67e1a6a))
- feat(avcmt): add utilities for git staging and dry-run cache management ([`9a7995f`](https://github.com/andyvandaric/avcmt-py/commit/9a7995f))
- feat(cli): organize commit subcommands and utilities ([`c1cd8fe`](https://github.com/andyvandaric/avcmt-py/commit/c1cd8fe))
- feat(cli): add 'commit' sub-command for semantic commit messaging in avcmt ([`6182779`](https://github.com/andyvandaric/avcmt-py/commit/6182779))
- feat(cli): implement unified CLI with Typer (#1) ([`ae1ce82`](https://github.com/andyvandaric/avcmt-py/commit/ae1ce82))

### Refactoring
- refactor(modules): improve file existence check in commit_generator ([`a497e82`](https://github.com/andyvandaric/avcmt-py/commit/a497e82))

### Chores
- chore(release): update release command in workflows ([`f394c0e`](https://github.com/andyvandaric/avcmt-py/commit/f394c0e))
- Merge pull request #3 from andyvandaric/refactor/migrate-release ([`7a84d12`](https://github.com/andyvandaric/avcmt-py/commit/7a84d12))
- Merge pull request #2 from andyvandaric/refactor/refactor/migrate-commit ([`a8bb8b8`](https://github.com/andyvandaric/avcmt-py/commit/a8bb8b8))


## v1.3.0 (2025-06-19)

### Features
- feat(scripts): migrate to pathlib for file and directory operations ([`1ba7b5c`](https://github.com/andyvandaric/avcmt-py/commit/1ba7b5c))

### Bug Fixes
- fix: Bump urllib3 to version 2.5.0 and update associated lockfile hashes ([`6cca949`](https://github.com/andyvandaric/avcmt-py/commit/6cca949))
- fix(avcmt): replace os.path with pathlib for path handling and improve file operations ([`7e1ba25`](https://github.com/andyvandaric/avcmt-py/commit/7e1ba25))

### Chores
- Merge branch 'fix/linter-path-errors' ([`812039e`](https://github.com/andyvandaric/avcmt-py/commit/812039e))
- chore(avcmt): improve logging messages in commit workflow ([`8d30dce`](https://github.com/andyvandaric/avcmt-py/commit/8d30dce))
- chore(avcmt): improve logging messages in commit workflow ([`2e4d2a6`](https://github.com/andyvandaric/avcmt-py/commit/2e4d2a6))
- chore(avcmt): improve push process and add user guidance ([`8ccbbae`](https://github.com/andyvandaric/avcmt-py/commit/8ccbbae))


## v1.2.0 (2025-06-19)

### Features
- feat(scripts): migrate project license to Apache 2.0 ([`52c5858`](https://github.com/andyvandaric/avcmt-py/commit/52c5858))

### Bug Fixes
- fix!: add licensing headers to provider modules and init file ([`eca9ab3`](https://github.com/andyvandaric/avcmt-py/commit/eca9ab3))

### Refactoring
- refactor(root): update LICENSE to Apache License 2.0 and add NOTICE file ([`ba9079e`](https://github.com/andyvandaric/avcmt-py/commit/ba9079e))

### Chores
- Merge branch 'chore/test-apache-license-migration' ([`32cc7d0`](https://github.com/andyvandaric/avcmt-py/commit/32cc7d0))
- chore(avcmt): add licensing headers to source files ([`e38174f`](https://github.com/andyvandaric/avcmt-py/commit/e38174f))


## v1.1.1 (2025-06-19)

### Bug Fixes
- fix(docs): update project description and shields in README.md ([`14c211d`](https://github.com/andyvandaric/avcmt-py/commit/14c211d))


## v1.1.0 (2025-06-18)

### Features
- feat(avcmt): refine commit management, enhance dry-run and code cleanup ([`8c1c0d4`](https://github.com/andyvandaric/avcmt-py/commit/8c1c0d4))
- feat(avcmt/providers): update OpenAI provider to use modern v1.x API ([`d997ca9`](https://github.com/andyvandaric/avcmt-py/commit/d997ca9))
- feat(root): add initial project setup with dependency lock and configuration ([`cafa9d5`](https://github.com/andyvandaric/avcmt-py/commit/cafa9d5))

### Bug Fixes
- fix(workflows): correct indentation and add step id for release workflow ([`86b7fa7`](https://github.com/andyvandaric/avcmt-py/commit/86b7fa7))
- fix(scripts): improve semrel.py robustness and usability ([`6281633`](https://github.com/andyvandaric/avcmt-py/commit/6281633))
- fix: update license text and improve README formatting for catch-all scope ([`3293386`](https://github.com/andyvandaric/avcmt-py/commit/3293386))
- fix(catch-all): update GitHub workflows for improved pre-commit and release operations ([`211073b`](https://github.com/andyvandaric/avcmt-py/commit/211073b))

### Refactoring
- refactor(avcmt): overhaul commit and release workflows for clarity and robustness ([`0cfcb56`](https://github.com/andyvandaric/avcmt-py/commit/0cfcb56))

### Chores
- chore(scripts): improve release version output and error handling ([`3ed56a1`](https://github.com/andyvandaric/avcmt-py/commit/3ed56a1))
- Revert "chore(release): v1.1.0" ([`de0aca5`](https://github.com/andyvandaric/avcmt-py/commit/de0aca5))
- chore(release): v1.1.0 ([`ba897d1`](https://github.com/andyvandaric/avcmt-py/commit/ba897d1))
- chore(.github/workflows): update release workflow with git configuration and internal release step ([`c3444e3`](https://github.com/andyvandaric/avcmt-py/commit/c3444e3))
- chore(root): update dependencies in pyproject.toml ([`32de1fc`](https://github.com/andyvandaric/avcmt-py/commit/32de1fc))
- chore(root): migrate project to version 1.0.0 and update project metadata ([`1f47ae5`](https://github.com/andyvandaric/avcmt-py/commit/1f47ae5))
- chore(.github/workflows): update release workflow to include PYPI_TOKEN for publishing ([`e7c6cd6`](https://github.com/andyvandaric/avcmt-py/commit/e7c6cd6))
- chore(root): update changelog and remove redundant release entries ([`1ca2d04`](https://github.com/andyvandaric/avcmt-py/commit/1ca2d04))


## v1.0.0 (2025-06-16)

### Bug Fixes

- **catch-all**: Add semantic release helper script for versioning and publishing
  ([`860e144`](https://github.com/andyvandaric/avcmt-py/commit/860e14466eeb7de4f1bbfd2be8e86ffad580c9a4))

- **root**: Add semrel script entry point
  ([`3312c9f`](https://github.com/andyvandaric/avcmt-py/commit/3312c9faf4b0607c731f7f446521b03a1dc742b8))

### Chores

- **catch-all**: Add GitHub Actions workflow for semantic release on tags
  ([`2e6315b`](https://github.com/andyvandaric/avcmt-py/commit/2e6315bf2aed0fafc308289562614a6c7b1c4c57))

- **root**: Update README and configuration for improved clarity and usability
  ([`956a706`](https://github.com/andyvandaric/avcmt-py/commit/956a706d864f8b83107764d5787894efac1119f1))

### Features

- **.github/workflows**: Update CI workflow to support semantic release and refine setup
  ([`fe64dc0`](https://github.com/andyvandaric/avcmt-py/commit/fe64dc0522f5d2dbdb26fa4f8aeab1e6d13a5a88))

- **avcmt**: Enhance commit grouping and AI prompt rendering
  ([`9346ad8`](https://github.com/andyvandaric/avcmt-py/commit/9346ad8fce60763681f0384e16d0fa2aa7666584))

- **avcmt**: Enhance commit grouping and AI prompt rendering
  ([`be6ca70`](https://github.com/andyvandaric/avcmt-py/commit/be6ca706bef6eecd1250fef7bf9db8d429b1b467))

### Refactoring

- **providers**: Improve request handling and error resilience in OpenAI and Pollinations providers
  ([`ca9cb81`](https://github.com/andyvandaric/avcmt-py/commit/ca9cb8144ca025f6bd84288d36b3f3bda8416d56))

- **scripts**: Integrate logging into all scripts for better traceability
  ([`78dd841`](https://github.com/andyvandaric/avcmt-py/commit/78dd841bd448d42cf5bcf0dd2ac41fb86c457de6))
