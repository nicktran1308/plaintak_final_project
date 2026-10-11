#!/usr/bin/env python3
"""
Entity-check gate evaluation.

Measures what the 20 unit tests cannot: how the gate performs on model output
it has never seen. The unit tests confirm it catches failures that were
authored deliberately; they say nothing about catch rate, false-positive rate,
or miss rate in the wild.

Three phases
------------
    generate   run the simplifier over the document at every rung and record
               each candidate together with the gate's verdict
    annotate   label each candidate by hand, WITHOUT seeing the verdict
    score      compare the two and report the confusion matrix

The annotation step is deliberately blind. Showing the gate's decision while
labelling would anchor the annotator to it, and the resulting agreement would
measure nothing. The verdict is recorded during generation and only revealed
at scoring time.

Usage
-----
    python eval/run_gate_eval.py --generate          # ~30 model calls
    python eval/run_gate_eval.py --annotate          # no cost, resumable
    python eval/run_gate_eval.py --score
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from pipeline.gate import check_simplification, extract_entities   # noqa: E402
from pipeline.intake import load_document                          # noqa: E402
from pipeline.simplify import MAX_RUNG, PROMPT, TARGETS            # noqa: E402

DOC = ROOT / "eval" / "synthetic_docs" / "discharge_instructions.pdf"
OUT = ROOT / "eval" / "results"
CAND = OUT / "gate_candidates.jsonl"
LABELS = OUT / "gate_labels.jsonl"

BAR = "=" * 74


# --------------------------------------------------------------------------
# Phase 1: generate
# --------------------------------------------------------------------------
def generate(limit: int | None) -> int:
    """
    Produce candidates at every rung, keeping the ones the gate rejects.

    simplify_once discards a blocked candidate, so it cannot be used here: the
    blocked outputs are precisely the cases the evaluation needs. The model is
    called directly and the gate is applied separately.
    """
    from config import make_claude, USE_NER   # noqa: E402

    model = make_claude()
    doc = load_document(DOC)
    # doc.content() already drops headers. Metadata lines that slipped through
    # as body text are excluded too: a date of birth is not an instruction, and
    # simplifying it measures nothing about the gate.
    META = ("patient:", "mrn:", "dob:", "attending:", "admitted:",
            "discharged:", "date of birth", "page ", "signature")
    paras = [p for p in doc.content()
             if not any(m in p.text.lower()[:40] for m in META)]
    if limit:
        paras = paras[:limit]

    OUT.mkdir(parents=True, exist_ok=True)
    rows, calls = [], 0

    for para in paras:
        current = para.text
        for level in range(1, MAX_RUNG + 1):
            candidate = model(
                PROMPT.format(target=TARGETS[level], text=current)
            ).strip()
            calls += 1
            verdict = check_simplification(para.text, candidate, use_ner=USE_NER)
            rows.append({
                "id": f"p{para.para_id}_r{level}",
                "para_id": para.para_id,
                "level": level,
                "original": para.text,
                "candidate": candidate,
                # recorded now, hidden during annotation, revealed at scoring
                "gate_passed": verdict.passed,
                "gate_reasons": list(verdict.reasons),
                "src_entities": sorted(str(e) for e in verdict.src_entities),
                "out_entities": sorted(str(e) for e in verdict.out_entities),
            })
            print(f"  {para.para_id:>3} rung {level}  "
                  f"gate={'pass ' if verdict.passed else 'BLOCK'}  "
                  f"{candidate[:52]}")
            # The ladder anchors every rung to the original, but the model is
            # given the previous rung, matching how simplify.py drives it.
            current = candidate

    CAND.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    print(f"\n{len(rows)} candidates from {len(paras)} paragraphs, "
          f"{calls} model calls")
    print(f"wrote {CAND}")
    print("\nNext: python eval/run_gate_eval.py --annotate")
    return 0


# --------------------------------------------------------------------------
# Phase 2: annotate
# --------------------------------------------------------------------------
QUESTION = """
Did this rewrite LOSE, CHANGE, or INVENT any critical fact?

  Critical facts are: drug names, doses, frequencies, dates, durations,
  lab values, and instructions NOT to do something.

  A rewrite that only changes wording is fine.
  Replacing a clinical term with a lay term is fine (glucose -> blood sugar).
  Dropping an entire clause that carried no critical fact is fine.

  y = yes, something critical was lost, changed, or invented   (BROKEN)
  n = no, every critical fact survived                          (SOUND)
  s = skip this one
  q = save and quit
