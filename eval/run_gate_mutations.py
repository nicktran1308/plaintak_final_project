#!/usr/bin/env python3
"""
Gate sensitivity by fault injection.

Blind annotation of 30 real candidates found zero fidelity failures, so the
gate's catch rate could not be computed: there were no positives to catch.
That is a good result for the model and a gap in the evaluation.

This harness closes the gap by corrupting known-sound output in specific,
documented ways and measuring what the gate detects. Every mutation type
reproduces a failure reported in the literature:

    drop_dose        Srinivasu et al. 2026 dropped "500 mg" entirely
    drop_frequency   Srinivasu et al. 2026 lost the dosing schedule
    alter_dose       an order-of-magnitude error, the classic dosing harm
    round_number     Picton et al. 2025 found inconsistent rounding
    flip_negation    Kong et al. 2026 found reversed instructions
    drop_date        follow-up dates lost in simplification
    drop_duration    a time-bounded instruction becoming unbounded
    swap_drug        one medication's instruction applied to another
    invent_dose      Makhmutova et al. 2024 found fabricated detail

WHAT THIS MEASURES, AND WHAT IT DOES NOT

  It measures the gate's sensitivity to known failure classes, applied
  systematically to real model output. That is stronger evidence than
  hand-written unit tests, because the corpus is not chosen to flatter.

  It does NOT measure the catch rate on naturally occurring failures. No
  natural failures occurred, so that number remains unknown. Both facts belong
  in the writeup, and neither should be presented as the other.

Usage
-----
    python eval/run_gate_mutations.py
    python eval/run_gate_mutations.py --show-misses
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from pipeline.gate import check_simplification   # noqa: E402

CAND = ROOT / "eval" / "results" / "gate_candidates.jsonl"
OUT = ROOT / "eval" / "results" / "gate_mutations.json"
BAR = "=" * 74

RE_DOSE = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:mg|mcg|ml|g|l|units?)\b", re.I)
RE_FREQ = re.compile(
    r"\b(?:once|twice|three times|two times|\d+ times)\s+(?:a|an|each|per|every)?\s*day\b"
    r"|\bdaily\b|\bevery night\b|\bat bedtime\b|\bbefore bed\b", re.I)
RE_DATE = re.compile(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b")
RE_DUR = re.compile(r"\b(?:for|in|over)?\s*\d+\s*(?:day|days|week|weeks|hour|hours)\b", re.I)
RE_NEG = re.compile(r"\b(?:do not|don't|never|avoid|stay away from)\b", re.I)
RE_NUM = re.compile(r"\b(\d+)\.(\d+)\b")

DRUGS = ["metformin", "lisinopril", "atorvastatin", "insulin glargine",
         "ibuprofen", "naproxen"]


# --------------------------------------------------------------------------
# Mutations. Each returns the corrupted text, or None when inapplicable.
# --------------------------------------------------------------------------
def drop_dose(t, rng):
    m = list(RE_DOSE.finditer(t))
    if not m:
        return None
    h = rng.choice(m)
    return (t[:h.start()] + t[h.end():]).replace("  ", " ")


def alter_dose(t, rng):
    m = list(RE_DOSE.finditer(t))
    if not m:
        return None
    h = rng.choice(m)
    num = re.search(r"\d+(?:[.,]\d+)?", h.group(0))
    if not num:
        return None
    try:
        v = float(num.group(0).replace(",", "."))
    except ValueError:
        return None
    bad = v / 10 if v >= 10 else v * 10
    bad = str(int(bad)) if bad == int(bad) else str(bad)
    return t[:h.start()] + h.group(0).replace(num.group(0), bad, 1) + t[h.end():]


def round_number(t, rng):
    m = list(RE_NUM.finditer(t))
    if not m:
        return None
    h = rng.choice(m)
    return t[:h.start()] + str(round(float(h.group(0)))) + t[h.end():]


def drop_frequency(t, rng):
    m = list(RE_FREQ.finditer(t))
    if not m:
        return None
    h = rng.choice(m)
    return (t[:h.start()] + t[h.end():]).replace("  ", " ")


def flip_negation(t, rng):
    m = list(RE_NEG.finditer(t))
    if not m:
        return None
    h = rng.choice(m)
    return (t[:h.start()] + t[h.end():]).replace("  ", " ").strip()


def drop_date(t, rng):
    m = list(RE_DATE.finditer(t))
    if not m:
        return None
    h = rng.choice(m)
    return t[:h.start()] + "later" + t[h.end():]


def drop_duration(t, rng):
    m = [x for x in RE_DUR.finditer(t) if not RE_DOSE.match(x.group(0))]
    if not m:
        return None
    h = rng.choice(m)
    return (t[:h.start()] + t[h.end():]).replace("  ", " ")


def swap_drug(t, rng):
    present = [d for d in DRUGS if d in t.lower()]
    if not present:
        return None
    old = rng.choice(present)
    new = rng.choice([d for d in DRUGS if d != old])
    return re.sub(re.escape(old), new, t, count=1, flags=re.I)


def invent_dose(t, rng):
    if RE_DOSE.search(t):
        return None      # only meaningful where the source had no dose
    return t.rstrip(".") + ". Take 20 mg once a day."


MUTATIONS = {
    "drop_dose": drop_dose,
    "alter_dose": alter_dose,
    "round_number": round_number,
    "drop_frequency": drop_frequency,
    "flip_negation": flip_negation,
    "drop_date": drop_date,
    "drop_duration": drop_duration,
    "swap_drug": swap_drug,
    "invent_dose": invent_dose,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--show-misses", action="store_true")
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args()

    if not CAND.exists():
        sys.exit("No candidates. Run run_gate_eval.py --generate first.")

    from config import USE_NER   # noqa: E402

    rows = [json.loads(l) for l in CAND.open(encoding="utf-8")]
    sound = [r for r in rows if r["gate_passed"]]
    print(f"{len(sound)} gate-passed candidates as the clean baseline\n")

    rng = random.Random(a.seed)
    stats = defaultdict(lambda: {"n": 0, "caught": 0})
    misses = []

    for r in sound:
        for name, fn in MUTATIONS.items():
            mutated = fn(r["candidate"], rng)
            if mutated is None or mutated.strip() == r["candidate"].strip():
                continue
            v = check_simplification(r["original"], mutated, use_ner=USE_NER)
            stats[name]["n"] += 1
            if not v.passed:
                stats[name]["caught"] += 1
            else:
                misses.append({
                    "id": r["id"], "mutation": name,
                    "original": r["original"], "mutated": mutated,
                })

    print(BAR)
    print("GATE SENSITIVITY BY INJECTED FAULT")
    print(BAR)
    print(f"\n{'fault':18}{'n':>5}{'caught':>9}{'rate':>9}   source")
    SRC = {
        "drop_dose": "Srinivasu 2026", "drop_frequency": "Srinivasu 2026",
        "alter_dose": "dosing harm", "round_number": "Picton 2025",
        "flip_negation": "Kong 2026", "drop_date": "follow-up loss",
        "drop_duration": "unbounded instruction", "swap_drug": "cross-medication",
        "invent_dose": "Makhmutova 2024",
    }
    tot_n = tot_c = 0
    for name in MUTATIONS:
        st = stats[name]
        if not st["n"]:
            print(f"{name:18}{'—':>5}{'':>9}{'':>9}   not applicable to this corpus")
            continue
        tot_n += st["n"]
        tot_c += st["caught"]
        print(f"{name:18}{st['n']:>5}{st['caught']:>9}"
              f"{st['caught'] / st['n']:>9.1%}   {SRC[name]}")

    print(f"\n{'OVERALL':18}{tot_n:>5}{tot_c:>9}{(tot_c / tot_n if tot_n else 0):>9.1%}")

    if misses:
        print(f"\nUNDETECTED ({len(misses)})")
        by = defaultdict(int)
        for m in misses:
            by[m["mutation"]] += 1
        for k, v in sorted(by.items(), key=lambda kv: -kv[1]):
            print(f"  {v:>3}  {k}")
        if a.show_misses:
            for m in misses[:12]:
                print(f"\n  {m['id']}  [{m['mutation']}]")
                print(f"    original: {m['original'][:66]}")
                print(f"    mutated : {m['mutated'][:66]}")

    OUT.write_text(json.dumps(
        {"seed": a.seed, "baseline": len(sound),
         "stats": {k: dict(v) for k, v in stats.items()},
         "misses": misses}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT}")

    print(f"\n{BAR}")
    print("""
REPORTING THIS

  Report it beside the blind-annotation result, never instead of it. The two
  measure different things:

    blind annotation   0 of 30 real candidates were broken, and the gate
                       blocked 0. False-positive rate 0%. Catch rate is
                       undefined because no natural failure occurred.

    fault injection    the rate above, on faults introduced deliberately.
                       This is sensitivity to known failure classes, not the
                       catch rate on failures that arise on their own.

  The honest sentence is that the model produced no fidelity failures on this
  document, so the gate's real-world catch rate remains unmeasured, and its
  sensitivity to documented failure modes is the figure reported here.
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
