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

# Resolve for the Linux/Python target the image is built for, not the host that
# runs this script. Without --python-platform/--python-version, uv resolves for
# the current machine, so a macOS dev drops Linux-only deps (e.g. greenlet) and
# the hash-locked file drifts from what CI (Linux) regenerates.
uv pip compile --generate-hashes \
	--python-platform x86_64-unknown-linux-gnu --python-version 3.12 \
	--constraint requirements-constraints.txt \
	pyproject.toml -o requirements.txt

# !!! TEMPORARY -- REMOVE ASAP (together with the fastmcp<2.13 pin in
# requirements-constraints.txt) !!!
# That pin keeps the deps source-buildable but holds fastmcp/mcp at versions
# osv-scanner flags for known CVEs. Suppress those advisories on this generated
# manifest until the Hermeto Rust build is fixed and fastmcp is unpinned. We are
# knowingly shipping CVEs until both are removed -- prioritize the fix.
{
	echo '# trunk-ignore-all(osv-scanner)'
	cat requirements.txt
} >requirements.txt.tmp
mv requirements.txt.tmp requirements.txt

trap 'rm -f .build-input.tmp' EXIT
cat requirements.txt requirements-build-constraints.txt >.build-input.tmp
# pybuild-deps 0.5.0 creates ~/.cache/pybuild-deps with mkdir(exist_ok=True) but
# not parents=True, so it crashes on a fresh runner where ~/.cache is absent.
mkdir -p "${XDG_CACHE_HOME:-${HOME}/.cache}"
uvx --from pybuild-deps==0.5.0 pybuild-deps compile --generate-hashes \
	-o requirements-build.txt .build-input.tmp
