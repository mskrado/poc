#!/usr/bin/env bash
# Clean-machine proof: fresh copy, fresh venv, install, test, reproduce.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
WORK="$(mktemp -d /tmp/hh-clean-XXXXXX)"
cp -r "$SRC"/{src,tests,pyproject.toml,README.md,LICENSE} "$WORK"/
cd "$WORK"
echo "== host"; date; uname -srm; echo "nproc: $(nproc)"; free -h | awk '/Mem:/{print "RAM: "$2}'
grep -m1 "model name" /proc/cpuinfo || true
env -i PATH=/usr/bin:/bin HOME="$WORK" python3 -m venv --clear .venv
. .venv/bin/activate
echo "== python"; python --version; pip --version
pip install -q --no-cache-dir ".[test]"
echo "== installed"; pip freeze --all
echo "== pytest"; python -m pytest -q -p no:cacheprovider
echo "== reproduce"; holdout-harness run --seed 20261125 --out results
sha256sum results/results.csv
echo "== workdir $WORK"
