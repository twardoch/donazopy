#!/usr/bin/env bash
# this_file: docs.sh
#
# Build (or serve) the donazopy documentation site.
#
# Sources live in src_docs/md/, the MkDocs config is mkdocs/mkdocs.yml, and the
# compiled site lands in docs/. The docs-only dependencies are declared in the
# `docs` dependency group in pyproject.toml; `uv run --group docs` fetches them
# on demand without affecting a normal `uv sync`.
#
# Usage:
#   ./docs.sh            # build the site into docs/
#   ./docs.sh build      # same
#   ./docs.sh serve      # live preview at http://127.0.0.1:8000/
#   ./docs.sh <args...>  # any other args are passed straight to `mkdocs`

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

CONFIG="mkdocs/mkdocs.yml"

if [[ $# -eq 0 ]]; then
  set -- build
fi

case "$1" in
  build)
    shift
    exec uv run --group docs mkdocs build -f "${CONFIG}" "$@"
    ;;
  serve)
    shift
    exec uv run --group docs mkdocs serve -f "${CONFIG}" "$@"
    ;;
  *)
    exec uv run --group docs mkdocs "$@" -f "${CONFIG}"
    ;;
esac
