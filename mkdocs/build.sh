#!/usr/bin/env bash
# this_file: mkdocs/build.sh
# Build the adjacent site; remaining arguments are forwarded to the renderer.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"

if [[ "${1:-}" == build ]]; then shift; fi
exec uvx --python 3.12 --from properdocs==1.6.7 \
  --with mkdocs==1.6.1 \
  --with mkdocs-materialx \
  --with mkdocs-include-markdown-plugin \
  --with mkdocs-llmstxt \
  --with pymdown-extensions \
  properdocs build --config-file mkdocs.yml "$@"
