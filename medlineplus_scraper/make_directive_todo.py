#!/usr/bin/env python3
"""
Scaffold the hand-authored directive tier of the glossary.

The mined tier is built from patient-education prose, which contains almost no
medication instruction language: the exemplar corpus has zero records matching
any dosing frequency and single digits for dosage units. These terms therefore
cannot be mined and must be authored by a Vietnamese-speaking clinician and
verified independently by a second speaker.

Every row is emitted with an EMPTY vi field on purpose. Guessing a directive
translation and presenting it for review anchors the reviewer on the guess,
which is exactly the wrong failure mode for medication instructions.

Each row carries english_context explaining the intended sense, so the second
reviewer knows what is being asked without needing the source conversation.

Usage:
    python make_directive_todo.py
"""

import json
import re
from pathlib import Path

OUT = Path("medlineplus-vi")

# (english term, sense id, gloss, english_context, require_any, safety_critical,
#  do_not_use)
TERMS = [
    (
        "hold", "hold.medication",
        "to stop taking a medication, temporarily",
        "A clinician instructing the patient to STOP a medication, usually "
        "before a procedure, test, or because of a lab result. It does NOT mean "
        "grasp, support, or continue. This is the highest-risk entry in the "
        "glossary: Kong et al. 2026 documented clinical harm when 'hold the "
        "kidney medicine' was understood as 'keep taking it'. The corpus "
        "contains only the physical sense (hold a crutch, hold a spray), mined "
        "as hold.physical -> 'giữ', so there is no corpus evidence for this "
        "sense and it must be authored from clinical knowledge.",
        ["medicine", "medication", "dose", "pill", "tablet", "capsule", "insulin"],
        True, "giữ",
    ),
    (
        "stop taking", "stop_taking.1",
        "to cease a medication, generally permanently or until told otherwise",
        "Distinguish from 'hold', which implies a temporary pause. Note the "
        "corpus renders 'Do not stop taking your medicine' as 'Không ngưng "
        "thuốc', which suggests 'ngưng' for the verb, but that is a single "
        "observation and should be confirmed, not assumed.",
        ["medicine", "medication", "pill", "tablet", "dose"], True, None,
    ),
    (
        "keep taking", "keep_taking.1",
        "to continue a medication that is already started",
        "The direct opposite of 'hold' and 'stop taking'. Because these are "
        "opposites that appear in similar sentence frames, the Vietnamese "
        "renderings must be unmistakably distinct from one another.",
        ["medicine", "medication", "pill", "tablet", "dose"], True, None,
    ),
    (
        "continue", "continue.medication",
        "to carry on with a medication or treatment course",
        "Medication sense only. The corpus uses 'continue' mostly in a general "
        "prose sense (continue giving breaths, continue to wash), so any mined "
        "rendering will reflect that and should not be reused here.",
        ["medicine", "medication", "treatment", "dose"], True, None,
    ),
    (
        "resume", "resume.1",
        "to restart a medication that was previously held or stopped",
        "Follows a hold. The patient must understand that restarting is now "
        "authorised. Must be clearly distinct from 'continue', which implies "
        "the medication was never interrupted.",
        ["medicine", "medication", "dose"], True, None,
    ),
    (
        "do not resume", "do_not_resume.1",
        "an instruction not to restart a held or stopped medication",
        "A negated directive. Vietnamese negation placement matters here; the "
        "phrase must not be readable as permission to restart. Worth testing "
        "the authored wording by back-translation.",
        ["medicine", "medication", "dose"], True, None,
    ),
    (
        "as needed", "as_needed.1",
        "take only when symptoms require it, not on a schedule (PRN)",
        "The patient must understand this is optional and symptom-triggered, "
        "not a missed scheduled dose. A rendering that reads as 'when "
        "necessary' in a vague sense may cause under- or over-use.",
        ["take", "dose", "medicine", "medication"], True, None,
    ),
    (
        "before meals", "before_meals.1",
        "take on a schedule relative to eating, prior to a meal",
        "Timing qualifier. Clinically distinct from 'on an empty stomach', "
        "which specifies a required gap. If Vietnamese usage conflates the two, "
        "flag it rather than choosing.",
        ["take", "dose", "medicine"], False, None,
    ),
    (
        "after meals", "after_meals.1",
        "take on a schedule relative to eating, following a meal",
        "Timing qualifier. Often used to reduce stomach upset.",
        ["take", "dose", "medicine"], False, None,
    ),
    (
        "with food", "with_food.1",
        "take together with food, to aid absorption or reduce irritation",
        "Distinct from 'after meals': 'with food' means concurrent, not "
        "subsequent. If the natural Vietnamese phrasing does not preserve that "
        "distinction, note it.",
        ["take", "dose", "medicine"], False, None,
    ),
    (
        "on an empty stomach", "empty_stomach.1",
        "take with no food for a defined period before and/or after",
        "Usually implies a specific interval (commonly one hour before or two "
        "hours after eating). Consider whether the Vietnamese should state the "
        "interval explicitly rather than rely on an idiom.",
        ["take", "dose", "medicine"], True, None,
    ),
    (
        "until", "until.1",
        "continue up to a stated endpoint, then stop",
        "Appears in 'take until finished' and 'until the bottle is empty'. The "
        "endpoint is the load-bearing part; a rendering that reads as 'for a "
        "while' loses the instruction.",
        ["take", "dose", "medicine", "finish"], True, None,
    ),
    (
        "twice daily", "twice_daily.1",
        "two doses in each 24-hour period",
        "The exemplar corpus contains ZERO records for any dosing frequency, so "
        "there is no corpus evidence whatsoever for this term or the three that "
        "follow. Consider whether spacing should be stated (roughly 12 hours "
        "apart) rather than left implicit.",
        ["take", "dose", "medicine"], True, None,
    ),
    (
        "once daily", "once_daily.1",
        "one dose in each 24-hour period",
        "No corpus evidence. Consider whether a fixed time of day should be "
        "recommended in the rendering.",
        ["take", "dose", "medicine"], True, None,
    ),
    (
        "three times daily", "three_times_daily.1",
        "three doses in each 24-hour period",
        "No corpus evidence. Must not be confusable with 'every three hours'.",
        ["take", "dose", "medicine"], True, None,
    ),
    (
        "every N hours", "every_n_hours.1",
        "dose at a fixed interval, where N is a number supplied at runtime",
        "This is a PATTERN, not a fixed string: N is a numeric slot filled per "
        "prescription. Please author it with an explicit placeholder so code can "
        "substitute the number, and check that Vietnamese word order still reads "
        "correctly for both single and double digit values. Contrast carefully "
        "with 'three times daily', which is not the same instruction.",
        ["take", "dose", "medicine", "hours"], True, None,
    ),
    (
        "at bedtime", "at_bedtime.1",
        "take once, shortly before sleeping",
        "Time-of-day qualifier, not a frequency. Should not imply an additional "
        "dose beyond the prescribed schedule.",
        ["take", "dose", "medicine"], False, None,
    ),
    (
        "as directed", "as_directed.1",
        "follow the instructions given separately by the prescriber",
        "A deferral, not an instruction. The rendering must not read as 'take "
        "as you see fit', which inverts the meaning into patient discretion.",
        ["take", "dose", "medicine"], True, None,
    ),
    (
        "mg", "unit_mg.1", "milligram, a unit of medication mass",
        "Decide and record whether units stay in Latin script (mg) or are "
        "localised, and apply that decision consistently across mg, ml, mcg and "
        "units. The corpus shows Latin script retained, e.g. '1000 mg of "
        "calcium' -> '1000 (mg) canxi', but that is only 9 records and includes "
        "inconsistent parenthesisation.",
        [], True, None,
    ),
    (
        "ml", "unit_ml.1", "millilitre, a unit of liquid volume",
        "Same script decision as mg. Particularly important for liquid "
        "medicines dosed with a syringe or spoon, where a misread volume is a "
        "direct overdose risk.",
        [], True, None,
    ),
    (
        "mcg", "unit_mcg.1", "microgram, a unit of medication mass",
        "One thousandth of a milligram. If the rendering is visually close to "
        "the mg rendering, say so: confusion between the two is a 1000-fold "
        "dosing error.",
        [], True, None,
    ),
    (
        "units", "unit_units.1",
        "international units, used for insulin and some other drugs",
        "The corpus contains insulin syringe text using 'đơn vị'. Confirm "
        "whether that is the right rendering in a dosing instruction as opposed "
        "to a description of syringe markings.",
        ["insulin", "dose", "syringe"], True, None,
    ),
    (
        "tablet", "tablet.1", "a solid oral dose form, pressed",
        "Distinguish from capsule if Vietnamese usage distinguishes them; if it "
        "does not, flag that rather than forcing a distinction.",
        ["take", "dose", "medicine"], False, None,
    ),
    (
        "capsule", "capsule.1", "a solid oral dose form, shell-encased",
        "See tablet. Relevant because some capsules must not be opened or "
        "crushed.",
        ["take", "dose", "medicine"], False, None,
    ),
    (
        "dose", "dose.1", "one administration of a medication",
        "The countable unit that 'skip a dose' and 'double dose' operate on, so "
        "this rendering must compose naturally with those two entries.",
        ["take", "medicine", "medication"], True, None,
    ),
    (
        "refill", "refill.1",
        "obtain a further supply of an existing prescription",
        "Both a noun and a verb in English. Note which the Vietnamese covers; if "
        "two renderings are needed, author both as separate senses.",
        ["prescription", "medicine", "pharmacy"], False, None,
    ),
    (
        "skip a dose", "skip_a_dose.1", "omit one scheduled administration",
        "Must be clearly distinct from stopping the medication entirely. A "
        "patient who reads this as 'stop' will discontinue treatment.",
        ["dose", "medicine", "medication"], True, None,
    ),
    (
        "double dose", "double_dose.1",
        "two doses at once, usually in the context of an instruction NOT to",
        "Almost always appears as a prohibition ('do not take a double dose to "
        "make up for a missed one'). Author the term so it composes correctly "
        "with negation.",
        ["dose", "medicine", "medication"], True, None,
    ),
]


