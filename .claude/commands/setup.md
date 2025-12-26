---
description: Initialize the project with all required tools and dependencies
---

Setup the project by performing the following steps. For each tool, check if it exists first before installing.

1. **Install Homebrew**: Check if Homebrew is installed (`command -v brew`). If not, install it using `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`.

2. **Install Python**: Check if Python 3.12+ is installed (`python3 --version`). If not or version is too old, run `brew install python@3.12`.

3. **Install uv**: Check if uv is installed (`command -v uv`). If not, run `brew install uv`.

4. **Install just**: Check if just is installed (`command -v just`). If not, run `brew install just`.

5. **Install OrbStack**: Check if OrbStack is installed (`command -v orbctl`). If not, run `brew install --cask orbstack` and inform the user they need to start OrbStack manually after installation.

6. **Create .env file**: Check if `.env` exists. If not, copy `.env.example` to `.env`.

7. **Install dependencies**: Run `just sync` to install all project dependencies via uv.

8. **Setup git hooks**: Run `just setup-hooks` to configure pre-commit hooks.

After completing these steps, summarize what was done and remind the user to:
- Start OrbStack if it was just installed
- Update `.env` with their actual API keys if they just created it from the example
