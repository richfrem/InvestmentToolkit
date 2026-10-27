# Wave 2 summary: toolkit-manager (3 skills -> 1 hub)

| Check | Result |
|---|---|
| Ledger accounting (`rewrite_references.py verify --wave 2`) | 34 rows, 0 failures; 15 path-expression warnings reviewed (`parents[1]` relative to the hub; audit scripts scanning `plugins/` by design) |
| Knowledge parity | 55 of 62 substantive lines verbatim; 7 deliberate edits (backup path, "run-screener" -> run-app mode) |
| Evals | 21 of 21 carried over, tagged with `mode` |
| `validate_apm_package.py` / `audit_skill.py` | passed / PASS |
| Real `apm install` into a throwaway project | deployed; 12 relative links resolve |
| Regression vs baseline | every suite identical (backend Python 1771, TypeScript 237/2, toolkit-manager 74 passed + the same 2 expected failures) |

Notes
- The audit scripts enumerate files with `rglob`/`grep -r`, which include dot-directories, so code under `.apm/` is still scanned (checked, because ripgrep-style tools would skip it).
- `extract_ecosystem_yaml.py` has no argument parser, so `--help` ran it and wrote a stray summary file into `.apm/`; removed.
