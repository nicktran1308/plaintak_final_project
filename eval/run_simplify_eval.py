#!/usr/bin/env python3
"""
Simplification evaluation.

Reports simplification quality in two tiers, because the corpora that carry
gold plain-language references are biomedical abstracts rather than the
discharge instructions this system targets:

    reference-based    SARI against PLABA, Cochrane, or Med-EASi gold
                       simplifications
    reference-free     readability change and entity preservation on
                       target-domain synthetic documents

EVERY READABILITY FIGURE IS REPORTED BESIDE ENTITY PRESERVATION, ALWAYS.

That is not a formatting preference. Flesch-Kincaid scores this project's own
source sentence "HOLD metformin 500 mg PO BID until you follow up with
nephrology on 11/14" at grade 6.8, because BID is one syllable and PO is two
letters: the abbreviations that make the sentence unreadable actively lower
its score. A simplifier that expands BID to "two times a day" — an
unambiguous improvement — makes the number worse. Readability alone would
therefore score correct simplification as failure, and a system optimised
against it would be optimised backwards.

ON BERTSCORE

The proposal names BERTScore. It is not computed here. BERTScore requires
PyTorch, PyTorch requires NumPy 2, and the pinned clinical NLP stack
(spaCy 3.7.4, scispaCy 0.5.4, thinc 8.2.3) requires NumPy 1. These cannot
coexist, and the gate depends on scispaCy, so the clinical stack takes
precedence. Semantic similarity is instead computed as cosine over voyage-3
embeddings, which needs no local ML runtime. It is labelled as such
throughout and is NOT reported as BERTScore.

Usage
-----
    python eval/run_simplify_eval.py --inspect
    python eval/run_simplify_eval.py --corpus cochrane --n 25
    python eval/run_simplify_eval.py --target-domain
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from pipeline.gate import check_simplification, extract_entities   # noqa: E402
from pipeline.intake import load_document                          # noqa: E402
from pipeline.simplify import PROMPT, TARGETS                      # noqa: E402

DATA = ROOT / "plaintalk-data"
DOC = ROOT / "eval" / "synthetic_docs" / "discharge_instructions.pdf"
OUT = ROOT / "eval" / "results"
BAR = "=" * 74


# --------------------------------------------------------------------------
# SARI (Xu et al. 2016), implemented directly.
#
# The reference implementation ships inside frameworks that pull in torch, so
# it is written out here. SARI averages three n-gram scores: F1 over n-grams
# correctly kept, precision over n-grams correctly deleted, and F1 over
# n-grams correctly added. Unlike BLEU it rewards deletion, which is most of
# what simplification does.
# --------------------------------------------------------------------------
def _ngrams(tokens: list[str], n: int) -> Counter:
    return Counter(tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1))


def _f1(p: float, r: float) -> float:
    return 0.0 if p + r == 0 else 2 * p * r / (p + r)


def sari(source: str, output: str, references: list[str], max_n: int = 4) -> float:
    s_tok, o_tok = source.lower().split(), output.lower().split()
    r_toks = [r.lower().split() for r in references]
    n_ref = len(r_toks)
    keep_s, del_s, add_s = [], [], []

    for n in range(1, max_n + 1):
        S, O = _ngrams(s_tok, n), _ngrams(o_tok, n)
        R = Counter()
        for rt in r_toks:
            R.update(_ngrams(rt, n))

        # kept: present in source and output, weighted by how many references
        # also kept it
        keep_o = {g: min(S[g], O[g]) for g in S if O[g] > 0}
        keep_r = {g: min(S[g], R[g] / n_ref) for g in S if R[g] > 0}
        inter = sum(min(keep_o.get(g, 0), keep_r.get(g, 0)) for g in set(keep_o) | set(keep_r))
        kp = inter / sum(keep_o.values()) if keep_o else 1.0
        kr = inter / sum(keep_r.values()) if keep_r else 1.0
        keep_s.append(_f1(kp, kr))

        # deleted: in source, dropped by the output, and dropped by references
        del_o = {g: max(S[g] - O[g], 0) for g in S}
        del_r = {g: max(S[g] - R[g] / n_ref, 0) for g in S}
        d_inter = sum(min(del_o[g], del_r[g]) for g in S)
        del_s.append(d_inter / sum(del_o.values()) if sum(del_o.values()) else 1.0)

        # added: absent from source, present in output and in references
        add_o = {g: O[g] for g in O if S[g] == 0}
        add_r = {g: R[g] for g in R if S[g] == 0}
        a_inter = sum(1 for g in add_o if g in add_r)
        ap = a_inter / len(add_o) if add_o else 1.0
        ar = a_inter / len(add_r) if add_r else 1.0
        add_s.append(_f1(ap, ar))

    avg = lambda xs: sum(xs) / len(xs)     # noqa: E731
    return 100.0 * (avg(keep_s) + avg(del_s) + avg(add_s)) / 3


# --------------------------------------------------------------------------
# Corpora
# --------------------------------------------------------------------------
def load_cochrane(split="test") -> list[tuple[str, list[str]]]:
    p = DATA / "cochrane" / f"{split}.jsonl"
    if not p.exists():
        return []
    out = []
    for line in p.open(encoding="utf-8"):
        r = json.loads(line)
        src, tgt = r.get("source"), r.get("target")
        if src and tgt:
            out.append((src, [tgt]))
    return out


def load_med_easi(split="test") -> list[tuple[str, list[str]]]:
    p = DATA / "med-easi" / f"{split}.jsonl"
    if not p.exists():
        return []
    out = []
    for line in p.open(encoding="utf-8"):
        r = json.loads(line)
        # Field names vary across releases; try the usual pairs.
        src = (r.get("Expert") or r.get("expert") or r.get("source")
               or r.get("complex"))
        tgt = (r.get("Simple") or r.get("simple") or r.get("target")
               or r.get("layman"))
        if src and tgt:
            out.append((src, [tgt]))
    return out


def load_plaba(split="test") -> list[tuple[str, list[str]]]:
    p = DATA / "plaba" / f"{split}.csv"
    if not p.exists():
        return []
    out = []
    with p.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            keys = {k.lower(): k for k in row}
            src = next((row[keys[k]] for k in ("input_text", "source", "abstract",
                                               "sentence", "original", "complex")
                        if k in keys), None)
            tgt = next((row[keys[k]] for k in ("target_text", "target", "adaptation",
                                               "simple", "simplified", "plain")
                        if k in keys), None)
            if src and tgt:
                out.append((src.strip(), [tgt.strip()]))
    return out


CORPORA = {"cochrane": load_cochrane, "med-easi": load_med_easi, "plaba": load_plaba}


def inspect() -> int:
    """Print each corpus's schema. Costs nothing and confirms the loaders."""
    print(BAR); print("CORPUS INSPECTION"); print(BAR)
    for name in ("cochrane", "med-easi", "plaba"):
        d = DATA / name
        print(f"\n{name}  ({d})")
        if not d.exists():
            print("  not found")
            continue
        for f in sorted(d.iterdir()):
            print(f"  {f.name}")
        pairs = CORPORA[name]("test")
        print(f"  loader returned {len(pairs)} pairs")
        if pairs:
            s, t = pairs[0]
            print(f"    source: {s[:88]}")
            print(f"    target: {t[0][:88]}")
        else:
            # show raw keys so the loader can be corrected
            for f in sorted(d.iterdir()):
                if f.suffix == ".jsonl":
                    r = json.loads(f.open(encoding="utf-8").readline())
                    print(f"    {f.name} keys: {list(r)}")
                    break
                if f.suffix == ".csv":
                    with f.open(encoding="utf-8") as fh:
                        print(f"    {f.name} columns: {next(csv.reader(fh))}")
                    break
    return 0


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------
def g(x, width=5):
    """Format a possibly-missing grade. textstat is optional."""
    return f"{x:>{width}.1f}" if isinstance(x, (int, float)) else f"{'n/a':>{width}}"


