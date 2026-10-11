#!/usr/bin/env python3
"""
Tests for translate.py.

No API key required: the model is a stub with controllable failure modes.
The fixture glossary mirrors the real glossary_directive_DONE.jsonl schema,
including a multi-sense `hold` entry.

Central assertions:
  - entities are claimed BEFORE glossary terms, so "500 mg" is never split
  - detected entities establish medication context without enumerating drugs
  - `hold` resolves by sense, and blocks when no sense fits
  - critical content never enters the prompt
  - a model that drops a placeholder is caught

Run:  python backend/tests/test_translate.py
"""

import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from pipeline.translate import (Term, build_context, load_glossary, protect,
                                restore, select_sense, translate)

NER = False  # regex core only, so the suite runs without scispaCy

# --------------------------------------------------------------------------
# Fixture glossary. Same shape as glossary_directive_DONE.jsonl.
# --------------------------------------------------------------------------
GLOSSARY_JSON = [
    {
        "en": "hold",
        "safety_critical": True,
        "senses": [
            {
                "sense_id": "hold.medication",
                "gloss": "to stop taking a medication temporarily",
                "vi": "tạm ngưng",
                "vi_alternatives": ["tạm ngưng dùng", "tạm ngưng uống"],
                "context": {
                    "rule": "requires",
                    "require_any": ["medicine", "medication", "dose", "pill",
                                    "tablet", "capsule", "insulin"],
                },
                "do_not_use": ["giữ", "cầm"],
                "do_not_use_reason": "giữ means to physically keep or grip",
                "confidence": "high",
            },
            {
                "sense_id": "hold.physical",
                "gloss": "to grasp, support or keep in position",
                "vi": "giữ",
                "context": {
                    "rule": "requires",
                    "require_any": ["crutch", "crutches", "cane", "walker",
                                    "breath", "wound", "pressure", "position",
                                    "arm", "leg", "hand", "still"],
                },
                "do_not_use": ["tạm ngưng", "ngưng"],
                "do_not_use_reason": "ngưng means to stop, not to grip",
                "confidence": "high",
            },
        ],
    },
    {
        "en": "do not",
        "safety_critical": True,
        "senses": [{"sense_id": "donot.imperative", "vi": "không",
                    "context": {"rule": "default"}, "confidence": "high"}],
    },
    {
        "en": "do not resume",
        "safety_critical": True,
        "senses": [{"sense_id": "donotresume.1", "vi": "không dùng lại",
                    "context": {"rule": "default"}, "confidence": "high"}],
    },
    {
        "en": "twice daily",
        "safety_critical": True,
        "senses": [{"sense_id": "bid.1", "vi": "hai lần mỗi ngày",
                    "context": {"rule": "requires",
                                "require_any": ["medicine", "medication",
                                                "dose", "take"]}}],
    },
    {
        "en": "until",
        "safety_critical": True,
        "senses": [{"sense_id": "until.1", "vi": "cho đến khi",
                    "context": {"rule": "requires",
                                "require_any": ["medicine", "medication", "dose"]}}],
    },
    {
        "en": "mg",
        "safety_critical": True,
        "senses": [{"sense_id": "unit_mg.1", "vi": "mg",
                    "context": {"rule": "default"}}],
    },
]

SRC_MED = "Hold metformin 500 mg twice daily until you follow up on 11/14."
SRC_PHYS = "Hold both crutches on your injured side."
SRC_AMBIG = "Hold the container upright."   # neither sense fits -> must block


class StubModel:
    """Echoes placeholders back. `mode` selects the failure to simulate."""

    def __init__(self, mode="good"):
        self.mode = mode
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if prompt.startswith("Translate this Vietnamese"):
            return prompt.split("VIETNAMESE:")[-1].split("ENGLISH:")[0].strip()
        src = prompt.split("ENGLISH:")[-1].split("VIETNAMESE:")[0].strip()
        if self.mode == "drop_placeholder":
            import re
            return re.sub(r"⟦1⟧\s*", "", src)
        if self.mode == "ignore_placeholders":
            return "giữ metformin cho đến ngày mai."
        return src


def gloss() -> dict[str, Term]:
    f = pathlib.Path(tempfile.mkdtemp()) / "glossary.jsonl"
    f.write_text(json.dumps(GLOSSARY_JSON, ensure_ascii=False), encoding="utf-8")
    return load_glossary(f)