def corpus_support(term, records):
    """How many exemplar records and distinct documents mention this term."""
    if term == "every N hours":
        pat = re.compile(r"\bevery\s+\d+\s*(to|-)?\s*\d*\s*hours?\b", re.I)
    else:
        pat = re.compile(r"\b" + re.escape(term) + r"\b", re.I)
    hits = [r for r in records if pat.search(r["en"])]
    return len(hits), len({r["id"] for r in hits})


def main():
    src = OUT / "pairs_exemplars.jsonl"
    records = [json.loads(l) for l in src.open(encoding="utf-8")] if src.exists() else []

    rows = []
    for en, sid, gloss, ctx, require, critical, avoid in TERMS:
        occ, docs = corpus_support(en, records)
        sense = {
            "sense_id": sid,
            "tier": "hand_authored",
            "status": "todo",
            "gloss": gloss,
            "english_context": ctx,
            "context": {
                "rule": "requires" if require else "default",
                "require_any": require,
                "exclude_any": [],
            },
            "vi": "",
            "vi_alternatives": [],
            "authored_by": "",
            "verified_by": "",
            "reviewer_notes": "",
            "corpus_support": {
                "occurrences": occ,
                "distinct_docs": docs,
                "note": "Counts English string matches in pairs_exemplars.jsonl, "
                        "NOT matches of the sense described above. 'hold' scores "
                        "71 here and none of them are the medication sense. Treat "
                        "a non-zero count as a place to look, not as evidence.",
            },
        }
        if avoid:
            sense["do_not_use"] = [avoid]
        rows.append({
            "en": en,
            "needs_review": True,
            "safety_critical": critical,
            "senses": [sense],
        })

    dest = OUT / "glossary_directive_TODO.jsonl"
    with dest.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    zero = [r["en"] for r in rows
            if r["senses"][0]["corpus_support"]["occurrences"] == 0]
    print(f"wrote {dest}")
    print(f"  terms to author: {len(rows)}")
    print(f"  safety_critical: {sum(1 for r in rows if r['safety_critical'])}")
    print(f"  all vi fields empty: {all(r['senses'][0]['vi'] == '' for r in rows)}")
    print(f"\n  terms with ZERO corpus support ({len(zero)} of {len(rows)}):")
    for t in zero:
        print(f"    {t}")
    print("\n  terms with some corpus support (occurrences / distinct docs):")
    for r in rows:
        cs = r["senses"][0]["corpus_support"]
        if cs["occurrences"]:
            print(f"    {r['en']:22s} {cs['occurrences']:4d} / {cs['distinct_docs']}")


if __name__ == "__main__":
    main()
