#!/usr/bin/env python3
"""
Tests for the abstention path: scope.py, retrieve.py, chat.py.

The central assertion is not "did it answer correctly" but "was the model
called at all". Refusals and abstentions must exit before generation.

Run:  python test_chat.py     (no API key, no scispaCy)
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from pipeline.chat import ChatEngine, ResponseType
from pipeline.retrieve import BagOfWordsEmbedder, Retriever, chunk_paragraphs
from pipeline.scope import Scope, classify

DOC = [
    "Hold metformin 500 mg PO BID until you follow up with nephrology on 11/14.",
    "Continue atorvastatin 40 mg PO QHS without interruption.",
    "Your fasting glucose was 126 mg/dL on 11/07.",
    "Return to the emergency department if you have decreased urine output.",
]

SCOPE_CASES = [
    # (question, expected scope)
    ("When is my follow-up appointment?", Scope.INFORMATIONAL),
    ("What dose of metformin am I taking?", Scope.INFORMATIONAL),
    ("Khi nào tôi tái khám?", Scope.INFORMATIONAL),
    ("Liều metformin của tôi là bao nhiêu?", Scope.INFORMATIONAL),

    ("Can I restart the metformin?", Scope.ADVICE_SEEKING),
    ("Should I stop taking my medicine?", Scope.ADVICE_SEEKING),
    ("Is it safe to drink alcohol with this?", Scope.ADVICE_SEEKING),
    ("Is my blood sugar dangerous?", Scope.ADVICE_SEEKING),
    ("What should I do?", Scope.ADVICE_SEEKING),
    ("Do I have kidney disease?", Scope.ADVICE_SEEKING),
    ("Tôi có thể uống lại metformin không?", Scope.ADVICE_SEEKING),
    ("Tôi có nên ngưng uống thuốc không?", Scope.ADVICE_SEEKING),
    ("Đường huyết của tôi có nguy hiểm không?", Scope.ADVICE_SEEKING),
    ("Tôi nên làm gì?", Scope.ADVICE_SEEKING),

    ("I'm having chest pain, what do I do?", Scope.EMERGENCY),
    ("Tôi bị đau ngực", Scope.EMERGENCY),
    ("I think I took too much insulin", Scope.EMERGENCY),
]


class RecordingModel:
    """Stand-in for Claude. Records whether it was called."""

    def __init__(self, reply="The passage says your follow-up is on 11/14."):
        self.calls = 0
        self.reply = reply

    def __call__(self, prompt: str) -> str:
        self.calls += 1
        return self.reply


def build(threshold=0.30, model=None):
    emb = BagOfWordsEmbedder()
    r = Retriever(emb, threshold=threshold)
    r.add(chunk_paragraphs(DOC, doc_id="discharge"))
    return ChatEngine(r, model=model, language="en")


def main() -> int:
    fails = 0

    print("=" * 72)
    print("SCOPE CLASSIFIER  (no model, bilingual)")
    print("=" * 72)
    for q, want in SCOPE_CASES:
        got = classify(q).scope
        ok = got is want
        fails += not ok
        print(f"[{'ok ' if ok else 'FAIL'}] {want.value:15} <- {q}")
        if not ok:
            print(f"         got {got.value}")

    print()
    print("=" * 72)
    print("ABSTENTION PATH  (asserting the model is NOT called)")
    print("=" * 72)

    # refusal exits before the model
    m = RecordingModel()
    eng = build(model=m)
    r = eng.ask("Can I restart the metformin?")
    ok = r.type is ResponseType.REFUSAL and not r.model_called and m.calls == 0
    fails += not ok
    print(f"[{'ok ' if ok else 'FAIL'}] refusal exits pre-model     "
          f"type={r.type.value} model_calls={m.calls}")

    # emergency exits before the model
    m = RecordingModel()
    eng = build(model=m)
    r = eng.ask("Tôi bị đau ngực")
    ok = r.type is ResponseType.EMERGENCY and m.calls == 0
    fails += not ok
    print(f"[{'ok ' if ok else 'FAIL'}] emergency exits pre-model   "
          f"type={r.type.value} model_calls={m.calls}")

    # plausible-but-absent: topically close, not in the document
    m = RecordingModel()
    eng = build(model=m)
    r = eng.ask("What is my cholesterol reading?")
    ok = r.type is ResponseType.ABSTAIN and m.calls == 0
    fails += not ok
    print(f"[{'ok ' if ok else 'FAIL'}] absent info exits pre-model "
          f"type={r.type.value} score={r.retrieval_score:.2f} model_calls={m.calls}")

    # grounded question DOES reach the model
    m = RecordingModel()
    eng = build(model=m)
    r = eng.ask("When is my nephrology follow up?")
    ok = r.type is ResponseType.ANSWER and m.calls == 1 and r.source_chunk is not None
    fails += not ok
    print(f"[{'ok ' if ok else 'FAIL'}] grounded question answered  "
          f"type={r.type.value} score={r.retrieval_score:.2f} model_calls={m.calls}")
    if r.source_chunk:
        print(f"         cited: {r.source_chunk.chunk_id} -> {r.source_chunk.text[:52]}...")

    # model may still decline; the system honours it
    m = RecordingModel(reply="NOT_IN_DOCUMENT")
    eng = build(model=m)
    r = eng.ask("When is my nephrology follow up?")
    ok = r.type is ResponseType.ABSTAIN and r.model_called
    fails += not ok
    print(f"[{'ok ' if ok else 'FAIL'}] model decline honoured      "
          f"type={r.type.value} model_calls={m.calls}")

    # every deferral lands on the handoff list
    m = RecordingModel()
    eng = build(model=m)
    for q in ["Can I restart the metformin?",
              "What is my cholesterol reading?",
              "Should I stop my insulin?"]:
        eng.ask(q)
    ok = len(eng.handoff_list()) == 3 and m.calls == 0
    fails += not ok
    print(f"[{'ok ' if ok else 'FAIL'}] deferrals reach handoff     "
          f"handoff={len(eng.handoff_list())} model_calls={m.calls}")

    # a session with no model configured still refuses and abstains
    eng = build(model=None)
    a = eng.ask("Should I stop taking my medicine?")
    b = eng.ask("What is my cholesterol reading?")
    ok = a.type is ResponseType.REFUSAL and b.type is ResponseType.ABSTAIN
    fails += not ok
    print(f"[{'ok ' if ok else 'FAIL'}] works with no model at all  "
          f"{a.type.value}, {b.type.value}")

    print()
    print("=" * 72)
    total = len(SCOPE_CASES) + 7
    print(f"{total - fails}/{total} passed")
    print("=" * 72)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
