#!/bin/zsh
# Re-runs every baseline suite after a wave. Usage: run_wave_tests.sh <wave-number>
# Output: docs/plans/apm-migration/waves/wave-<n>/<suite>.txt  (compare with baseline/)
cd "$(git rev-parse --show-toplevel)"
export PYTHONDONTWRITEBYTECODE=1
OUT=docs/plans/apm-migration/waves/wave-$1; mkdir -p $OUT; rm -f $OUT/DONE
run() { name=$1; shift; echo "== $name" > $OUT/$name.txt; ( "$@" ) >> $OUT/$name.txt 2>&1; echo "exit=$?" >> $OUT/$name.txt; }
run backend-py   python3 -m pytest investment_screener/backend/tests/py_services -q -p no:cacheprovider
for p in portfolio-advisor stock-valuation tradingview toolkit-manager questrade etf-analysis; do
  # pytest skips dot-directories, so tests under .apm/ must be passed explicitly
  extra=$(find plugins/$p/.apm -type d -name tests 2>/dev/null | tr '\n' ' ')
  run plugin-$p  python3 -m pytest $( [ -d plugins/$p/tests ] && echo plugins/$p/tests ) ${=extra} -q -p no:cacheprovider
done
run backend-ts   sh -c 'cd investment_screener/backend && npm test --silent'
echo done > $OUT/DONE
