# avcmt-py - AI-Powered Semantic Release Style Git Commit Automation for Python Projects

[![PyPI version](https://img.shields.io/pypi/v/avcmt-py.svg)](https://pypi.org/project/avcmt-py/) [![Downloads](https://static.pepy.tech/badge/avcmt-py)](https://pepy.tech/project/avcmt-py) [![License](https://img.shields.io/github/license/andyvandaric/avcmt-py)](LICENSE) [![CI](https://github.com/andyvandaric/avcmt-py/actions/workflows/ci.yml/badge.svg)](https://github.com/andyvandaric/avcmt-py/actions/workflows/ci.yml) [![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://pre-commit.com/) [![Ruff](https://img.shields.io/badge/Ruff-%20-fastapi?style=for-the-badge&labelColor=202020&logo=ruff&logoColor=white)](https://docs.astral.sh/ruff/) [![PyPI](https://img.shields.io/badge/pypi-v0.11.13-orange?style=for-the-badge&logo=pypi&logoColor=white)](https://pypi.org/project/ruff/) [![License: MIT](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](https://opensource.org/licenses/MIT) [![Python Versions](https://img.shields.io/badge/%203.10%20|%203.11%20|%203.12%20|%203.13-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/) [![CI](https://img.shields.io/badge/main-passing-brightgreen?style=for-the-badge&logo=github)](https://github.com/andyvandaric/avcmt-py/actions)


Tired of manually crafting Git commit messages? Supercharge your Python development workflow with **[avcmt-py](https://github.com/andyvandaric/avcmt-py)**, the intelligent CLI tool that automates semantic, structured commit message generation using AI. Boost productivity and maintain a crystal-clear repository history effortlessly.

> **TL;DR:**
> AI-powered, semantic-release-style git commit automation for Python projects.
> One command, zero guesswork: meaningful, structured commits using your Pollinations AI API Token.
> Install, configure your API key, and enjoy never writing boring commit messages again!

---

## 🚀 What is avcmt-py?

**avcmt-py** is a blazing-fast, fully-automated CLI tool for generating *meaningful*, *structured* git commit messages using AI (Gemini, OpenAI, Pollinations, etc) — optimized for Python developers who want clean semantic-release workflow, better productivity, and crystal-clear repo history.

- **No more generic "fix bug", "update code" commits.**
- **Just run `avcmt` and get a ready-to-commit, semantic-release-formatted message,** automatically grouped by directory or file.
- **Integrates with pre-commit, CI/CD, and release workflows.**
- **Flexible AI provider: choose your favorite (support for Gemini, Pollinations, OpenAI out-of-the-box).**

---

## ✨ Features

- **AI-Powered Commit Messages:**
  Generate detailed, semantic-release-style commit messages from git diff with a single command.

- **Directory Grouping:**
  Automatically groups and commits related changes per directory (or as a catch-all).

- **Semantic Release Ready:**
  Commit format fully compatible with [semantic-release](https://semantic-release.gitbook.io/) for auto versioning & changelogs.

- **Multi-Provider AI:**
  Easily switch between Gemini, Pollinations, OpenAI (or extend to your own LLM API).

- **Zero Hardcoded Secrets:**
  API keys are loaded from `.env` or environment variables.

- **Easy to Install, Easy to Use:**
  Works on any Python project, no lock-in.

---

## 📦 Installation

```bash
pip install avcmt-py
```

Or install from source:

```bash
git clone https://github.com/andyvandaric/avcmt-py.git
cd avcmt-py
pip install .
```

## ⚡️ Quick Start (TL;DR)

1.  **Add your API key**

    -   Copy `.env.example` to `.env`

    -   Edit `.env` and fill your Pollinations or OpenAI API key

    ```env
    # Example (.env)
    POLLINATIONS_API_TOKEN=your-token-here
    ```

2.  **Stage your git changes:**

    ```
    git add .
    ```

3.  **Run avcmt:**

    ```bash
    avcmt           # AI generates & applies grouped commits!
    ```
    -   Optionally use:

        -   `--dry-run` (preview messages)

        -   `--push` (auto-push after commit)

        -   `--debug` (show AI prompts & raw response)

4.  **Done!**

    -   Check your git log for clean, structured, semantic-release-ready commit messages.

* * * *

## 🛠️ Usage

```bash
avcmt [OPTIONS]
```

-   `--dry-run` : Preview commit messages without applying

-   `--push` : Push commits to remote after done

-   `--debug` : Show debug info (prompts & AI response)

#### Example

```bash
avcmt --dry-run
avcmt --push
```

* * * *

## 🔒 Environment & Configuration

-   Place `.env` in your project root (or set env vars globally)

-   Supported ENV:

    -   `POLLINATIONS_API_TOKEN`

    -   (other providers: applied next update)

* * * *

## 📦 **Project Structure** (`avcmt-py/`)

```bash
avcmt-py/
│
├── avcmt/
│   ├── __init__.py
│   ├── cli.py
│   ├── commit.py
│   ├── ai.py
│   └── utils.py
│
├── README.md
├── LICENSE
├── .env.example
├── .gitignore
├── pyproject.toml
└── setup.cfg
```

### ✨ **File Descriptions**

-   `avcmt/cli.py` --- CLI entry point, handles argument parsing and triggers auto-commit.

-   `avcmt/commit.py` --- Core logic for grouping, git handling, and logging.

-   `avcmt/ai.py` --- Handles API requests to Pollinations (reads token from `.env`).

-   `avcmt/utils.py` --- Helper functions for logging, env handling, and file operations.

-   `.env.example` --- Environment file template. Don't forget to add your token in `.env`.

-   `pyproject.toml` --- Project metadata, scripts, and dependencies.

-   `README.md` --- Contains branding and usage instructions.

-   `LICENSE` --- MIT License.

-   `.gitignore` --- Ignores `.env`, `.pyc`, build files, etc.

## 🧩 Advanced

-   **Custom AI Providers:**
    See `avcmt/ai.py` to extend with your own LLM API.

-   **Integration with pre-commit:**
    Works out-of-the-box, can be called in hooks or CI.

-   **Full CLI options:**
    Run `avcmt --help` for all flags.

* * * *

## 📚 FAQ

**Q: Will this overwrite my changes or commit everything automatically?**
A: No, only staged files are affected. You're always in control.

**Q: Can I use it for monorepos?**
A: Yes, directory grouping is automatic, but fully configurable.

**Q: What if my provider's API token is missing or invalid?**
A: You'll see a clear error and nothing will be committed.

**Q: Is it safe for public/private repos?**
A: Yes, no token or diff is ever sent to any server except the AI you choose.

* * * *

## 🌟 Why avcmt-py?

-   ✨ *Stop wasting time on commit messages*

-   ✨ *Zero learning curve, drop-in to any Python repo*

-   ✨ *Works everywhere: CLI, hook, CI/CD, local/dev/remote*

-   ✨ *Your AI, your rules: bring your own API key, use any LLM*

* * * *

## 🔗 Links

-   [GitHub](https://github.com/andyvandaric/avcmt-py)

-   [PyPI](https://pypi.org/project/avcmt-py/)

* * * *

## 📝 License

[MIT](LICENSE) --- Made by [Andy Vandaric](https://github.com/andyvandaric)

* * * *

## 👏 Credits

-   Inspired by semantic-release, and real-life productivity pain points.

-   Powered by Pollinations AI.
# First semantic-release version
