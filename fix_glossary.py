#!/usr/bin/env python3
"""Relax context rules on unambiguous glossary terms and add hold.physical."""
import json, pathlib, shutil

p = pathlib.Path("backend/data/glossary_directive_DONE.jsonl")
shutil.copy(p, p.with_suffix(".jsonl.bak"))
rows = json.loads(p.read_text(encoding="utf-8"))

# Terms whose Vietnamese would be WRONG outside medication context.
KEEP_REQUIRES = {"hold", "resume", "do not resume", "tablet"}

HOLD_PHYSICAL = {
    "sense_id": "hold.physical",
    "gloss": "to grasp, support, or keep in position, physically",
    "vi": "giữ",
    "vi_alternatives": ["cầm", "giữ chặt"],
    "context": {"rule": "requires", "require_any": [
        "crutch", "crutches", "cane", "walker", "railing", "breath",
        "position", "arm", "leg", "hand", "wound", "bandage", "gauze",
        "pressure", "ice", "compress", "inhaler", "still"]},
    "do_not_use": ["tạm ngưng", "ngưng"],
    "do_not_use_reason": "ngưng means to stop; in a physical context this would tell the patient to stop rather than to grip.",
    "register": "plain",
    "confidence": "high",
    "reviewer_note": "All 75 corpus occurrences of 'hold' are physical manipulation, consistently giữ. Deliberately NOT a default sense, so an undetected drug name blocks rather than silently resolving to giữ.",
}

changed = []
for r in rows:
    if r["en"] == "hold" and not any(s["sense_id"] == "hold.physical" for s in r["senses"]):
        r["senses"].append(HOLD_PHYSICAL)
        changed.append("hold: added hold.physical")
    if r["en"] in KEEP_REQUIRES:
        continue
    for s in r["senses"]:
        ctx = s.setdefault("context", {})
        if ctx.get("rule") == "requires":
            ctx["_was_requires"] = ctx.get("require_any", [])
            ctx["rule"] = "default"
            ctx.pop("require_any", None)
            changed.append(f"{r['en']}: requires -> default")

p.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{len(changed)} changes written to {p}")
for c in changed:
    print("  ", c)
    