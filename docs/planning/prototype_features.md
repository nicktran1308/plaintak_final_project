# Prototype features

Code-only work that makes the trustworthy-AI claim harder to dismiss. No patient testing, no hospital connection, no new language, no reviewer product.

`main` already includes everything in **Already done**. Work on `prototype_features`. The record of changes since the midterm brief is `../reports/post_midterm_update.md`. The measured system is `../reports/midterm_status.md`. Do not rewrite those safety tables. The 0% rounding figure there is the old measurement.

The claim: a small model plus a verifier that never asks the model whether it told the truth can beat an unchecked model on clinical text. Refusals and abstentions are branches. The gate compares normalized facts to the clinician’s original. The gate checks that a fact is present, not what it governs. Negation flips were caught 18.2% of the time. That boundary is the research topic.

## Build next, in this order

**1. More documents.** Done. Nineteen sheets. The original wording is unchanged. The other 18 are in `eval/synthetic_docs/sheets/`, with facts in `sheets/manifest.jsonl`. The published evals have not been re-run on them.

**2. A test for every known failure.** Next. These run offline with an injected model. Keep the two colloquial misses (`Thuốc này uống được không bác?`, `Chỉ số này có cao lắm không?`), the negation flips, the range-rounding case already in `backend/tests/test_gate.py`, and the back-translation restore bug. After this, a glossary or prompt change cannot silently break a cited result.

**3. Negation scope, without medspaCy.** Do not install medspaCy. It broke the pinned clinical stack once. A negation or a duration has to stay attached to the same instruction. “Avoid strenuous exertion for 7 days” rewritten as “Do not do hard exercise. Do not do heavy activity for 7 days” should fail, because the 7 days moved. Re-run the fault-injection set and report the new rate next to 18.2%. This is the result to lead with.

**4. Separate the two abstention layers.** At threshold 0.30, 47 of 159 abstentions were the model declining after retrieval. The others never called the model. Report both in every table. Then run the same question set through a second model with the same gate. State whether the zero false-answer rate depends on the model obeying.

**5. Exemplars the way the app uses them.** The evaluation inserted four unrelated pairs. The app retrieves similar pairs. Run naive, placeholders only, and retrieved exemplars on the new sheets. Draw a conclusion only after that.

**6. A verdict object.** For every blocked sentence, record which entity is missing, altered, or attached to the wrong clause, and the span. The interface, the tests, and the report should all read that object. Interpretable verification is the contribution.

## Already done

Do not rebuild these. Details are in `../reports/post_midterm_update.md`.

1. Refusal and abstention cards say the question was saved. Emergency cards do not.
2. The reading-level grade is hidden. The level chip remains.
3. The paste button says “Need more information.” / “Cần thêm thông tin.” until 20 characters.
4. Start over asks first, inside the app.
5. Faint text is `#62747C`. The focus ring is `#147A68`.
6. English passages carry `lang="en"` when the page is Vietnamese.
7. `HIGH` becomes `CAO (HIGH)` on the English text shown first, and the same for `LOW`, `NORMAL`, `ABNORMAL`, `CRITICAL`, `POSITIVE`, and `NEGATIVE`.
8. The level chip stays still when the new sentence matches the one on the card.
9. Under 1000px the question panel is fixed to the bottom of the screen.
10. A bare number in a range inherits the unit. `1.5 to 2 L` rounded to `2 to 2 L` blocks. Gate tests: 24 of 24.
11. The Vietnamese print button says Print, not `In`.
12. Nineteen synthetic discharge sheets. Original wording is unchanged. Facts are in `eval/synthetic_docs/sheets/manifest.jsonl`. The published evals have not been re-run on the new sheets.

One interface gap is still open and is not part of the research order: `translateAll` in `frontend/src/App.jsx` leaves a failed paragraph in English and does not say so on the card. Fix it only if a demo of whole-document translation needs it.
