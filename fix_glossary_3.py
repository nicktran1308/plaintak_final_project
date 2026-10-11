#!/usr/bin/env python3
"""
Apply the second reviewer's decisions on the four flagged glossary entries.

Reviewed by a Vietnamese speaker who did not author the file, working from the
entries flagged HIGH and MEDIUM by an LLM pre-screen. Their judgement on
naturalness is authoritative here and overrides both the pre-screen's
recommendation and the original author's note where the two conflict.

B1  resume        "dùng lại" -> "uống lại"
B2  continue      keep "tiếp tục"; the author's own note is corrected
B3  hold          new sense for breath: "nín thở"
B4  mcg           block the μg and ug symbols
"""
import json
import shutil
from pathlib import Path

P = Path("backend/data/glossary_directive_DONE.jsonl")
shutil.copy(P, P.with_suffix(".jsonl.bak3"))
rows = json.loads(P.read_text(encoding="utf-8"))
REVIEWER = "second Vietnamese speaker (independent of the author)"
changed = []

HOLD_BREATH = {
    "sense_id": "hold.breath",
    "gloss": "to hold one's breath",
    "vi": "nín thở",
    "vi_alternatives": ["nhịn thở"],
    "context": {"rule": "requires", "require_any": ["breath", "breathe", "inhale", "exhale"]},
    "do_not_use": ["giữ hơi thở", "tạm ngưng", "ngưng"],
    "do_not_use_reason": (
        "'giữ hơi thở' is a literal calque and reads as stilted. 'nín thở' is "
        "the ordinary Vietnamese for holding one's breath."),
    "register": "plain",
    "regional_note": "Same in Northern and Southern usage.",
    "confidence": "high",
    "verified_by": REVIEWER,
    "reviewer_note": (
        "Added on second review. The physical sense 'giữ' is correct for "
        "objects such as crutches and gauze, but not for breath."),
}

for r in rows:
    # ---- B1: resume ----------------------------------------------------
    if r["en"] == "resume":
        s = r["senses"][0]
        old = s["vi"]
        s["vi"] = "uống lại"
        s["vi_alternatives"] = ["dùng lại", "bắt đầu dùng lại"]
        s["verified_by"] = REVIEWER
        s["reviewer_note"] = (
            "Second review changed 'dùng lại' to 'uống lại'. 'dùng lại' can be "
            "read as REUSING a physical item, such as an old syringe, rather "
            "than restarting a course of medication. 'uống lại' is tied to "
            "consumption and cannot carry that reading. The particle 'lại' "
            "still supplies the restart-after-interruption meaning that "
            "distinguishes resume from continue.")
        changed.append(f"resume: '{old}' -> 'uống lại'")

    # ---- B2: continue --------------------------------------------------
    if r["en"] == "continue":
        s = r["senses"][0]
        s["verified_by"] = REVIEWER
        s["reviewer_note"] = (
            "Second review CONFIRMED plain 'tiếp tục' and rejected the earlier "
            "suggestion of 'tiếp tục dùng'. Because the pipeline substitutes "
            "the term at the position the English word occupied, 'Continue "
            "atorvastatin 40 mg' yields 'tiếp tục atorvastatin 40 mg', which "
            "reads naturally and needs no added verb. This overrides the "
            "original author's note and an LLM pre-screen, both of which "
            "recommended adding 'dùng'.")
        changed.append("continue: kept 'tiếp tục', note corrected")

    # ---- B3: hold, breath sense ----------------------------------------
    if r["en"] == "hold":
        if not any(x["sense_id"] == "hold.breath" for x in r["senses"]):
            # Insert ahead of hold.physical, and stop that sense claiming breath.
            idx = next((i for i, x in enumerate(r["senses"])
                        if x["sense_id"] == "hold.physical"), len(r["senses"]))
            r["senses"].insert(idx, HOLD_BREATH)
            changed.append("hold: added hold.breath -> 'nín thở'")
        for x in r["senses"]:
            if x["sense_id"] == "hold.physical":
                req = x.get("context", {}).get("require_any", [])
                dropped = [w for w in req if "breath" in w]
                if dropped:
                    x["context"]["require_any"] = [w for w in req if "breath" not in w]
                    changed.append(f"hold.physical: removed {dropped} from require_any")

    # ---- B4: mcg symbols -----------------------------------------------
    if r["en"] == "mcg":
        s = r["senses"][0]
        dnu = s.setdefault("do_not_use", [])
        for sym in ("μg", "ug", "µg"):     # U+03BC and U+00B5 both occur
            if sym not in dnu:
                dnu.append(sym)
        s["do_not_use_reason"] = (
            (s.get("do_not_use_reason", "") + " ").strip() +
            " The symbols μg and ug are blocked so that the screen matches what "
            "is printed on the medication label: an older patient reading 'mcg' "
            "on the bottle may not recognise 'μg' as the same unit.")
        s["verified_by"] = REVIEWER
        changed.append("mcg: blocked μg, µg, ug")

P.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{len(changed)} changes, backup at {P.with_suffix('.jsonl.bak3').name}")
for c in changed:
    print("  " + c)

verified = sum(1 for r in rows for s in r["senses"] if s.get("verified_by"))
total = sum(len(r["senses"]) for r in rows)
print(f"\n{verified} of {total} senses carry verified_by")
print("The remaining senses were pre-screened as LOW priority and not")
print("individually examined by the second reviewer. Report that as such.")
