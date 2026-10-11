#!/usr/bin/env python3
"""
Translation evaluation and ablation.

Tests the project's own architecture rather than assuming it. The
terminology-grounded pipeline is substantially more work than asking a model
to translate: a hand-authored glossary, placeholder protection, retrieved
exemplars, and two verification passes. If naive translation performs as well,
none of that was necessary, and the honest thing is to find out.

Three arms
----------
    naive       ask the model to translate. No glossary, no protection.
                This is what a patient gets from a general-purpose tool.

    protected   placeholder substitution only. Doses, dates and drug names
                never reach the model; verified glossary terms are inserted
                rather than generated. No exemplars.

    full        protection plus retrieved professionally translated exemplars,
                the deployed configuration.

Every arm is scored the same way, by the entity-check gate operating on the
Vietnamese output and its back-translation. The gate does not know which arm
produced the text.

Measured per arm
----------------
    entity preservation   share of source entities recoverable from the output
    gate pass rate        share of translations safe to show the patient
    forbidden renderings  glossary do_not_use violations, e.g. hold -> giữ,
                          the inversion Kong et al. 2026 documented as harmful
    literal survival      doses and dates appearing verbatim in the Vietnamese

Usage
-----
    python eval/run_translate_eval.py                 # all arms, all paragraphs
    python eval/run_translate_eval.py --arms naive full
    python eval/run_translate_eval.py --limit 4       # cheaper
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from pipeline.gate import check_translation, extract_entities        # noqa: E402
from pipeline.intake import load_document                            # noqa: E402
from pipeline.translate import (BACK_PROMPT, PROMPT, load_glossary,  # noqa: E402
                                protect, restore, select_sense,
                                build_context)

DOC = ROOT / "eval" / "synthetic_docs" / "discharge_instructions.pdf"
OUT = ROOT / "eval" / "results"
BAR = "=" * 74

NAIVE_PROMPT = """Translate the English text into Vietnamese for an older patient with limited health literacy.

Use plain, respectful Vietnamese. Address the reader as "quý vị".
Output only the translation.

ENGLISH: {source}
VIETNAMESE:"""

NAIVE_BACK = """Translate this Vietnamese text into English literally.
Output only the translation.