def readability(text: str):
    try:
        import textstat
        return round(textstat.flesch_kincaid_grade(text), 1)
    except Exception:
        return None


def entity_report(src: str, out: str, use_ner: bool):
    v = check_simplification(src, out, use_ner=use_ner)
    src_e = {(e.kind, e.canon) for e in v.src_entities}
    out_e = {(e.kind, e.canon) for e in v.out_entities}
    kept = len(src_e & out_e)
    return {
        "n_src": len(src_e),
        "kept": kept,
        "preserved": kept / len(src_e) if src_e else None,
        "passed": v.passed,
        "reasons": list(v.reasons),
    }


def cosine(a, b):
    num = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return 0.0 if na == 0 or nb == 0 else num / (na * nb)


# --------------------------------------------------------------------------
# Runs
# --------------------------------------------------------------------------
def run_corpus(name: str, n: int, level: int, embed: bool) -> int:
    from config import make_claude, make_embedder, USE_NER   # noqa: E402

    pairs = CORPORA[name]("test") or CORPORA[name]("validation")
    if not pairs:
        sys.exit(f"No pairs loaded from {name}. Run --inspect and send me the schema.")
    pairs = pairs[:n]
    model = make_claude()
    embedder = make_embedder() if embed else None

    print(f"{name}: {len(pairs)} pairs at ladder level {level}\n")
    rows = []
    for i, (src, refs) in enumerate(pairs, 1):
        out = model(PROMPT.format(target=TARGETS[level], text=src)).strip()
        r = {
            "i": i, "source": src, "output": out, "reference": refs[0],
            "sari": round(sari(src, out, refs), 2),
            "grade_src": readability(src),
            "grade_out": readability(out),
            "grade_ref": readability(refs[0]),
            "entities": entity_report(src, out, USE_NER),
        }
        if embedder:
            v = embedder([src, out])
            r["embed_cos"] = round(cosine(v[0], v[1]), 3)
        rows.append(r)
        e = r["entities"]
        print(f"  {i:>3}  SARI {r['sari']:>6}  grade {g(r['grade_src'])} -> "
              f"{g(r['grade_out'])}  entities {e['kept']}/{e['n_src']} "
              f"{'pass' if e['passed'] else 'BLOCK'}")

    report(name, rows, level)
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"simplify_{name}_L{level}.json"
    p.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {p}")
    return 0


