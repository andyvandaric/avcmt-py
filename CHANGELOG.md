# CHANGELOG

<!-- version list -->

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
