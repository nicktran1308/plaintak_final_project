#!/usr/bin/env python3
"""
End-to-end smoke test. THIS ONE COSTS MONEY: it calls the real API.

Run from the project root:
    python backend/smoke_test.py

Verifies the full pipeline on the synthetic discharge sheet and prints the
number of API calls made, so refusals and abstentions can be seen to cost zero.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))

import config
from pipeline.chat import ChatEngine
from pipeline.intake import load_document
from pipeline.retrieve import Retriever, chunk_paragraphs
from pipeline.simplify import simplify_once, start
from pipeline.translate import load_glossary, translate

DOC = "eval/synthetic_docs/discharge_instructions.pdf"

calls = {"n": 0}
_raw = None

def counted_claude():
    global _raw
    _raw = config.make_claude()
    def call(p):
        calls["n"] += 1
        return _raw(p)
    return call


def main():
    print("=" * 66)
    print("CONFIG")
    print("=" * 66)
    print(f"  model      {config.MODEL_SIMPLIFY}")
    print(f"  claude key {bool(config.ANTHROPIC_API_KEY)}")
    print(f"  voyage key {bool(config.VOYAGE_API_KEY)}")
    print(f"  embed      {config.EMBED_MODEL}")
    print(f"  threshold  {config.RETRIEVAL_THRESHOLD}")
    G = load_glossary(config.GLOSSARY_PATH)
    print(f"  glossary   {len(G)} terms")
    missing = [n for n, v in [("ANTHROPIC_API_KEY", config.ANTHROPIC_API_KEY),
                              ("VOYAGE_API_KEY", config.VOYAGE_API_KEY)] if not v]
    if missing:
        sys.exit(f"\nMissing in .env: {', '.join(missing)}")

    print("\n" + "=" * 66)
    print("INTAKE")
    print("=" * 66)
    doc = load_document(DOC)
    print(f"  {len(doc.paragraphs)} paragraphs, {len(doc.content())} content")
    target = next(p for p in doc.paragraphs if "metformin" in p.text.lower())
    print(f"  target [{target.para_id}] {target.text[:58]}...")

    print("\n" + "=" * 66)
    print("RETRIEVAL  (Voyage embeddings)")
    print("=" * 66)
    r = Retriever(config.make_embedder(), threshold=config.RETRIEVAL_THRESHOLD)
    r.add(chunk_paragraphs(doc.texts(), doc_id=doc.doc_id))
    print(f"  {len(r.chunks)} chunks embedded")

    model = counted_claude()

    print("\n" + "=" * 66)
    print("SIMPLIFICATION LADDER")
    print("=" * 66)
    lad = start(target.para_id, target.text)
    print(f"  rung 0 (grade {lad.current.readability}): {lad.current.text[:56]}...")
    for _ in range(2):
        before = lad.level
        simplify_once(lad, model, use_ner=config.USE_NER)
        if lad.level == before:
            print(f"  BLOCKED at rung {lad.blocked_at}: {'; '.join(lad.block_reasons)}")
            break
        print(f"  rung {lad.level} (grade {lad.current.readability}): {lad.current.text[:56]}...")

    print("\n" + "=" * 66)
    print("QUESTION ANSWERING")
    print("=" * 66)
    chat = ChatEngine(r, model=model, language="en")
    for q in ["When is my nephrology follow up?",
              "Can I restart the metformin?",
              "What is my cholesterol level?",
              "Tôi có thể uống lại metformin không?"]:
        before = calls["n"]
        resp = chat.ask(q)
        print(f"  [{resp.type.value:9}] calls+{calls['n']-before}  score={resp.retrieval_score:.2f}  {q}")
        print(f"              {resp.text[:60]}")
    print(f"\n  handoff list: {len(chat.handoff_list())} questions")

    print("\n" + "=" * 66)
    print("TRANSLATION")
    print("=" * 66)
    res = translate(target.text, model, G, back_translate=True, use_ner=config.USE_NER)
    print(f"  passed: {res.passed}")
    for s in res.substitutions:
        print(f"    {s}")
    print(f"  VI:   {res.output_vi}")
    print(f"  back: {res.back_en}")
    if not res.passed:
        for x in res.reasons:
            print(f"  REASON: {x}")

    print("\n" + "=" * 66)
    print(f"total API calls: {calls['n']}")
    print("=" * 66)


if __name__ == "__main__":
    main()