VIETNAMESE: {text}
ENGLISH:"""

EXEMPLARS_PATH = ROOT / "backend" / "data" / "exemplars.jsonl"


def load_exemplars(k: int = 4) -> list[tuple[str, str]]:
    """
    Exemplar pairs for the full arm.

    Retrieval by embedding would be closer to the deployed system, but a fixed
    sample keeps the ablation about protection versus no protection rather
    than about retrieval quality, and costs no extra API calls.
    """
    if not EXEMPLARS_PATH.exists():
        return []
    out = []
    for line in EXEMPLARS_PATH.open(encoding="utf-8"):
        r = json.loads(line)
        en, vi = r.get("en"), r.get("vi")
        if en and vi and 40 < len(en) < 220:
            out.append((en, vi))
        if len(out) >= k:
            break
    return out


# --------------------------------------------------------------------------
# Arms
# --------------------------------------------------------------------------
def run_naive(source, model, glossary, use_ner):
    vi = model(NAIVE_PROMPT.format(source=source)).strip()
    back = model(NAIVE_BACK.format(text=vi)).strip()
    return vi, back, [], None


def _grounded(source, model, glossary, use_ner, exemplars):
    prot = protect(source, glossary, use_ner=use_ner)
    if prot.unresolved:
        return None, None, prot.substitutions, (
            f"refused: no sense matched for {', '.join(prot.unresolved)}")

    ex = ""
    if exemplars:
        lines = ["\nExamples of professionally translated patient material:"]
        for en, vi in exemplars:
            lines.append(f"EN: {en}\nVI: {vi}")
        ex = "\n".join(lines) + "\n"

    raw = model(PROMPT.format(exemplars=ex, source=prot.text)).strip()
    vi, missing = restore(raw, prot.restore_vi)
    if missing:
        return vi, None, prot.substitutions, (
            f"model dropped {len(missing)} placeholder(s)")

    raw_back = model(BACK_PROMPT.format(text=raw)).strip()
    back, _ = restore(raw_back, prot.restore_en)
    return vi, back, prot.substitutions, None


def run_protected(source, model, glossary, use_ner):
    return _grounded(source, model, glossary, use_ner, [])


def run_full(source, model, glossary, use_ner, exemplars=None):
    return _grounded(source, model, glossary, use_ner, exemplars or [])


ARMS = {"naive": run_naive, "protected": run_protected, "full": run_full}


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------
def gate_glossary(source, glossary, use_ner):
    ctx = build_context(source, use_ner=use_ner)
    return {
        t.en: {"vi": s.vi, "do_not_use": s.do_not_use}
        for t in glossary.values()
        if (s := select_sense(t, ctx)) is not None
    }


def literal_survival(source, vi, use_ner):
    """Doses and dates that must appear verbatim in the Vietnamese."""
    want = [e for e in extract_entities(source, use_ner=use_ner)
            if e.kind in ("dose", "ratio", "date")]
    if not want:
        return None, 0, 0
    low = vi.lower() if vi else ""
    kept = 0
    for e in want:
        num = re.match(r"[\d.]+", e.canon)
        if e.kind == "date":
            mo, day = e.canon.split("-")
            if re.search(rf"\b{day}\b", low) and re.search(rf"\b{mo}\b", low):
                kept += 1
        elif num and num.group(0) in low:
            kept += 1
    return kept / len(want), kept, len(want)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="*", default=list(ARMS), choices=list(ARMS))
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()

    from config import make_claude, USE_NER, GLOSSARY_PATH   # noqa: E402

    model = make_claude()
    glossary = load_glossary(GLOSSARY_PATH)
    exemplars = load_exemplars()
    doc = load_document(DOC)
    META = ("patient:", "mrn:", "dob:", "attending:", "admitted:", "discharged:")
    paras = [p for p in doc.content()
             if not any(m in p.text.lower()[:40] for m in META)]
    if a.limit:
        paras = paras[:a.limit]

    print(f"{len(paras)} paragraphs, arms: {', '.join(a.arms)}")
    print(f"glossary {len(glossary)} terms, exemplars {len(exemplars)}\n")
    if not exemplars:
        print("NOTE: no exemplars found at backend/data/exemplars.jsonl, so the")
        print("      full arm differs from protected only by an empty prompt")
        print("      section. Copy pairs_exemplars.jsonl there to test it properly.\n")

    rows = []
    for para in paras:
        print(f"p{para.para_id}: {para.text[:60]}")
        for arm in a.arms:
            fn = ARMS[arm]
            vi, back, subs, note = (
                fn(para.text, model, glossary, USE_NER, exemplars)
                if arm == "full" else fn(para.text, model, glossary, USE_NER))

            if vi is None:
                rows.append({"para_id": para.para_id, "arm": arm, "refused": True,
                             "note": note, "passed": False})
                print(f"    {arm:10} REFUSED  {note}")
                continue

            v = check_translation(
                para.text, vi, back,
                glossary=gate_glossary(para.text, glossary, USE_NER),
                use_ner=USE_NER)
            src_e = {(e.kind, e.canon) for e in v.src_entities}
            out_e = {(e.kind, e.canon) for e in v.out_entities}
            pres = len(src_e & out_e) / len(src_e) if src_e else None
            lit, lk, ln = literal_survival(para.text, vi, USE_NER)
            forbidden = [r for r in v.reasons if "forbidden rendering" in r]

            rows.append({
                "para_id": para.para_id, "arm": arm, "refused": False,
                "source": para.text, "vi": vi, "back": back,
                "passed": v.passed, "reasons": list(v.reasons),
                "preserved": pres, "literal": lit,
                "literal_kept": lk, "literal_total": ln,
                "forbidden": forbidden, "note": note,
                "substitutions": subs,
            })
            flag = "pass " if v.passed else "BLOCK"
            print(f"    {arm:10} {flag}  entities {len(src_e & out_e)}/{len(src_e)}  "
                  f"literal {lk}/{ln}"
                  + ("  FORBIDDEN" if forbidden else ""))
        print()

    # ---------------- report ----------------
    print(BAR)
    print("TRANSLATION ABLATION")
    print(BAR)
    print(f"\n{'arm':12}{'n':>4}{'pass':>7}{'entities':>10}{'literal':>9}"
          f"{'forbidden':>11}{'refused':>9}")

    for arm in a.arms:
        rs = [r for r in rows if r["arm"] == arm]
        if not rs:
            continue
        ok = [r for r in rs if not r["refused"]]
        passed = sum(1 for r in rs if r["passed"])
        pres = [r["preserved"] for r in ok if r.get("preserved") is not None]
        lit = [r["literal"] for r in ok if r.get("literal") is not None]
        forb = sum(1 for r in ok if r.get("forbidden"))
        ref = sum(1 for r in rs if r["refused"])
        print(f"{arm:12}{len(rs):>4}{passed / len(rs):>7.0%}"
              f"{(sum(pres) / len(pres) if pres else 0):>10.0%}"
              f"{(sum(lit) / len(lit) if lit else 0):>9.0%}"
              f"{forb:>11}{ref:>9}")

    forb_all = [r for r in rows if r.get("forbidden")]
    if forb_all:
        print(f"\nFORBIDDEN RENDERINGS ({len(forb_all)})")
        print("A glossary do_not_use violation. Kong et al. 2026 documented")
        print("'hold the kidney medicine' rendered as an instruction to continue")
        print("it as an error with potential for clinical harm.")
        for r in forb_all:
            print(f"  p{r['para_id']} [{r['arm']}]  {r['forbidden'][0][:70]}")

    by_reason = defaultdict(lambda: defaultdict(int))
    for r in rows:
        if r["refused"] or r["passed"]:
            continue
        for x in r.get("reasons", []):
            key = ("forbidden" if "forbidden" in x
                   else "literal" if "literal check" in x
                   else "back-translation" if "back-translation" in x
                   else x.split(":")[0])
            by_reason[r["arm"]][key] += 1
    if by_reason:
        print("\nBLOCK REASONS BY ARM")
        for arm in a.arms:
            if arm in by_reason:
                items = ", ".join(f"{k} {v}" for k, v in
                                  sorted(by_reason[arm].items(), key=lambda kv: -kv[1]))
                print(f"  {arm:12} {items}")

    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "translate_ablation.json"
    p.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {p}")

    print(f"\n{BAR}")
    print("""
READING THIS

  The comparison that matters is naive against protected. If they score the
  same, the glossary and placeholder work did not earn its cost, and that is a
  finding worth reporting rather than hiding.

  Watch the forbidden-rendering count in particular. A naive arm is free to
  translate "hold" as "giữ", which tells the patient to keep taking a
  medication that was stopped. The protected arm substitutes the verified term
  before the model sees the word, so that inversion is structurally impossible
  rather than merely unlikely.

  All arms share one document and one language pair, so this measures whether
  protection helps here, not how much it helps in general.
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
