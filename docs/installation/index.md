# Installation

donazopy targets **Python 3.12+** and is packaged with [Hatch](https://hatch.pypa.io/) plus [`hatch-vcs`](https://github.com/ophidian-org/hatch-vcs) for git-tag-derived semantic versions. Day-to-day work uses [`uv`](https://docs.astral.sh/uv/).

## Requirements

- Python 3.12 or newer.
- `uv` (recommended) — installs and resolves dependencies from the lockfile.
- Git, if you build from a clone (the version is derived from git tags).

Runtime dependencies (declared in `pyproject.toml`):

| Package         | Why                                             |
| --------------- | ----------------------------------------------- |
| `dnspython`     | Parsing and serializing BIND zone files.        |
| `fire`          | Turning the `Donazopy` class into a CLI.        |
| `httpx`         | HTTP client for provider APIs (Cloudflare).     |
| `python-dotenv` | Loading provider credentials from `.env` files. |

## Install for development (from a clone)

```bash
git clone https://github.com/twardoch/donazopy.git
cd donazopy
uv sync
```

`uv sync` creates a virtual environment in `.venv/` and installs the locked dependencies. After that you can run the CLI through `uv`:

```bash
uv run donazopy version
```

Don't use bare `pip`

Use `uv add <package>` to add a dependency, or `uv sync` to install. Bare `pip install` bypasses the lockfile.

## Install as a tool

Once the package is published you can install the `donazopy` command globally with `uv`:

```bash
uv tool install donazopy
donazopy version
```

To install from a local checkout as a tool:

```bash
uv tool install --from . donazopy
```

## Verify the install

```bash
uv run donazopy version
# -> "1.0.2" (or whatever your git tag resolves to)

uv run donazopy providers
# -> ['cloudflare']
```

If `donazopy version` prints a version string and `donazopy providers` lists at least `cloudflare`, the install is good.

## Building the docs

The documentation site (this site) is built with [`properdocs`](https://pypi.org/project/properdocs/) (a thin successor to MkDocs) and the [`mkdocs-materialx`](https://pypi.org/project/mkdocs-materialx/) theme. Sources live in `src_docs/md/`, the MkDocs config is `mkdocs/mkdocs.yml`, and the compiled site lands in `docs/`.

```bash
./docs.sh          # build the site into docs/
./docs.sh serve    # live-preview at http://127.0.0.1:8000/
```

The docs dependencies are declared in a separate dependency group in `pyproject.toml`, so a normal `uv sync` for using donazopy does not pull them in; `./docs.sh` fetches them on demand via `uv run --group docs`.

See [Contributing](https://github.com/twardoch/donazopy/contributing/index.md) for the full development workflow.
