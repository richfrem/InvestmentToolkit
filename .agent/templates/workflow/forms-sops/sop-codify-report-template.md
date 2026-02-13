# SOP: Codify Report (RDF)

**Source Workflow**: `/codify-report`
**Target**: `legacy-system/oracle-reports-overviews/[ReportName]-Report-Overview.md`

## Phase 1: Analysis
- [ ] **Run Investigation**: `python tools/cli.py context --target [ReportName] --type report`
- [ ] **Verify Context**: Check `temp/context-bundles/[ReportName]_context.md` for queries.

## Phase 2: Documentation
- [ ] **Initialize**: Copy `.agent/templates/outputs/report-overview-template.md` (or generic) to target path.
- [ ] **Fill Section**: **Purpose** (Output description)
- [ ] **Fill Section**: **Queries** (SQL extraction)
- [ ] **Fill Section**: **Parameters** (User inputs)
- [ ] **Fill Section**: **Layout** (Groups/Frames)

## Phase 3: Intelligence Sync
- [ ] **Enrich Links**: `/curate-enrich-links [TargetFile]`
- [ ] **RLM Distill**: `/codify-rlm-distill [TargetFile]`
- [ ] **Vector Ingest**: `/codify-vector-ingest [TargetFile]`
- [ ] **Inventory Update**: `/curate-update-inventory`

## Phase 4: Closure
- [ ] **Retrospective**: `/workflow-retrospective`
- [ ] **End Workflow**: `/workflow-end`
