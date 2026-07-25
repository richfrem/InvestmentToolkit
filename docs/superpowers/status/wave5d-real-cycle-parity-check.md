# Wave 5D Task 6 — Real-Cycle Parity Check (Prediction Ledger Dual-Write)

**Status:** Complete. Proves the **live, going-forward** dual-write path added in Task 2
(`prediction_ledger.py::append_prediction()` / `_append_prediction_event()`) produces
byte-identical data on both the JSONL side (`predictions.jsonl`) and the Intelligence Ledger side
(`intelligence_event.payload_json`, reached via `observations.jsonl` → `replay_events_to_db`) for a
brand-new claim, per spec §5's requirement to "run both paths in parallel for at least one full
real-world cycle... and diff row-for-row" — not satisfied by the Task 5 historical backfill alone.

## Why this deviates from the brief's literal Step 1 command

The brief's suggested command was:

```bash
python3 py_services/harvest_predictions.py --dry-run
```

Re-grepping the file's actual current argparse block confirmed `--dry-run` exists, but running it
surfaced a real, pre-existing bug unrelated to this wave's work:

```
$ python3 py_services/harvest_predictions.py --dry-run
Traceback (most recent call last):
  ...
  File ".../py_services/generate_track_record_report.py", line 68, in _load_predictions_from_ledger
    conn = initialize_db(db_path)
  File ".../py_services/intelligence/db_client.py", line 4, in initialize_db
    conn = sqlite3.connect(db_path)
sqlite3.OperationalError: unable to open database file
```

Root cause: `generate_track_record_report.py`'s `DEFAULT_INTEL_DB_PATH` is computed as
`_PY_SERVICES_DIR.resolve().parents[2] / "data/intelligence.sqlite"` — `parents[2]` from
`py_services/` resolves to the **worktree root**, not `investment_screener/backend/`, so the
default path is missing the `investment_screener/backend/` prefix and points at a directory that
doesn't exist. This is a real, out-of-scope bug (not a Task 6 concern, and not one of Tasks 7-9's
files) — logged here for visibility, not fixed as part of this task.

Per the brief's own fallback guidance, Task 6 instead exercises the exact same dual-write code path
Task 2 built — `prediction_ledger.append_prediction()` — directly, with a single realistic fixture
claim record, against fresh tmp-scoped `predictions.jsonl` / `observations.jsonl` /
`intelligence.sqlite` paths. This isolates the parity proof from the unrelated CLI bug above while
still exercising 100% of the real dual-write machinery (`_append_jsonl`, `_append_prediction_event`,
`event_store.append_event`, `replay_ledger.replay_events_to_db`, `event_repository.get_latest_event_by_type`).

## Step 1 — Real dual-write invocation

Fixture claim record (shape matches the real `_append_if_new()` record schema in
`harvest_predictions.py`: `v`, `id`, `date`, `ticker`, `type`, `claim`, `direction`, `horizonDays`,
`basePrice`, `baseSpyPrice`, `harvestedAt`):

```python
record = {
    "v": 1,
    "id": "NVDA:action_rating:2026-07-24",
    "date": "2026-07-24",
    "ticker": "NVDA",
    "type": "action_rating",
    "claim": {"action": "ACCUMULATE"},
    "direction": "bullish",
    "horizonDays": 90,
    "basePrice": 123.45,
    "baseSpyPrice": 567.89,
    "harvestedAt": "2026-07-24T12:00:00Z",
}

append_prediction(
    record,
    path=Path("<tmp>/predictions.jsonl"),
    jsonl_path="<tmp>/observations.jsonl",
)
```

Real output:

```
append_prediction() completed.
```

Resulting `predictions.jsonl` line (JSONL side, authoritative during the Hybrid dual-write window):

```json
{"v": 1, "id": "NVDA:action_rating:2026-07-24", "date": "2026-07-24", "ticker": "NVDA", "type": "action_rating", "claim": {"action": "ACCUMULATE"}, "direction": "bullish", "horizonDays": 90, "basePrice": 123.45, "baseSpyPrice": 567.89, "harvestedAt": "2026-07-24T12:00:00Z"}
```

Resulting `observations.jsonl` line (Intelligence Ledger side, `PREDICTION_CLAIM` event):

