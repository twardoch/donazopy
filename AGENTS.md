# Repository Guidelines
<!-- this_file: AGENTS.md -->

## Project Structure & Module Organization

This repository currently contains the early project definition for `donazopy`, a Python CLI tool for DNS and domain-provider management. Public project notes live in `README.md` and `IDEA.md`; private research material belongs under `private/` and is ignored by git.

Expected implementation layout should keep provider integrations isolated:

- `src/donazopy/` for application code.
- `src/donazopy/providers/` for one module per DNS/domain provider, for example `cloudflare.py` or `namecheap.py`.
- `tests/` for unit and integration tests mirroring `src/`.
- `spec/` for design specifications when generated from the planning notes.

## Build, Test, and Development Commands

The package lives under `src/donazopy/`. Prefer `uv` and Hatch-based workflows:

- `uv sync` installs runtime + `dev` dependencies (ruff, mypy, pytest) from the lockfile.
- `uv run pytest tests/` runs the test suite (all provider calls are mocked — no network).
- `uv run ruff check . && uv run ruff format --check .` lints and checks formatting.
- `uv run mypy src/donazopy` type-checks under `--strict`.
- `./docs.sh build` compiles `src_docs/md/` into `docs/` via MkDocs + MaterialX.
- `./build.sh` cleans and builds distributions with `uvx hatch clean` and `uvx hatch build`.
- `./publish.sh` cleans, derives the git-tag version, builds, then publishes with `uv publish`.

CI (`.github/workflows/ci.yml`) runs lint, format, mypy, and tests on Ubuntu and macOS
across Python 3.12 and 3.13; `release.yml` publishes to PyPI on a `v*` tag.

Do not use bare `pip`; use `uv add <package>` for dependencies.

## Coding Style & Naming Conventions

Target Python 3.12+. Use type hints, `pathlib`, dataclasses or Pydantic at I/O boundaries, and concise functions with explicit failure handling. Format with Ruff once configured. Use `snake_case` for modules, functions, and variables; `PascalCase` for classes; and provider modules named after providers in lowercase.

Every source file should include a `this_file` marker near the top, for example:

```python
# this_file: src/donazopy/providers/cloudflare.py
```

## Testing Guidelines

Write tests before implementation where practical. Use `pytest` via Hatch, with test files named `test_<module>.py` and test functions named `test_<function>_when_<condition>_then_<result>`. Cover normal paths, empty input, invalid DNS data, missing credentials, API errors, and provider-specific edge cases.

## Commit & Pull Request Guidelines

Git history is minimal (`Initial commit`, `v1.0.0`), so keep future commits short and imperative, for example `Add Cloudflare provider scaffold`. Pull requests should describe the change, list verification commands run, note provider/API assumptions, and link related issues or spec sections. Include CLI output examples when behavior changes.

## Security & Configuration Tips

Never commit credentials, `.env`, `.pypirc`, provider tokens, or private research. Keep secrets in local environment variables or ignored config files. DNS-provider API behavior must be checked against official documentation before implementation.
