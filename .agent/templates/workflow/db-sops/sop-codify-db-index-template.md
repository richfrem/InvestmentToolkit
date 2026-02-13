# SOP: Codify Database Index

**Source Workflow**: `/codify-db-index`
**Target**: `legacy-system/oracle-db-overviews/indexes/[IndexName]-Index-Overview.md`

## Phase 1: Analysis
- [ ] **Run Investigation**: `python tools/cli.py context --target [IndexName] --type index`
- [ ] **Verify Context**: Check `temp/context-bundles/[IndexName]_context.md`.

## Phase 2: Documentation
- [ ] **Initialize**: Copy `.agent/templates/outputs/db-index-template.md` to target path.
- [ ] **Fill Section**: **Purpose** (Performance)
- [ ] **Fill Section**: **Columns** (Indexed columns)
- [ ] **Fill Section**: **Type** (B-Tree, Bitmap, Unique)

## Phase 3: Intelligence Sync
- [ ] **Enrich Links**: `/curate-enrich-links [TargetFile]`
- [ ] **RLM Distill**: `/codify-rlm-distill [TargetFile]`
- [ ] **Vector Ingest**: `/codify-vector-ingest [TargetFile]`
- [ ] **Inventory Update**: `/curate-update-inventory`

## Phase 4: Closure
- [ ] **Retrospective**: `/workflow-retrospective`
- [ ] **End Workflow**: `/workflow-end`
