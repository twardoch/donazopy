#!/usr/bin/env bash
set -euo pipefail

uvx hatch clean
uvx hatch build
