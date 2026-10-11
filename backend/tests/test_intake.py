#!/usr/bin/env python3
"""Tests for intake.py and simplify.py. No API key required."""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from pipeline.intake import load_text, split_paragraphs, is_header, is_list_item
from pipeline.simplify import MAX_RUNG, simplify_once, simplify_paragraph, start

NER = False

DISCHARGE = """VALLEY GENERAL MEDICAL CENTER

DISCHARGE DIAGNOSIS

Primary: Acute kidney injury, Stage 2, secondary to volume
depletion, superimposed on Stage 3a chronic kidney disease.

MEDICATION INSTRUCTIONS

1. Hold metformin 500 mg PO BID until you follow up with
   nephrology on 11/14.
2. Continue atorvastatin 40 mg PO QHS without interruption.
3. Avoid all NSAIDs, including ibuprofen.

Page 1 of 2

ACTIVITY AND DIET

Ambulate as tolerated. Avoid strenuous exertion for 7 days.
"""

ORIGINAL = "Hold metformin 500 mg PO BID until you follow up with nephrology on 11/14."


class StubModel:
    """Returns a canned rewrite per level, or a deliberately broken one."""

    def __init__(self, mode="good"):
        self.mode = mode
        self.calls = 0

    def __call__(self, prompt: str) -> str:
        self.calls += 1
        if self.mode == "drops_dose":
            return "Stop taking metformin two times a day until 11/14."
        if self.mode == "drops_negation":
            return "Take metformin 500 mg two times a day until 11/14."
        if self.mode == "invents":
            return ("Stop taking metformin 500 mg two times a day until 11/14. "
                    "Also take 20 mg of aspirin.")
        if "4th grade" in prompt:
            return "Stop metformin 500 mg. Take it 2 times a day. Stop until 11/14."
        if "6th grade" in prompt:
            return "Stop taking metformin 500 mg two times a day until you see the kidney doctor on 11/14."
        return "Stop taking metformin 500 mg by mouth two times a day until your kidney visit on 11/14."


def main() -> int:
    fails = 0

    def check(name, cond, detail=""):
        nonlocal fails
        fails += not cond
        print(f"[{'ok ' if cond else 'FAIL'}] {name}")
        if detail and not cond:
            print(f"         {detail}")

    print("=" * 72)
    print("INTAKE")
    print("=" * 72)
    doc = load_text(DISCHARGE, "discharge")
    for p in doc.paragraphs:
        print(f"   [{p.para_id:2}] {p.kind:10} {p.text[:54]}")

    kinds = [p.kind for p in doc.paragraphs]
    check("headers detected", kinds.count("header") >= 3, f"got {kinds.count('header')}")
    check("list items detected", kinds.count("list_item") == 3, f"got {kinds.count('list_item')}")
    check("page furniture dropped",
          not any("Page 1 of 2" in p.text for p in doc.paragraphs))
    check("wrapped lines rejoined",
          any("nephrology on 11/14" in p.text and p.kind == "list_item"
              for p in doc.paragraphs))
    check("each list item is separate",
          sum(1 for p in doc.paragraphs if "metformin" in p.text) == 1)
    check("headers excluded from content",
          all(p.kind != "header" for p in doc.content()))
    check("paragraph ids are sequential",
          [p.para_id for p in doc.paragraphs] == list(range(len(doc.paragraphs))))

    ids_a = [p.para_id for p in load_text(DISCHARGE).paragraphs]
    ids_b = [p.para_id for p in load_text(DISCHARGE).paragraphs]
    check("splitting is deterministic", ids_a == ids_b)

    check("is_header on a caps line", is_header("MEDICATION INSTRUCTIONS"))
    check("is_header rejects a sentence",
          not is_header("Ambulate as tolerated and avoid exertion for 7 days."))
    check("is_list_item on numbered", is_list_item("1. Hold metformin"))
    check("is_list_item on bullet", is_list_item("\u2022 Avoid NSAIDs"))

    print()
    print("=" * 72)
    print("SIMPLIFICATION LADDER")
    print("=" * 72)

    m = StubModel("good")
    lad = simplify_paragraph(0, ORIGINAL, m, to_level=1, use_ner=NER)
    check("rung 1 added", lad.level == 1 and lad.current.verified,
          "; ".join(lad.block_reasons))
    print(f"       rung 1: {lad.current.text[:62]}")

    lad = simplify_paragraph(0, ORIGINAL, StubModel("good"), to_level=3, use_ner=NER)
    check("ladder climbs to max", lad.level == MAX_RUNG, f"level={lad.level}")
    check("ladder then exhausted", not lad.can_simplify and lad.status == "exhausted")
    for r in lad.rungs:
        print(f"       rung {r.level}: {r.text[:60]}")

    check("rung 0 is the untouched original", lad.rungs[0].text == ORIGINAL)

    m = StubModel("drops_dose")
    lad = simplify_paragraph(0, ORIGINAL, m, to_level=1, use_ner=NER)
    check("dropped dose blocks the rung",
          lad.blocked_at == 1 and lad.level == 0 and lad.status == "blocked")
    print(f"       reason: {lad.block_reasons[0] if lad.block_reasons else '-'}")

    m = StubModel("drops_negation")
    lad = simplify_paragraph(0, ORIGINAL, m, to_level=1, use_ner=NER)
    check("dropped negation blocks the rung", lad.blocked_at == 1)

    m = StubModel("invents")
    lad = simplify_paragraph(0, ORIGINAL, m, to_level=1, use_ner=NER)
    check("invented dose blocks the rung", lad.blocked_at == 1)
    print(f"       reason: {lad.block_reasons[0] if lad.block_reasons else '-'}")

    m = StubModel("good")
    lad = start(0, ORIGINAL)
    for _ in range(6):
        simplify_once(lad, m, use_ner=NER)
    check("no calls past the last rung", m.calls == MAX_RUNG, f"calls={m.calls}")

    # A blocked ladder keeps the last verified rung rather than resetting.
    lad = simplify_paragraph(0, ORIGINAL, StubModel("good"), to_level=2, use_ner=NER)
    before = lad.current.text
    simplify_once(lad, StubModel("drops_dose"), use_ner=NER)
    check("block preserves the last good rung",
          lad.current.text == before and lad.blocked_at == 3)

    total = 20
    print()
    print("=" * 72)
    print(f"{total - fails}/{total} passed")
    print("=" * 72)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
