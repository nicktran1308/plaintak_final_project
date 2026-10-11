#!/usr/bin/env python3
"""
Mine candidate EN->VI term pairs from the aligned exemplar corpus.

The corpus is block-aligned, not word-aligned, so terms are recovered
statistically: for each English n-gram, find the Vietnamese n-gram that
co-occurs with it across documents far more often than chance, scored by Dice
coefficient over DOCUMENT sets rather than record sets.

The document-count rule is the main quality defense. A candidate must appear in
at least MIN_DOCS distinct source documents, which are translated by different
people at different organisations. Random misalignment does not recur across
independent translators, and neither does one translator's idiosyncratic word
choice. This is what rejects "latching on -> bam".

It does NOT rescue a term whose correct translation depends on context. "hold"
occurs in 33 documents, all of them physical manipulation, so the rule happily
confirms "hold -> giu" -- which is correct for crutches and dangerously wrong
for medication, where "hold" means stop. Sense disambiguation is a schema
problem, not a frequency problem; see SAFETY_OVERRIDES and the hand-authored
tier.

Usage:
    python build_glossary.py [--min-docs 5]
"""

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

OUT = Path("medlineplus-vi")

MIN_DOCS = 5
EN_MAX_N = 3
VI_MAX_N = 4
MIN_DICE = 0.35
# A rival rendering this close to the best one means the corpus disagrees with
# itself, which a human needs to settle.
RIVAL_RATIO = 0.6
# Score margin within which a longer Vietnamese phrase beats a shorter one.
LONGEST_TOLERANCE = 0.10
# A Vietnamese term is the translation of at most one English term. A weaker
# claimant is riding on collocation ("talk" co-occurs with "bac si" because the
# sentence is "talk to your doctor") and is dropped.
VI_CLAIM_RATIO = 0.9

EN_STOP = set("""
a an the and or but if then than that this these those of in on at to for with
from by as is are was were be been being do does did have has had will would
can could should may might must not no you your yours he she it its they them
their we our us i me my so such other some any each more most very will about
into over under out up down off again once here there when where why how all
both few nor only own same too s t just don now
""".split())

VI_STOP = set("""
và của là các một những cho với từ trong ngoài trên dưới khi nếu thì mà này đó
được có không quý vị bạn anh chị em người ta sẽ đã đang bị làm để về như hoặc
cũng rất nhiều ít hơn nhất còn nữa lại vào ra đến tới theo bởi vì nên do sau
trước giữa cùng thêm bớt hay
""".split())


def norm_en(text):
    text = text.lower().replace("\u2019", "'")
    return re.findall(r"[a-z][a-z'-]*", text)


def norm_vi(text):
    return re.findall(r"[^\W\d_]+", text.lower(), re.UNICODE)


def ngrams(tokens, max_n, stop):
    out = set()
    for n in range(1, max_n + 1):
        for i in range(len(tokens) - n + 1):
            gram = tokens[i:i + n]
            if gram[0] in stop or gram[-1] in stop:
                continue
            if all(w in stop for w in gram):
                continue
            if any(len(w) < 2 for w in gram) and n == 1:
                continue
            out.add(" ".join(gram))
    return out


def dice(a, b, both):
    return 2 * both / (a + b) if (a + b) else 0.0


def contained(short, long_):
    """True if `short` is a contiguous sub-phrase of `long_`."""
    return f" {short} " in f" {long_} "


