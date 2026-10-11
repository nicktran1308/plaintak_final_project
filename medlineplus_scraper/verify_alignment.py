#!/usr/bin/env python3
"""
Score EN/VI alignment with LaBSE and rebuild the exemplar set.

The column-based extractor in extract_pairs.py assigns each Vietnamese block to
the English block it overlaps most. Vietnamese renders taller than English, so
the right-hand column drifts down the page and the offset accumulates: past a
certain point the PREVIOUS Vietnamese block overlaps more than the correct one.
The result is an off-by-one substitution between sibling list items of near
identical length, which a length-ratio filter cannot see by construction.

LaBSE embeds both languages into one space, so a mismatched sibling scores low
regardless of its length or position.

On threshold choice: a first pass fit 0.72 to 20 hand-labelled records, but that
threshold was then validated against those same records, so its apparent perfect
separation was circular. A second round of labelling on unseen records found
~20% defects above the cutoff and ~60% good data below it, so the cosine score
does not cleanly separate good from bad at any threshold. Two failure modes
explain the floor:

  content addition   the Vietnamese carries the correct translation plus extra
                     material. Cosine measures absence, never addition, so these
                     score high. Disagreeing list numbers catch some of them.
  source error       the blocks are aligned correctly and the published PDF
                     itself mistranslates. No filter can detect this.

Roughly 10% of records are correctly aligned but badly translated, which caps
achievable precision near 90% against an observed ~80%. The threshold is
therefore a recall/diversity dial, not a correctness switch.

Usage:
    pip install sentence-transformers --break-system-packages
    python verify_alignment.py                  # reuse existing cosines
    python verify_alignment.py --rescore        # recompute with LaBSE
    python verify_alignment.py --threshold 0.7

Writes, next to pairs_dedup.jsonl:
    pairs_scored.jsonl     every bilingual record plus its "cos" score
    pairs_exemplars.jsonl  records at or above the threshold
"""

import argparse
import json
import re
from pathlib import Path

OUT = Path("medlineplus-vi")
MODEL = "sentence-transformers/LaBSE"
# Defect rates measured either side of 0.72 were comparable, so the lower cutoff
# buys retrieval diversity without a worse error rate.
DEFAULT_THRESHOLD = 0.65


def _leading_number(text):
    m = re.match(r"\s*(\d+)\s*[.)]\s", text)
    return int(m.group(1)) if m else None


def _numbers_disagree(rec):
    a, b = _leading_number(rec["en"]), _leading_number(rec["vi"])
    return a is not None and b is not None and a != b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--rescore", action="store_true",
                    help="recompute cosines instead of reusing pairs_scored.jsonl")
    args = ap.parse_args()

    scored = OUT / "pairs_scored.jsonl"
    if scored.exists() and not args.rescore:
        bi = [json.loads(l) for l in scored.open(encoding="utf-8")]
        print(f"reusing cosines from {scored} ({len(bi)} records)")
    else:
        src = OUT / "pairs_dedup.jsonl"
        if not src.exists():
            raise SystemExit(f"{src} not found; run the dedup step first.")
        recs = [json.loads(l) for l in src.open(encoding="utf-8")]
        bi = [r for r in recs if r["kind"] == "bilingual"]
        print(f"scoring {len(bi)} bilingual records with {MODEL}")

        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(MODEL)
        en = model.encode(
            [r["en"] for r in bi],
            batch_size=args.batch_size,
            normalize_embeddings=True,
            show_progress_bar=True,
        )
        vi = model.encode(
            [r["vi"] for r in bi],
            batch_size=args.batch_size,
            normalize_embeddings=True,
            show_progress_bar=True,
        )
        for r, a, b in zip(bi, en, vi):
            r["cos"] = round(float(a @ b), 4)

        with scored.open("w", encoding="utf-8") as f:
            for r in bi:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"wrote {scored} ({len(bi)} records)")

    keep = [r for r in bi if r["cos"] >= args.threshold]
    # LaBSE scores a pair highly when the correct translation is present even if
    # a stray leading item rode along with it, so it misses the case where the
    # Vietnamese block starts one list item early. Disagreeing list numbers catch
    # exactly that, and teaching a model to add an unsourced sentence is the
    # failure this corpus exists to prevent.
    dropped_by_number = [r for r in keep if _numbers_disagree(r)]
    keep = [r for r in keep if not _numbers_disagree(r)]
    exemplars = OUT / "pairs_exemplars.jsonl"
    with exemplars.open("w", encoding="utf-8") as f:
        for r in keep:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    cs = sorted(r["cos"] for r in bi)
    print(f"\nwrote {exemplars} ({len(keep)} records at cos >= {args.threshold})")
    print(f"  also dropped {len(dropped_by_number)} with disagreeing list numbers")
    print("\ncosine distribution:")
    for p in (5, 25, 50, 75, 95):
        print(f"  p{p:02d} = {cs[int(len(cs) * p / 100)]:.3f}")
    print("\nrecords kept by threshold:")
    for t in (0.60, 0.65, 0.70, 0.72, 0.75, 0.80, 0.85):
        n = sum(1 for c in cs if c >= t)
        print(f"  cos >= {t:.2f}  {n:5d}  ({n / len(cs) * 100:.1f}%)")


if __name__ == "__main__":
    main()