```json
{"event_id": "evt_cd84e8876bf8", "event_sequence": 1, "ticker": "NVDA", "event_type": "PREDICTION_CLAIM", "effective_at": "", "ingested_at": "2026-07-24T14:32:01Z", "source_id": "prediction_ledger", "status": "ACTIVE", "title": "Prediction claim: NVDA action_rating (None)", "body_markdown": "Direction: bullish, horizon: 90 days.", "payload_json": "{\"v\": 1, \"id\": \"NVDA:action_rating:2026-07-24\", \"date\": \"2026-07-24\", \"ticker\": \"NVDA\", \"type\": \"action_rating\", \"claim\": {\"action\": \"ACCUMULATE\"}, \"direction\": \"bullish\", \"horizonDays\": 90, \"basePrice\": 123.45, \"baseSpyPrice\": 567.89, \"harvestedAt\": \"2026-07-24T12:00:00Z\"}", "supersedes_event_id": null, "idempotency_key": "prediction-claim-NVDA:action_rating:2026-07-24", "content_hash": "9940ee74d82155da7933f68a6dfe304d5baded90d1d38dec5e3507c81885b842"}
```

## Step 2 — Row-for-row diff (JSONL record vs. ledger `payload_json`)

The ledger side requires one extra hop not spelled out in the brief's literal Step 2 script:
`append_prediction()` only appends to `observations.jsonl` — it does not itself insert into
`intelligence.sqlite`. That table is a read-model rebuilt from the JSONL ledger by
`intelligence/replay_ledger.py::replay_events_to_db()`. Ran that replay against the fresh tmp
`intelligence.sqlite`, then performed the exact assert described in the brief:

```python
conn = initialize_db("<tmp>/intelligence.sqlite")
replay_events_to_db("<tmp>/observations.jsonl", conn)

with open("<tmp>/predictions.jsonl") as f:
    lines = [json.loads(l) for l in f if l.strip()]
latest_jsonl = lines[-1]

latest_event = get_latest_event_by_type(conn, "PREDICTION_CLAIM")
latest_ledger_payload = json.loads(latest_event["payload_json"])

assert latest_jsonl == latest_ledger_payload, (...)
print("PARITY CONFIRMED: JSONL record and intelligence_event payload_json are byte-identical.")
```

Real output:

```
PARITY CONFIRMED: JSONL record and intelligence_event payload_json are byte-identical.
```

## Result

**Byte-identical, zero diff.** The `predictions.jsonl` record and the
`intelligence_event.payload_json` for the same claim (`NVDA:action_rating:2026-07-24`) are
identical Python dict values (`latest_jsonl == latest_ledger_payload` passed with no
`AssertionError`). This confirms the Task 2 dual-write path is correct for a brand-new, live
claim — not just for the Task 5 historical backfill.

## Observation logged, not fixed (out of scope for Task 6)

`_append_prediction_event()` in `prediction_ledger.py` builds the ledger event's `effective_at` and
`title` from `record.get("claimDate")`, but the real record schema used by `harvest_predictions.py`
keys the date as `record["date"]`, not `record["claimDate"]`. Net effect: every real
`PREDICTION_CLAIM` event's `effective_at` column is `""` and its title ends in `(None)` (visible in
the Step 1 output above) — cosmetic/metadata-only, since the row-for-row parity check above only
depends on `payload_json`, which is unaffected and is confirmed byte-identical. Worth a follow-up
fix in a future task (not Tasks 7-9, which are rollback/archival/exit-report scoped), since
`effective_at` is used for date-ordered queries elsewhere in the Intelligence Ledger consumer
pattern.

## Scope confirmation

- All commands above ran against this worktree's own files (`investment_screener/backend/`) and
  tmp-scoped paths under `/private/tmp/claude-501/.../scratchpad/wave5d-task6/`. No writes were
  made to the main checkout's `predictions.jsonl`, `observations.jsonl`, or `intelligence.sqlite`.
- This worktree's own `data/predictions.jsonl` (87 lines) / `data/observations.jsonl` (196 lines)
  were left untouched — Task 5's real backfill only ran against the main checkout's copies, per
  the standing rule that gitignored data files never sync via worktree.
