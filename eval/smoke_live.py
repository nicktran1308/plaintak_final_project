#!/usr/bin/env python3
"""
Live smoke test: run the simplification ladder and the translation pipeline
against the real model on the real document.

This is NOT a measurement. It answers one question: does the pipeline survive
contact with a live model? Every module was built and verified against stubs,
so the failure modes this catches are the ones stubs cannot show — a model
mangling a ⟦N⟧ placeholder, returning markdown fences, prefacing its answer
with "Here is the translation:", or wrapping output in quotes.

Cost: roughly 20-30 model calls. A few cents.

Usage
-----
    python eval/smoke_live.py                  # 3 paragraphs, ladder + translation
    python eval/smoke_live.py --paras 4 9 11   # specific paragraphs
    python eval/smoke_live.py --no-translate   # ladder only, cheaper
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from pipeline.gate import extract_entities                       # noqa: E402
from pipeline.intake import load_document                        # noqa: E402
from pipeline.simplify import MAX_RUNG, simplify_once, start     # noqa: E402
from pipeline.translate import load_glossary, protect, translate  # noqa: E402

DOC = ROOT / "eval" / "synthetic_docs" / "discharge_instructions.pdf"
GLOSSARY = ROOT / "backend" / "data" / "glossary_directive_DONE.jsonl"

BAR = "=" * 74


class Counter:
    """Wraps the model so calls can be counted and failures surfaced."""

    def __init__(self, fn):
        self.fn = fn
        self.calls = 0

    def __call__(self, prompt: str) -> str:
        self.calls += 1
        return self.fn(prompt)


def show_entities(label, text):
    ents = sorted(str(e) for e in extract_entities(text))
    print(f"    {label}: {', '.join(ents) if ents else '(none)'}")


def run_ladder(doc, para_id, model):
    para = doc.get(para_id)
    if para is None:
        print(f"  paragraph {para_id} not found")
        return
    print(f"\n{BAR}\nSIMPLIFICATION LADDER — paragraph {para_id}\n{BAR}")
    print(f"  rung 0 (grade {para.text and start(para_id, para.text).current.readability}):")
    print(f"    {para.text[:150]}")

    lad = start(para_id, para.text)
    show_entities("entities", para.text)

    while lad.can_simplify:
        before = lad.level
        simplify_once(lad, model)
        if lad.blocked_at is not None:
            print(f"\n  rung {lad.blocked_at}: BLOCKED by the gate")
            for r in lad.block_reasons:
                print(f"    reason: {r}")
            print(f"  patient stays on rung {lad.level}")
            break
        if lad.level == before:
            break
        r = lad.current
        print(f"\n  rung {r.level} (grade {r.readability}):")
        print(f"    {r.text[:150]}")

    print(f"\n  final: rung {lad.level} of {MAX_RUNG}, status = {lad.status}")


def run_translation(doc, para_id, model, glossary):
    para = doc.get(para_id)
    if para is None:
        return
    print(f"\n{BAR}\nTRANSLATION — paragraph {para_id}\n{BAR}")
    print(f"  source:\n    {para.text[:150]}")

    prot = protect(para.text, glossary)
    print(f"\n  protected (this is all the model sees):\n    {prot.text[:150]}")
    for sub in prot.substitutions:
        print(f"    {sub}")
    if prot.unresolved:
        print(f"  UNRESOLVED safety-critical terms: {prot.unresolved}")
        print("  translation will be refused; the patient sees the English original")
        return

    res = translate(para.text, model, glossary, back_translate=True)
    print(f"\n  vietnamese:\n    {(res.output_vi or '(none)')[:150]}")
    print(f"\n  back-translation:\n    {(res.back_en or '(none)')[:150]}")
    print(f"\n  gate verdict: {'PASS — shown to patient' if res.passed else 'BLOCK — falls back to English'}")
    for r in res.reasons:
        print(f"    {r}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paras", type=int, nargs="*", default=[9, 15, 19],
                    help="paragraph ids to test (default: a medication item, "
                         "the activity block, and the ED criteria)")
    ap.add_argument("--no-translate", action="store_true")
    ap.add_argument("--no-ladder", action="store_true")
    args = ap.parse_args()

    from config import make_claude   # noqa: E402

    doc = load_document(DOC)
    print(f"loaded {DOC.name}: {len(doc.paragraphs)} paragraphs, "
          f"{len(doc.content())} content")

    glossary = {}
    if not args.no_translate:
        if not GLOSSARY.exists():
            print(f"glossary not found at {GLOSSARY}; skipping translation")
            args.no_translate = True
        else:
            glossary = load_glossary(GLOSSARY)
            print(f"glossary: {len(glossary)} terms")

    model = Counter(make_claude())

    for pid in args.paras:
        if not args.no_ladder:
            run_ladder(doc, pid, model)
        if not args.no_translate:
            run_translation(doc, pid, model, glossary)

    print(f"\n{BAR}")
    print(f"model calls: {model.calls}")
    print(BAR)
    print("""
WHAT TO LOOK FOR

  Ladder
    - does the grade number go DOWN as the rung number goes up?
    - do the entities survive, or does the gate block a rung?
    - a BLOCK is not a failure: it is the gate doing its job. Read the reason.

  Translation
    - the 'protected' line must contain NO doses, dates or drug names
    - the vietnamese must contain the numbers verbatim (500 mg, 11/14)
    - the back-translation should resemble the English source
    - if the model returned markdown fences, quotes, or a preamble like
      'Here is the translation:', the prompt needs tightening
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
