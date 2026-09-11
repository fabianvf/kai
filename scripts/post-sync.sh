#!/bin/bash
# Regenerate Hermeto-compatible requirements files for kai_mcp_solution_server.
#
# Invoked by dymurray/mta-sync after a successful merge from konveyor/kai so
# the hash-locked requirements.txt stays in step with upstream pyproject.toml
# changes (upstream commits an unhashed file; .gitattributes merge=ours keeps
# our copy on merge, and this script refreshes it). uv.lock is likewise kept via
# merge=ours and refreshed here. Also runs in CI via
# .github/workflows/verify-requirements-txt.yml as the drift detector.
#
# requirements-build-constraints.txt pins wheel-only build deps to a sdist-
# bearing version because pybuild-deps can't introspect wheels.
set -euo pipefail

cd "$(dirname "$0")/../kai_mcp_solution_server"

# Refresh the lockfile from the (post-merge) pyproject.toml so `uv sync` for devs
# stays consistent. requirements.txt/-build.txt are compiled from pyproject directly
# below and don't depend on this, but keeping uv.lock fresh avoids drift.
uv lock

uv pip compile --generate-hashes pyproject.toml -o requirements.txt

trap 'rm -f .build-input.tmp' EXIT
cat requirements.txt requirements-build-constraints.txt >.build-input.tmp
uvx --from pybuild-deps==0.5.0 pybuild-deps compile --generate-hashes \
	-o requirements-build.txt .build-input.tmp
