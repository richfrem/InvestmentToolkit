#!/bin/zsh
# Records the pre-migration test baseline. Output: docs/plans/apm-migration/baseline/<suite>.txt
cd "$(git rev-parse --show-toplevel)"
export PYTHONDONTWRITEBYTECODE=1
PY=python3
OUT=docs/plans/apm-migration/baseline
run() { name=$1; shift; echo "== $name" > $OUT/$name.txt; ( "$@" ) >> $OUT/$name.txt 2>&1; echo "exit=$?" >> $OUT/$name.txt; }
run backend-py   $PY -m pytest investment_screener/backend/tests/py_services -q -p no:cacheprovider
for p in portfolio-advisor stock-valuation tradingview toolkit-manager; do
  run plugin-$p  $PY -m pytest plugins/$p/tests -q -p no:cacheprovider
done
run plugin-questrade     $PY -m pytest plugins/questrade/tests -q -p no:cacheprovider
run plugin-etf-analysis  $PY -m pytest plugins/etf-analysis/.apm/skills -q -p no:cacheprovider
run backend-ts   sh -c 'cd investment_screener/backend && npm test --silent'
echo done > $OUT/DONE