"""


def annotate() -> int:
    if not CAND.exists():
        sys.exit("No candidates. Run --generate first.")

    rows = [json.loads(l) for l in CAND.open(encoding="utf-8")]
    done = {}
    if LABELS.exists():
        for l in LABELS.open(encoding="utf-8"):
            r = json.loads(l)
            done[r["id"]] = r

    todo = [r for r in rows if r["id"] not in done]
    print(f"{len(done)} already labelled, {len(todo)} remaining")
    print("\nThe gate's decision is hidden on purpose. Seeing it would anchor")
    print("your judgement and the agreement figure would mean nothing.\n")

    for i, row in enumerate(todo, 1):
        print(BAR)
        print(f"[{i}/{len(todo)}]  {row['id']}   rung {row['level']}")
        print(BAR)
        print("\nORIGINAL:")
        print("  " + row["original"].replace("\n", "\n  "))
        print("\nREWRITE:")
        print("  " + row["candidate"].replace("\n", "\n  "))
        print("\nFacts found in the ORIGINAL (for reference, not a verdict):")
        print("  " + ", ".join(row["src_entities"]) or "  (none)")
        print(QUESTION)

        while True:
            ans = input("  y / n / s / q > ").strip().lower()
            if ans in ("y", "n", "s", "q"):
                break
            print("  please answer y, n, s or q")

        if ans == "q":
            break
        if ans == "s":
            continue

        note = input("  note (optional, press Enter to skip) > ").strip()
        done[row["id"]] = {
            "id": row["id"], "para_id": row["para_id"], "level": row["level"],
            "human_broken": ans == "y", "note": note,
        }
        with LABELS.open("w", encoding="utf-8") as f:
            for r in done.values():
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"  saved ({len(done)} total)\n")

    print(f"\n{len(done)} labels in {LABELS}")
    print("Next: python eval/run_gate_eval.py --score")
    return 0


# --------------------------------------------------------------------------
# Phase 3: score
# --------------------------------------------------------------------------
@dataclass
class Matrix:
    tp: int = 0   # broken, gate blocked   — correct catch
    fn: int = 0   # broken, gate passed    — MISS, the dangerous cell
    fp: int = 0   # sound,  gate blocked   — false positive, hides good output
    tn: int = 0   # sound,  gate passed    — correct release

    @property
    def n(self): return self.tp + self.fn + self.fp + self.tn

    @property
    def catch_rate(self):
        d = self.tp + self.fn
        return self.tp / d if d else None

    @property
    def precision(self):
        d = self.tp + self.fp
        return self.tp / d if d else None

    @property
    def false_positive_rate(self):
        d = self.fp + self.tn
        return self.fp / d if d else None


def pct(x): return "n/a" if x is None else f"{x:.1%}"


def score(rescore: bool = False) -> int:
    if not (CAND.exists() and LABELS.exists()):
        sys.exit("Need both candidates and labels. Run --generate then --annotate.")

    cands = {json.loads(l)["id"]: json.loads(l) for l in CAND.open(encoding="utf-8")}

    if rescore:
        # Re-run the CURRENT gate over the stored candidates. The human labels
        # describe the text, not the gate, so a gate change can be measured
        # against them without spending a single model call or asking the
        # annotator to look at anything twice.
        from config import USE_NER   # noqa: E402
        for c in cands.values():
            v = check_simplification(c["original"], c["candidate"], use_ner=USE_NER)
            c["gate_passed"] = v.passed
            c["gate_reasons"] = list(v.reasons)
        print("re-scored with the current gate (no model calls, labels unchanged)\n")
    labels = [json.loads(l) for l in LABELS.open(encoding="utf-8")]

    m = Matrix()
    misses, fps = [], []
    for lab in labels:
        c = cands.get(lab["id"])
        if not c:
            continue
        broken, blocked = lab["human_broken"], not c["gate_passed"]
        if broken and blocked:
            m.tp += 1
        elif broken and not blocked:
            m.fn += 1
            misses.append((lab, c))
        elif not broken and blocked:
            m.fp += 1
            fps.append((lab, c))
        else:
            m.tn += 1

    print(BAR)
    print(f"ENTITY-CHECK GATE  (n = {m.n} hand-labelled candidates)")
    print(BAR)
    print(f"\n{'':22}{'gate blocked':>15}{'gate passed':>14}")
    print(f"{'human: broken':22}{m.tp:>15}{m.fn:>14}")
    print(f"{'human: sound':22}{m.fp:>15}{m.tn:>14}")

    print("\nMETRICS")
    print(f"  catch rate (recall)   {pct(m.catch_rate):>8}   "
          f"of genuinely broken rewrites, the share the gate blocked")
    print(f"  precision             {pct(m.precision):>8}   "
          f"of blocks, the share that were genuinely broken")
    print(f"  false-positive rate   {pct(m.false_positive_rate):>8}   "
          f"of sound rewrites, the share wrongly blocked")

    if misses:
        print(f"\nMISSES ({len(misses)}) — broken output the gate released.")
        print("These are the cases that would reach a patient.")
        for lab, c in misses:
            print(f"\n  {lab['id']}  {lab.get('note') or '(no note)'}")
            print(f"    original: {c['original'][:70]}")
            print(f"    rewrite : {c['candidate'][:70]}")

    if fps:
        print(f"\nFALSE POSITIVES ({len(fps)}) — sound output the gate blocked.")
        print("Each one hides a correct simplification from a patient.")
        for lab, c in fps:
            print(f"\n  {lab['id']}  {'; '.join(c['gate_reasons'])}")
            print(f"    rewrite : {c['candidate'][:70]}")

    print(f"\n{BAR}")
    print("""
READING THIS

  A miss is worse than a false positive: a miss reaches the patient, while a
  false positive only falls back to the clinician's original text. Report both,
  and do not tune one to zero at the other's expense.

  A modest catch rate is a valid result. Measuring the gate's limits is a
  stated contribution of this project, not an incidental check, and an
  unflattering number honestly reported is worth more than a flattering one
  produced by testing against failures you wrote yourself.
""")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generate", action="store_true")
    ap.add_argument("--annotate", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--rescore", action="store_true",
                    help="re-run the current gate over stored candidates; free")
    ap.add_argument("--limit", type=int, default=None,
                    help="only the first N content paragraphs")
    a = ap.parse_args()

    if a.generate:
        return generate(a.limit)
    if a.annotate:
        return annotate()
    if a.score or a.rescore:
        return score(rescore=a.rescore)
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
