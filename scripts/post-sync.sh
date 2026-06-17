#!/bin/bash
# Regenerate Hermeto-compatible requirements files for kai_mcp_solution_server.
#
# Invoked by dymurray/mta-sync after a successful merge from konveyor/kai so
# the hash-locked requirements.txt stays in step with upstream pyproject.toml
# changes (upstream commits an unhashed file; .gitattributes merge=ours keeps
# our copy on merge, and this script refreshes it). Also runs in CI via
# .github/workflows/verify-requirements-txt.yml as the drift detector.
#
# requirements-build-constraints.txt pins wheel-only build deps to a sdist-
# bearing version because pybuild-deps can't introspect wheels.
#
# requirements-constraints.txt caps upstream runtime deps that resolve to
# versions which can't be built from source in Hermeto (e.g. fastmcp 2.13+
# pulling the Rust-backed uv_build via py-key-value-aio).
set -euo pipefail

cd "$(dirname "$0")/../kai_mcp_solution_server"

uv pip compile --generate-hashes --constraint requirements-constraints.txt \
    pyproject.toml -o requirements.txt

trap 'rm -f .build-input.tmp' EXIT
cat requirements.txt requirements-build-constraints.txt > .build-input.tmp
uvx --from pybuild-deps==0.5.0 pybuild-deps compile --generate-hashes \
    -o requirements-build.txt .build-input.tmp
