import json
import re
from pathlib import Path

DATED_RE = re.compile(r"^([A-Z0-9.\-]+)_\d{4}-\d{2}-\d{2}\.md$")


def migrate_pointers(projections_dir: str) -> dict:
    rewritten = 0
    for path in Path(projections_dir).glob("*.json"):
        versions = json.loads(path.read_text())
        changed = False
        for version in versions:
            ai_thesis = version.get("aiThesis")
            if not isinstance(ai_thesis, dict):
                continue
            report = ai_thesis.get("researchReport")
            if not report:
                continue
            match = DATED_RE.match(report)
            if not match:
                continue
            ai_thesis["researchReport"] = f"{match.group(1)}.summary.md"
            changed = True
            rewritten += 1
        if changed:
            tmp_path = path.with_suffix(".json.tmp")
            tmp_path.write_text(json.dumps(versions, indent=2))
            tmp_path.replace(path)
    return {"rewritten_count": rewritten}