def run_target_domain(level_max: int) -> int:
    """
    Reference-free evaluation on the document this system actually targets.

    No gold simplification exists for a discharge instruction sheet, so SARI
    cannot be computed. Readability and entity preservation can, and together
    they are the honest measurement for this tier.
    """
    from config import make_claude, USE_NER   # noqa: E402

    model = make_claude()
    doc = load_document(DOC)
    META = ("patient:", "mrn:", "dob:", "attending:", "admitted:", "discharged:")
    paras = [p for p in doc.content()
             if not any(m in p.text.lower()[:40] for m in META)]

    print(f"target domain: {len(paras)} content paragraphs, levels 1..{level_max}\n")
    rows = []
    for para in paras:
        current = para.text
        for lvl in range(1, level_max + 1):
            out = model(PROMPT.format(target=TARGETS[lvl], text=current)).strip()
            r = {
                "para_id": para.para_id, "level": lvl,
                "source": para.text, "output": out,
                "grade_src": readability(para.text),
                "grade_out": readability(out),
                "entities": entity_report(para.text, out, USE_NER),
            }
            rows.append(r)
            e = r["entities"]
            print(f"  p{para.para_id:<3} L{lvl}  grade {g(r['grade_src'])} -> "
                  f"{g(r['grade_out'])}  entities {e['kept']}/{e['n_src']} "
                  f"{'pass' if e['passed'] else 'BLOCK'}")
            current = out

    report("target-domain", rows, None, reference_free=True)
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "simplify_target_domain.json"
    p.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {p}")
    return 0


def report(name, rows, level, reference_free=False) -> None:
    def mean(key, where=lambda r: True):
        vals = [r[key] for r in rows if where(r) and r.get(key) is not None]
        return sum(vals) / len(vals) if vals else None

    print(f"\n{BAR}")
    print(f"{name.upper()}" + (f"  (level {level})" if level else ""))
    print(BAR)

    if not reference_free:
        s = mean("sari")
        print(f"\n  SARI                        {s:.2f}" if s else "\n  SARI  n/a")
        c = mean("embed_cos")
        if c is not None:
            print(f"  embedding cosine            {c:.3f}   "
                  f"voyage-3, NOT BERTScore (see module docstring)")

    gs, go = mean("grade_src"), mean("grade_out")
    if gs is None or go is None:
        print("\n  readability                 n/a   (pip install textstat)")
    else:
        print(f"\n  readability  source        {gs:>6.1f}")
        print(f"               output        {go:>6.1f}   ({go - gs:+.1f} grade levels)")
        if not reference_free:
            gr = mean("grade_ref")
            if gr is not None:
                print(f"               gold reference{gr:>6.1f}")

    pres = [r["entities"]["preserved"] for r in rows
            if r["entities"]["preserved"] is not None]
    passed = sum(1 for r in rows if r["entities"]["passed"])
    print(f"\n  entity preservation         "
          f"{(sum(pres) / len(pres) if pres else 0):.1%}")
    print(f"  gate pass rate              {passed / len(rows):.1%} "
          f"({passed}/{len(rows)})")

    # The pairing that the whole two-tier design exists for.
    improved_but_lost = [
        r for r in rows
        if r["grade_out"] is not None and r["grade_src"] is not None
        and r["grade_out"] < r["grade_src"] and not r["entities"]["passed"]
    ]
    if improved_but_lost:
        print(f"\n  READABILITY IMPROVED BUT ENTITIES LOST: {len(improved_but_lost)}")
        print("  Each of these would score as a success on readability alone.")
        for r in improved_but_lost[:5]:
            print(f"    grade {g(r['grade_src'])} -> {g(r['grade_out'])}   "
                  f"{'; '.join(r['entities']['reasons'])[:54]}")

    worse = [r for r in rows if r["grade_out"] is not None
             and r["grade_src"] is not None and r["grade_out"] > r["grade_src"]]
    if worse:
        print(f"\n  readability got WORSE on {len(worse)} of {len(rows)}")
        print("  Expanding an abbreviation adds syllables, so a correct rewrite")
        print("  can raise the score. Read this beside entity preservation.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inspect", action="store_true")
    ap.add_argument("--corpus", choices=list(CORPORA))
    ap.add_argument("--target-domain", action="store_true")
    ap.add_argument("--n", type=int, default=25)
    ap.add_argument("--level", type=int, default=2, choices=[1, 2, 3])
    ap.add_argument("--embed", action="store_true",
                    help="also compute voyage-3 cosine (extra API calls)")
    a = ap.parse_args()

    if a.inspect:
        return inspect()
    if a.corpus:
        return run_corpus(a.corpus, a.n, a.level, a.embed)
    if a.target_domain:
        return run_target_domain(a.level)
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