def resolve_vi_claims(rows):
    """
    Drop English terms that merely co-occur with a Vietnamese term already
    better explained by another English term. Without this, every word in
    "talk to your doctor" claims "bac si".
    """
    best = {}
    for r in rows:
        s = r["senses"][0]
        d = s["evidence"]["dice"]
        if s["vi"] not in best or d > best[s["vi"]]:
            best[s["vi"]] = d
    keep, dropped = [], []
    for r in rows:
        s = r["senses"][0]
        weak = s["evidence"]["dice"] < best[s["vi"]] * VI_CLAIM_RATIO
        # A safety-critical term must never vanish from the glossary. Silently
        # dropping "hold" leaves downstream code with no entry to consult and no
        # warning that one is missing, which is worse than a flagged weak entry.
        if weak and r["en"] not in SAFETY_OVERRIDES:
            dropped.append(r)
        else:
            keep.append(r)
    return keep, dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-docs", type=int, default=MIN_DOCS)
    ap.add_argument("--min-dice", type=float, default=MIN_DICE)
    args = ap.parse_args()

    src = OUT / "pairs_exemplars.jsonl"
    recs = [json.loads(l) for l in src.open(encoding="utf-8")]
    print(f"mining {len(recs)} records from {src}")

    en_grams, vi_grams = [], []
    for r in recs:
        en_grams.append(ngrams(norm_en(r["en"]), EN_MAX_N, EN_STOP))
        vi_grams.append(ngrams(norm_vi(r["vi"]), VI_MAX_N, VI_STOP))

    en_docs, vi_docs = defaultdict(set), defaultdict(set)
    for r, eg, vg in zip(recs, en_grams, vi_grams):
        for g in eg:
            en_docs[g].add(r["id"])
        for g in vg:
            vi_docs[g].add(r["id"])

    en_cand = {g for g, d in en_docs.items() if len(d) >= args.min_docs}
    vi_keep = {g for g, d in vi_docs.items() if len(d) >= args.min_docs}
    print(f"english n-grams in >= {args.min_docs} docs: {len(en_cand)}")
    print(f"vietnamese n-grams in >= {args.min_docs} docs: {len(vi_keep)}")

    # For each English candidate, tally Vietnamese grams over the same documents.
    joint = defaultdict(lambda: defaultdict(set))
    occurrences = defaultdict(int)
    for r, eg, vg in zip(recs, en_grams, vi_grams):
        hits = eg & en_cand
        vhits = vg & vi_keep
        for e in hits:
            occurrences[e] += 1
            je = joint[e]
            for v in vhits:
                je[v].add(r["id"])

    rows = []
    for e, vmap in joint.items():
        scored = []
        for v, docs in vmap.items():
            if len(docs) < args.min_docs:
                continue
            d = dice(len(en_docs[e]), len(vi_docs[v]), len(docs))
            if d >= args.min_dice:
                scored.append((d, len(docs), v))
        if not scored:
            continue
        scored.sort(reverse=True)

        # A unigram always scores at least as well as the phrase containing it,
        # and usually a hair better, because it also occurs on its own: "bac"
        # beat "bac si" by 0.011. Among candidates within LONGEST_TOLERANCE of
        # the best score, take the longest phrase instead of the top score.
        best_d = scored[0][0]
        near = [c for c in scored if c[0] >= best_d * (1 - LONGEST_TOLERANCE)]
        chosen = max(near, key=lambda c: (len(c[2].split()), c[0]))

        rivals = []
        for d, nd, v in scored:
            if v == chosen[2]:
                continue
            if contained(v, chosen[2]) or contained(chosen[2], v):
                continue
            if d >= best_d * RIVAL_RATIO:
                rivals.append((d, nd, v))

        examples = []
        for r, eg, vg in zip(recs, en_grams, vi_grams):
            if e in eg and chosen[2] in vg:
                examples.append({"en": r["en"], "vi": r["vi"], "title": r["title"]})
            if len(examples) == 3:
                break

        rows.append({
            "en": e,
            "needs_review": bool(rivals),
            "safety_critical": False,
            "senses": [{
                "sense_id": f"{e.replace(' ', '_')}.1",
                "tier": "mined",
                "gloss": None,
                "context": {"rule": "default", "require_any": [], "exclude_any": []},
                "vi": chosen[2],
                "vi_alternatives": [
                    {"vi": v, "distinct_docs": nd, "dice": round(d, 3)}
                    for d, nd, v in rivals[:4]
                ],
                "evidence": {
                    "distinct_docs": chosen[1],
                    "occurrences": occurrences[e],
                    "dice": round(chosen[0], 3),
                    "examples": examples,
                },
            }],
        })

    rows, parasites = resolve_vi_claims(rows)
    apply_safety_overrides(rows)
    rows.sort(key=lambda r: (-r["senses"][0]["evidence"]["distinct_docs"],
                             -r["senses"][0]["evidence"]["dice"]))

    dest = OUT / "glossary_mined.jsonl"
    with dest.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    nr = sum(1 for r in rows if r["needs_review"])
    sc = sum(1 for r in rows if r["safety_critical"])
    print(f"\nwrote {dest}")
    print(f"  candidates clearing >= {args.min_docs} distinct documents: {len(rows)}")
    print(f"  dropped as collocation parasites: {len(parasites)}")
    print(f"  flagged needs_review (rival renderings): {nr}")
    print(f"  flagged safety_critical: {sc}")

    print("\n20 most frequent candidates by distinct-document support:")
    print(f"  {'docs':>4} {'occ':>4} {'dice':>5}  {'english':28s} vietnamese")
    for r in rows[:20]:
        s = r["senses"][0]
        ev = s["evidence"]
        flag = " [review]" if r["needs_review"] else ""
        flag += " [SAFETY]" if r["safety_critical"] else ""
        print(f"  {ev['distinct_docs']:4d} {ev['occurrences']:4d} "
              f"{ev['dice']:5.2f}  {r['en'][:28]:28s} {s['vi']}{flag}")


# English terms whose correct Vietnamese depends on context. Frequency evidence
# cannot settle these, so the mined sense is scoped and the dangerous sense is
# deferred to the hand-authored tier rather than silently omitted.
SAFETY_OVERRIDES = {
    "hold": {
        "mined_sense_id": "hold.physical",
        "gloss": "to grasp, support or keep in position, physically",
        "exclude_any": ["medicine", "medicines", "medication", "medications",
                        "dose", "doses", "pill", "pills", "tablet", "tablets",
                        "capsule", "capsules", "insulin", "warfarin", "drug",
                        "drugs", "prescription"],
        "note": ("In a medication context 'hold' means STOP, not 'giu'. Kong et "
                 "al. 2026 report clinical harm from 'hold the kidney medicine' "
                 "being rendered as 'keep taking it'. The medication sense is "
                 "hand-authored in glossary_directive_TODO.jsonl; this mined "
                 "sense must never be applied to medication text."),
    },
}


def apply_safety_overrides(rows):
    by_en = {r["en"]: r for r in rows}
    missing = [t for t in SAFETY_OVERRIDES if t not in by_en]
    if missing:
        raise SystemExit(
            f"safety-critical terms absent from mined output: {missing}. "
            "They must be present and scoped, not silently omitted."
        )
    for term, ov in SAFETY_OVERRIDES.items():
        row = by_en.get(term)
        if not row:
            continue
        sense = row["senses"][0]
        sense["sense_id"] = ov["mined_sense_id"]
        sense["gloss"] = ov["gloss"]
        sense["context"] = {"rule": "excludes", "require_any": [],
                            "exclude_any": ov["exclude_any"]}
        sense["note"] = ov["note"]
        row["safety_critical"] = True
        row["needs_review"] = True


if __name__ == "__main__":
    main()
