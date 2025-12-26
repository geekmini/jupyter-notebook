---
description: Initialize the project with all required tools and dependencies
---

Setup the project by performing the following steps:

1. **Install required tools**: Run `brew install python@3.12 uv just` to install Python, uv (package manager), and just (command runner). If any are already installed, brew will skip them.

2. **Install OrbStack**: Check if OrbStack is installed (`orbctl version`). If not, run `brew install --cask orbstack` and inform the user they need to start OrbStack manually after installation.

3. **Create .env file**: Copy `.env.example` to `.env` if `.env` doesn't already exist. If `.env` already exists, skip this step and inform the user.

4. **Install dependencies**: Run `just sync` to install all project dependencies via uv.

5. **Setup git hooks**: Run `just setup-hooks` to configure pre-commit hooks.

After completing these steps, summarize what was done and remind the user to:
- Start OrbStack if it was just installed
- Update `.env` with their actual API keys if they just created it from the example
