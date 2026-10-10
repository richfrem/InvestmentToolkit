# Keeping thesis pages current

Every thesis page in the web app opens with a **Current developments** note: the most relevant recent news and analysis for the stocks that thesis covers. The note lives in `domain_model.sqlite` (`thesis_document_currency`, one row per page, no history) and is written with `plugins/portfolio-advisor/scripts/thesis_currency.py`. The events it is built from live in the intelligence ledger (`NEWS_SWEEP`, `RESEARCH_IMPORT`, `THESIS_UPDATE`). A page the skills do not touch goes stale, so the daily, weekly and review skills each refresh the pages they affect.

## Commands
```bash
# 1. Record what a news sweep found (once per model; see the news-sweep skill)
python3 plugins/portfolio-advisor/scripts/record_news_sweep.py --source grok --write < findings.md

# 2. Which pages need a refresh, and why
python3 plugins/portfolio-advisor/scripts/thesis_currency.py stale --max-age-days 7

# 3. For each page: the stocks it covers, its current note, and the recent events
python3 plugins/portfolio-advisor/scripts/thesis_currency.py context --document asi_race

# 4. Replace the note (stdin), or re-date it when nothing material changed
python3 plugins/portfolio-advisor/scripts/thesis_currency.py put --document asi_race --by daily-loop < note.md
python3 plugins/portfolio-advisor/scripts/thesis_currency.py touch --document asi_race --by weekly-review

# New or reshaped thesis: say which stocks it covers
python3 plugins/portfolio-advisor/scripts/thesis_currency.py set-members --document robotics_automation --tickers HUMN,KOID
```

## Findings format for `record_news_sweep.py`
Markdown from stdin, one section per stock after you have triangulated the models and passed the fact-check gate. Use `## MACRO` for market-wide items. Anything else is ignored.
```markdown
## NVDA
- Board added $150B to the buyback authorization (2026-10-04).
## MACRO
- 10Y 4.1%, VIX 14.9.
```
Re-running the same sweep changes nothing; a changed finding replaces the earlier one.

## Writing the note
- Only what the context shows. Never invent; mark anything unconfirmed `(unverified)`.
- 4 to 8 bullets, at most 2,400 characters. Most decision-relevant first.
- Each bullet: what happened (dated), why it matters to **this** thesis (confirms, challenges or neutral), with the ticker in bold.
- Keep an item only while it still matters: drop news older than about three weeks unless it still drives the view. This is a current picture, not a log: no "updated", "previously" or change history.
- No weights, actions or fair values: the table below the note shows those live, from the same source as every other page.
- If the context shows no events and the old note is still right, use `touch` instead of rewriting it.

## Who refreshes what
| Skill | When | What |
| --- | --- | --- |
| `news-sweep` | after recording the sweep | pages whose stocks appear in the findings |
| `daily-loop` | each session | pages `stale` lists with new events |
| `weekly-review` | each week | every page `stale` lists (`touch` the ones that did not change) |
| `strategic-review` | after the review | every page; also check the page's own prose against the review |
| `thesis-review` / `thesis-review-agent` | new or changed thesis | `set-members`, then the first note |

`verify_refresh.py` warns when a page's note is more than 14 days old or has newer events.
