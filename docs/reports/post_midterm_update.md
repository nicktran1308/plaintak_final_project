# PlainTalk — Update after the midterm status

**Nick Tran · CPSC 597 · Dr. Chang-Hyun Jo**
16 October 2026

This note is the record of work done after `midterm_status.md`. That file remains the evidence brief for the measured system. This file is what changed afterward, written so the final report and a new working session can use it. The safety tables in the midterm brief were not re-run, except the one new gate case below.

The repository is public at https://github.com/nicktran1308/plaintak_final_project. `main` and `prototype_features` are at the same commit as of this note. New work continues on `prototype_features`. The build order is `../planning/prototype_features.md`. The next item there is number 8.

## What the midterm brief left open, and what is now done

`midterm_status.md` §10 named four interface findings that a later pass might fix. Three are fixed. Unassisted paper intake is not: there is still no camera, and a person alone with a paper sheet still has to type it.

| Midterm finding | Now |
|---|---|
| The refusal card did not say the question was saved | The card adds “Added to the list for your doctor.” / “Đã thêm vào danh sách cho bác sĩ.” when the backend stored the question. An emergency card does not show that line. |
| Faint text and the focus ring failed contrast | Faint labels are `#62747C` (about 4.7:1). The focus ring is `#147A68` (about 5:1). |
| On a phone the question box sat under the whole paper | Under 1000px the question panel is fixed to the bottom of the screen. Wider screens keep it in the side column. |
| A person alone with paper has to type it in | Still true. |

The second-speaker review of the 28 directive terms, and the interface inspection of Personas B and C, are already recorded in the midterm brief. Two glossary wording changes belong in the final report:

- **do not resume** is `không tiếp tục`. `không dùng lại` stays as an alternative. `không bắt đầu` stays forbidden.
- Before a date, `cho đến khi` is allowed as well as `cho đến`. `trừ khi` stays forbidden.

`resume` stays `uống lại`. Bare `tiếp tục` stays forbidden for that sense.

## Changes since the brief

### What the patient sees

None of these change the published safety tables.

1. **A declined question says it was saved.** Refusal and abstention both show the line, because both are stored for the clinician. An emergency card does not.
2. **The Vietnamese print button says Print.** `In` is the Vietnamese word for print, and it read as the English word “in.”
3. **The reading-level number is hidden.** The card still shows the level. It no longer shows the Flesch-Kincaid grade. The backend still computes that number. On the metformin line the grade was 6.8 while the line still contained `PO` and `BID`.
4. **The paste button says why it is off.** Until the text is 20 characters, the line under the button is “Need more information.” / “Cần thêm thông tin.”
5. **Start over asks first.** The dialog is in the app. “Keep going” / “Ở lại” is the filled button and takes focus. Confirming clears the paper and the questions.
6. **English passages are marked as English** when the page is Vietnamese: the paragraph, the clinician’s original, and the cited source. The answer stays in the patient’s language.
7. **Lab flags are shown before translation.** On the English text the patient sees first, `HIGH` becomes `CAO (HIGH)`, and the same for `LOW`, `NORMAL`, `ABNORMAL`, `CRITICAL`, `POSITIVE`, and `NEGATIVE`. The original under a simplification stays word for word.
8. **The level chip does not advance when the sentence did not change.** A real wording change still moves the chip.
9. **On a phone the question box stays on screen,** pinned to the bottom.

### One safety change

**Bare numerals in a range are tracked.** In `1.5 to 2 L`, the first number now inherits the unit. Rounding it to `2 to 2 L` blocks. A faithful `1.5 to 2 liters` still passes. Before this change that rounding was caught 0 of 3 times. The 0% figure in `midterm_status.md` §6.2 is the old measurement. The new cases are `rounded range` and `range preserved` in `backend/tests/test_gate.py`. The gate tests are 24 of 24. The fault-injection table was not re-run.

## What is still open

- **A skipped paragraph in whole-document translation is silent.** `translateAll` in `frontend/src/App.jsx` leaves a failed paragraph in English and continues, with no reason on the card. That is the next build.
- **Negation scope is 18.2%.** Set comparison checks that a prohibition is present, not which clause it governs. That limit was deliberate for the semester. Do not install medspaCy to fix it. That install broke the pinned clinical stack once already.
- **The safety numbers are one synthetic discharge sheet.** The translation comparison is 10 paragraphs, run once. Fault injection, not a natural catch rate, is the gate’s 82.4%.
- **The exemplar arm was not tested the way the app runs it.** The evaluation used four fixed pairs, not retrieved ones.
- **Two colloquial Vietnamese permission questions still reach the model:** `Thuốc này uống được không bác?` and `Chỉ số này có cao lắm không?`
- **Final report, demonstration, and presentation.** The weekly reports plus this note are the draft of the evidence. A README at the repository root says how to install and run the system.

## Where this update lives

| Change | Where |
|---|---|
| Inspection of Personas B and C, and the accessibility check | `../interface/interface_walkthrough.md` §§9–14 |
| Glossary wording | `../../backend/data/glossary_directive_DONE.jsonl` |
| Patient-interface changes | `../../frontend/src/` |
| Range-numeral check | `../../backend/pipeline/gate.py`, `../../backend/tests/test_gate.py` |
| What to build next | `../planning/prototype_features.md` |
| Measured results, except the new range case | `midterm_status.md` §§6 and 11 |