def main() -> int:
    fails = 0
    G = gloss()

    def check(name, cond, detail=""):
        nonlocal fails
        fails += not cond
        print(f"[{'ok ' if cond else 'FAIL'}] {name}")
        if detail and not cond:
            print(f"         {detail}")

    # ----------------------------------------------------------------------
    print("=" * 72)
    print("GLOSSARY LOADING")
    print("=" * 72)
    check("loads 6 terms", len(G) == 6, f"got {len(G)}")
    check("hold carries 2 senses", len(G["hold"].senses) == 2,
          f"got {len(G['hold'].senses)}")
    check("safety_critical preserved", G["hold"].safety_critical)

    # ----------------------------------------------------------------------
    print()
    print("=" * 72)
    print("CONTEXT AUGMENTATION")
    print("=" * 72)
    ctx = build_context(SRC_MED, use_ner=NER)
    tokens = ctx.split("\u2063")[-1]
    print(f"       tokens from entities: {tokens.strip()}")
    check("dose entity yields medication context", "dose" in tokens)
    check("frequency entity detected", "frequency" in tokens)
    check("physical sentence yields no medication context",
          "\u2063" not in build_context(SRC_PHYS, use_ner=NER))

    # ----------------------------------------------------------------------
    print()
    print("=" * 72)
    print("SENSE SELECTION")
    print("=" * 72)
    s = select_sense(G["hold"], build_context(SRC_MED, use_ner=NER))
    check("medication context -> tạm ngưng",
          s and s.sense_id == "hold.medication" and s.vi == "tạm ngưng",
          f"got {s.sense_id if s else None}")

    s = select_sense(G["hold"], build_context(SRC_PHYS, use_ner=NER))
    check("crutches context -> giữ",
          s and s.sense_id == "hold.physical" and s.vi == "giữ",
          f"got {s.sense_id if s else None}")

    s = select_sense(G["hold"], build_context(SRC_AMBIG, use_ner=NER))
    check("no matching sense returns None (must block, not guess)",
          s is None, f"got {s.sense_id if s else None}")

    # ----------------------------------------------------------------------
    print()
    print("=" * 72)
    print("PROTECTION ORDERING  (entities before glossary)")
    print("=" * 72)
    p = protect(SRC_MED, G, use_ner=NER)
    print(f"       protected: {p.text}")
    for x in p.substitutions:
        print(f"         {x}")
    check("'500 mg' claimed whole, not split by the 'mg' entry",
          any("500 mg -> 500 mg" in x for x in p.substitutions),
          "; ".join(p.substitutions))
    check("dose absent from prompt text", "500 mg" not in p.text)
    check("date absent from prompt text", "11/14" not in p.text)
    check("hold absent from prompt text", "hold" not in p.text.lower())
    check("nothing unresolved", not p.unresolved, str(p.unresolved))

    restored, missing = restore(p.text, p.restore_vi)
    check("restore is lossless",
          not missing and "500 mg" in restored and "tạm ngưng" in restored, restored)

    # longest match wins
    p2 = protect("Do not resume driving for two weeks.", G, use_ner=NER)
    check("'do not resume' beats 'do not'",
          any("do not resume" in x.lower() for x in p2.substitutions),
          "; ".join(p2.substitutions))

    # ambiguous hold must block
    p3 = protect(SRC_AMBIG, G, use_ner=NER)
    check("ambiguous 'hold' lands in unresolved",
          p3.unresolved == ["Hold"], str(p3.unresolved))

    # ----------------------------------------------------------------------
    print()
    print("=" * 72)
    print("TRANSLATION PIPELINE")
    print("=" * 72)
    m = StubModel("good")
    r = translate(SRC_MED, m, G, back_translate=True, use_ner=NER)
    check("medication sentence passes", r.passed, "; ".join(r.reasons))
    print(f"       output: {r.output_vi}")
    check("model never saw '500 mg'", "500 mg" not in m.prompts[0])
    check("model never saw '11/14'", "11/14" not in m.prompts[0])

    m = StubModel("good")
    r = translate(SRC_PHYS, m, G, back_translate=True, use_ner=NER)
    check("physical sentence passes with giữ",
          r.passed and "giữ" in (r.output_vi or ""), "; ".join(r.reasons))
    print(f"       output: {r.output_vi}")

    m = StubModel("good")
    r = translate(SRC_AMBIG, m, G, back_translate=False, use_ner=NER)
    check("ambiguous sentence is refused, model never called",
          not r.passed and len(m.prompts) == 0, "; ".join(r.reasons))
    if not r.passed:
        print(f"       reason: {r.reasons[0]}")

    m = StubModel("drop_placeholder")
    r = translate(SRC_MED, m, G, back_translate=False, use_ner=NER)
    check("dropped placeholder is caught", not r.passed, "; ".join(r.reasons))
    if not r.passed:
        print(f"       reason: {r.reasons[0]}")

    m = StubModel("ignore_placeholders")
    r = translate(SRC_MED, m, G, back_translate=False, use_ner=NER)
    check("model ignoring protection is blocked", not r.passed, "; ".join(r.reasons))
    if not r.passed:
        print(f"       reason: {r.reasons[0]}")

    total = 22
    print()
    print("=" * 72)
    print(f"{total - fails}/{total} passed")
    print("=" * 72)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())