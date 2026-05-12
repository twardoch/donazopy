# Contributing

donazopy is a small, deliberately conservative codebase. Contributions are welcome — the bar is: real behavior, real tests, no secrets, no stubs that pretend to work.

## Development setup

```bash
git clone https://github.com/twardoch/donazopy.git
cd donazopy
uv sync          # creates .venv/ and installs locked deps
uv run donazopy version
```

Use `uv add <package>` for new runtime dependencies (never bare `pip`). Docs-only dependencies go in the `docs` dependency group (see [docs build](#building-the-docs)).

## Running the test suite

```bash
uvx hatch test                 # the canonical test command
# or:
uv run pytest -q
```

Tests must run **without network access** — provider tests use mocked HTTP. Any live integration test must be opt-in via an explicit environment variable and use disposable test zones; it must never run by default.

## Lint, format, and type-check

```bash
uvx ruff format .                                  # format
uvx ruff check . --fix                             # lint (E,W,F,I,B,C4,UP,SIM)
uvx mypy src tests                                 # strict typing
# Pyright is also configured (standard mode over src + tests).
python -m compileall src tests                     # quick smoke compile
```

`ruff` is configured with line length 120 (E501 ignored). `mypy` runs in `--strict` mode; tests relax `disallow_untyped_defs`.

## Code conventions

- **`this_file:` marker.** Every source file starts with a marker giving its path relative to the project root, no leading `./`:
- Python: `# this_file: src/donazopy/providers/cloudflare.py`
- Markdown: a YAML frontmatter `this_file:` key.
- YAML config: `# this_file: mkdocs/mkdocs.yml` Update it if you move the file.
- **Naming:** `snake_case` for modules/functions/variables, `PascalCase` for classes. Provider modules are named after the provider in lowercase (`cloudflare.py`, `google_cloud.py`).
- **Boundaries:** parse raw input into typed values at the edge (dataclasses, `dnspython` records); keep the interior typed. Raise typed exceptions (`TargetError`, `ZoneFileError`, `ProviderError` and friends) at the boundary.
- **Provider isolation:** all provider-specific logic lives in `src/donazopy/providers/<key>.py` plus the registry wiring. Nothing else should import provider internals.
- **No secrets, ever:** don't commit `.env`, `.pypirc`, tokens, or private research. Don't print credential values. Status output is redacted by design — keep it that way.
- **Keep it small:** Python 3.12+, type hints in their simplest form (`list`, `dict`, `|` unions), `pathlib`, concise functions, explicit failure handling. Prefer well-maintained packages over hand-rolled utilities.

## Test naming

Tests live under `tests/` mirroring `src/`:

- Files: `test_<module>.py` (e.g. `test_zonefile.py`).
- Functions: `test_<function>_when_<condition>_then_<result>`.

Cover the normal path **and** the edges: empty input, invalid DNS data, missing credentials, API errors, provider-specific quirks, and the safe-write "refuse to overwrite" behavior. Add helpful assertion messages.

## Adding a provider

See [Providers → Adding a new provider](https://github.com/twardoch/donazopy/providers/#adding-a-new-provider) for the full checklist. In short: read the official API docs, write a module with a `ProviderSpec`, implement an adapter satisfying `DNSHostingProvider` / `RegistrarProvider`, register it in `providers/registry.py`, add mocked HTTP tests — and only then is it "operational". Update `CHANGELOG.md` (move completed `TODO.md` items into it) once verified.

## Building the docs

The documentation site is built with `properdocs` (a thin MkDocs successor) and the `mkdocs-materialx` theme. Sources are in `src_docs/md/`, the config is `mkdocs/mkdocs.yml`, the compiled site is in `docs/`.

```bash
./docs.sh           # build into docs/
./docs.sh serve     # live preview at http://127.0.0.1:8000/
./docs.sh --help    # any other args pass straight through to the build tool
```

`docs.sh` runs the build via `uv run --group docs`, so the docs-only dependencies (declared in the `docs` group of `pyproject.toml`) are fetched on demand and don't affect a normal `uv sync`.

When you change a doc page, keep the `this_file:` frontmatter key correct and re-run `./docs.sh` to verify it still builds cleanly.

## Commits and pull requests

- Keep commits short and imperative: `Add Cloudflare zone export`, `Fix target parsing for absolute paths`.
- A PR should: describe the change; list the verification commands you ran (`uvx hatch test`, `uvx ruff check .`, `./docs.sh`, …); note any provider/API assumptions; and link the related issue or spec chapter.
- Include CLI output examples when behavior changes.
- Don't enable a provider's live-write support without official-docs confirmation and mocked tests.

## See also

- [Architecture](https://github.com/twardoch/donazopy/architecture/index.md) — package layout and conventions.
- [Providers](https://github.com/twardoch/donazopy/providers/index.md) — the provider model.
- [Zone files](https://github.com/twardoch/donazopy/zonefiles/index.md) — the local engine.
