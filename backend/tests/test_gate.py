#!/usr/bin/env python3
"""
Gate tests. Each case is a documented failure mode from the literature or a
faithful rewrite that MUST be allowed through.

Run:  python test_gate.py
No API key and no scispaCy required; the regex core covers every case here.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from pipeline.gate import check_simplification, check_translation, extract_entities

NER = False  # regex core only, so tests run anywhere

SRC = "Hold metformin 500 mg PO BID until you follow up with nephrology on 11/14."

# (name, source, output, should_pass, why)
SIMPLIFY_CASES = [
    ("faithful rewrite", SRC,
     "Stop taking metformin 500 mg by mouth two times a day until you see the "
     "kidney doctor on 11/14.",
     True, "BID -> two times a day must normalize to the same entity"),

    ("dropped dose", SRC,
     "Stop taking metformin two times a day until you see the kidney doctor on 11/14.",
     False, "Srinivasu et al: dose silently dropped"),

    ("dropped frequency", SRC,
     "Stop taking metformin 500 mg until you see the kidney doctor on 11/14.",
     False, "frequency lost"),

    ("altered dose", SRC,
     "Stop taking metformin 50 mg two times a day until 11/14.",
     False, "500 -> 50 is a tenfold error"),

    ("dropped date", SRC,
     "Stop taking metformin 500 mg two times a day until your next visit.",
     False, "follow-up date lost"),

    ("date written out", SRC,
     "Stop taking metformin 500 mg by mouth two times a day until November 14.",
     True, "November 14 and 11/14 are the same date"),

    ("negation removed",
     "Do not take this medicine with alcohol.",
     "Take this medicine with alcohol.",
     False, "polarity reversed, the most dangerous simplification error"),

    ("negation reworded",
     "Do not take this medicine with alcohol.",
     "Avoid alcohol while taking this medicine.",
     True, "avoid preserves the prohibition"),

    ("invented dose",
     "Take your blood pressure medicine as directed.",
     "Take your blood pressure medicine 20 mg once a day.",
     False, "Makhmutova et al: fabricated detail not present in source"),

    ("every 12 hours normalizes", SRC,
     "Stop taking metformin 500 mg by mouth every 12 hours until 11/14.",
     True, "every 12 hours == BID"),

    ("lab value preserved",
     "Your fasting glucose was 126 mg/dL, above the normal range of 70 to 100 mg/dL.",
     "Your fasting blood sugar was 126 mg/dL. Normal is 70 to 100 mg/dL.",
     True, "all three values carried over"),

    ("lab value dropped",
     "Your fasting glucose was 126 mg/dL, above the normal range of 70 to 100 mg/dL.",
     "Your fasting blood sugar was high.",
     False, "numbers replaced with a vague word"),

    ("duration preserved",
     "Avoid strenuous exercise for 7 days.",
     "Do not do hard exercise for 7 days.",
     True, "duration and negation both survive"),

    ("insulin units", "Inject 18 units of insulin glargine at bedtime.",
     "Inject 18 units of insulin glargine at bedtime.",
     True, "identity case"),

    ("units dropped", "Inject 18 units of insulin glargine at bedtime.",
     "Inject your insulin at bedtime.",
     False, "dose lost"),

    ("rounded range",
     "Drink approximately 1.5 to 2 L daily.",
     "Drink approximately 2 to 2 L daily.",
     False, "Picton et al: the bare end of a range was rounded"),

    ("range preserved",
     "Drink approximately 1.5 to 2 L daily.",
     "Drink about 1.5 to 2 liters each day.",
     True, "both ends of the range survive; L expands to liters"),
]

# (name, source_en, output_vi, back_en, glossary, should_pass, why)
GLOSSARY = {
    "hold": {"vi": "ngưng", "do_not_use": ["giữ"],
             "note": "medication sense means STOP"},
}

TRANSLATE_CASES = [
    ("good translation", SRC,
     "Ngưng dùng metformin 500 mg uống hai lần mỗi ngày cho đến khi tái khám ngày 14/11.",
     "Stop taking metformin 500 mg by mouth two times a day until your follow-up on 11/14.",
     GLOSSARY, True, "entities intact, correct sense of hold"),

    ("Kong et al harm case", SRC,
     "Giữ metformin 500 mg uống hai lần mỗi ngày cho đến khi tái khám ngày 14/11.",
     "Keep taking metformin 500 mg by mouth two times a day until your follow-up on 11/14.",
     GLOSSARY, False, "hold -> giu inverts the instruction; forbidden rendering"),

    ("dose dropped in translation", SRC,
     "Ngưng dùng metformin uống hai lần mỗi ngày cho đến khi tái khám ngày 14/11.",
     "Stop taking metformin by mouth two times a day until your follow-up on 11/14.",
     GLOSSARY, False, "500 mg absent from the Vietnamese"),

    ("negation lost in back-translation",
     "Do not take this medicine with alcohol.",
     "Uống thuốc này với rượu.",
     "Take this medicine with alcohol.",
     None, False, "meaning reversed, caught by back-translation"),

    ("no back-translation supplied", SRC,
     "Ngưng dùng metformin 500 mg uống hai lần mỗi ngày cho đến khi tái khám ngày 14/11.",
     None, GLOSSARY, True, "literal check alone passes; noted in reasons"),

    ("do not resume reviewed rendering",
     "Do not resume metformin 500 mg.",
     "không tiếp tục metformin 500 mg.",
     "Do not resume metformin 500 mg.",
     {"resume": {"vi": "uống lại", "do_not_use": ["tiếp tục"]},
      "do not resume": {"vi": "không tiếp tục", "do_not_use": ["không bắt đầu"]}},
     True, "không tiếp tục is the reviewed form; it must not be read as bare resume"),

    ("resume rendered as continue",
     "Resume metformin 500 mg.",
     "tiếp tục metformin 500 mg.",
     "Continue metformin 500 mg.",
     {"resume": {"vi": "uống lại", "do_not_use": ["tiếp tục"]}},
     False, "bare resume must not be rendered as tiếp tục"),
]


def main() -> int:
    fails = 0

    print("=" * 72)
    print("SIMPLIFICATION")
    print("=" * 72)
    for name, src, out, want, why in SIMPLIFY_CASES:
        v = check_simplification(src, out, use_ner=NER)
        ok = v.passed == want
        fails += not ok
        print(f"[{'ok ' if ok else 'FAIL'}] {name:28} expect "
              f"{'PASS' if want else 'BLOCK':5} got {'PASS' if v.passed else 'BLOCK'}")
        if not ok or not v.passed:
            print(f"         why: {why}")
            for r in v.reasons:
                print(f"         gate: {r}")

    print()
    print("=" * 72)
    print("TRANSLATION")
    print("=" * 72)
    for name, src, vi, back, gloss, want, why in TRANSLATE_CASES:
        v = check_translation(src, vi, back, glossary=gloss, use_ner=NER)
        ok = v.passed == want
        fails += not ok
        print(f"[{'ok ' if ok else 'FAIL'}] {name:28} expect "
              f"{'PASS' if want else 'BLOCK':5} got {'PASS' if v.passed else 'BLOCK'}")
        if not ok or not v.passed:
            print(f"         why: {why}")
            for r in v.reasons:
                print(f"         gate: {r}")

    total = len(SIMPLIFY_CASES) + len(TRANSLATE_CASES)
    print()
    print("=" * 72)
    print(f"{total - fails}/{total} passed")
    print("=" * 72)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
