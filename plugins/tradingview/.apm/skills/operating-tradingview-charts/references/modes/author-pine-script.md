# Mode: author-pine-script (`/tv-author-pine-script`)

Master workflow for authoring, researching, and linting custom Pine Script v6 indicators. Trigger on /tv-author-pine-script or 'author pine script'.
Allowed tools: Bash, Read, Write.

Master workflow for authoring, researching, and linting custom Pine Script v6 indicators.


## Constraints

- Pine Script v6 only: All generated scripts must specify `//@version=6`.
- Mandatory lint gate: Must pass `scripts/pine_linter.py` before injection.
- No repainting: Forbidden to use lookahead on unconfirmed historical bars or future data leakage.
- Standalone self-contained code: Never import non-existent external libraries.

## Quick start

```bash
python3 scripts/pine_linter.py <script.pine>
```

## Workflow

1. Research existing indicator references in `plugins/tradingview/.apm/skills/operating-tradingview-charts/assets/pinescript-indicators/`.
2. Author indicator logic conforming strictly to Pine Script v6 syntax.
3. Run automated linter: `python3 scripts/pine_linter.py <file.pine>`.
4. Inject onto chart via [pine-inject mode](pine-inject.md)`.
5. Monitor Pine Editor console for compilation errors and self-heal if warnings occur.

## Verification

- Confirm `pine_linter.py` returns exit code 0.
- Confirm chart compiles without runtime errors in TradingView.
- Validate routing cases against `evals/evals.json`.

## References

- [Pine Script Overview](../pinescript_overview.md) - Pine Script architecture and indicators reference.
- [Pine Script Agent Skill Rules](../PineScript_Agent_Skill_Rules.md) - Rules and best practices for authoring Pine Script.
- [Top TradingView Indicators Reference](../Top_TradingView_Indicators_Reference.md) - Reference catalog of top TradingView community indicators.
