#!/usr/bin/env bash
set -euo pipefail

uvx hatch clean
uvx gitnextver
uvx hatch build
uv publish
