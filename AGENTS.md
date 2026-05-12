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

The package scaffold is not present yet. Once added, prefer `uv` and Hatch-based workflows:

- `uv sync` installs project dependencies from the lockfile.
- `uvx hatch test` runs the test suite.
- `./build.sh` should clean and build distributions with `uvx hatch clean` and `uvx hatch build`.
- `./publish.sh` should clean, update the git-tag-based version, build, then publish with `uv publish`.

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
