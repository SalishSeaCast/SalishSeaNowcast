# AGENTS Instructions

## Project & Environment Overview
- **Package Manager:** This project strictly uses [Pixi](https://pixi.sh) for environment, dependency, and task management.
- **Python Version:** Managed via Pixi's `pyproject.toml` / `pixi.lock`.

## Execution Rules (Crucial)
1. **Never use raw global tools:** Do NOT execute direct `pip install`, `python`, `pytest`, or `conda` commands.
2. **Always use Pixi:**
   - Run Python scripts: `pixi run python <script.py>`
   - Add new dependencies: `pixi add <package_name>`
   - Add dev dependencies: `pixi add --feature dev <package_name>`
   - Execute project tasks: `pixi run <task_name>`
   - Run tests: `pixi run -e dev pytest` — extra arguments can be appended (e.g. a specific test name or directory).

## Directory Layout
- `nowcast/`: Core application source code.
- `config/`: Configuration files and settings.
- `docs/`: Sphinx documentation.
- `tests/`: Pytest suite.
- `notebooks/`: Jupyter notebooks for analysis and visualization, organized by purpose (`comparison/`, `publish/`, `research/`).
- `release_mgmt/`: Release management scripts and configuration.
- `sarracenia/`: Sarracenia file transfer and MQTT synchronization configuration.
- `htmlcov/`: Generated HTML test coverage reports (excluded from git).
- `.pixi/`: Local Pixi environments (excluded from git and indexing).
- `pyproject.toml`: Canonical source of truth for dependencies and project tasks.

## Code Style
- **Formatter:** Code is formatted with [black](https://black.readthedocs.io/), enforced via [pre-commit](https://pre-commit.com/) hooks.
- Ensure any code changes conform to black formatting before committing.

## Git Commits
- **Only commit when explicitly asked** by the user — do not commit automatically.
- **Commit message format:**
  - Start with a short imperative sentence (≤50 characters, no period).
  - Leave a blank line.
  - Follow with a detailed explanation of 2–3 sentences maximum.
  - Avoid overly verbose descriptions or unnecessary details.

## Safety & Constraints
- **Lockfile Integrity:** Do not edit `pixi.lock` manually. If `pyproject.toml` changes, run `pixi install` to re-sync.
- **Environment Isolation:** Do not suggest creating global virtual environments (`venv` or `virtualenv`) or standard Conda environments.
