# PlainTalk — Update after the midterm status

**Nick Tran · CPSC 597 · Dr. Chang-Hyun Jo**
11 October 2026

This note is the record of work done after `midterm_status.md`. That file remains the evidence brief for the measured system. This file is what changed afterward, written so the final report can use it. The safety numbers in the midterm brief were not re-run.

The repository is public at https://github.com/nicktran1308/plaintak_final_project. `main` holds the course snapshot plus the changes below. New work continues on `prototype_features`.

## What the midterm brief left open, and what is now done

`midterm_status.md` §10 named four interface findings that a later pass might fix, plus the final write-up. Three of those four findings are now fixed in the patient interface. Unassisted paper intake is not: there is still no camera, and a person alone with a paper sheet still has to type it.

| Midterm finding | Now |
|---|---|
| The refusal card did not say the question was saved | The card adds “Added to the list for your doctor.” / “Đã thêm vào danh sách cho bác sĩ.” when the backend stored the question. An emergency card does not show that line. |
| Faint text and the focus ring failed contrast | Faint labels are `#62747C` (about 4.7:1). The focus ring is `#147A68` (about 5:1). |
| On a phone the question box sat under the whole paper | Under 1000px the question panel is fixed to the bottom of the screen. Wider screens keep it in the side column. |
| A person alone with paper has to type it in | Still true. |

The second-speaker review of the 28 directive terms, and the interface inspection of Personas B and C, are already recorded in the midterm brief. They are not repeated here except for the two glossary wording changes, which the final report should use:

- **do not resume** is `không tiếp tục`. `không dùng lại` stays as an alternative. `không bắt đầu` stays forbidden.
- Before a date, `cho đến khi` is allowed as well as `cho đến`. `trừ khi` stays forbidden.

`resume` stays `uống lại`. Bare `tiếp tục` stays forbidden for that sense.

## Interface changes since the brief

None of these change the safety numbers. They change what the patient sees.

1. **A declined question says it was saved.** The explanation and the saved-list line are separate. Refusal and abstention both show the line, because both are stored for the clinician.
2. **The Vietnamese print button says Print.** `In` is the Vietnamese word for print, and it read as the English word “in.”
3. **The reading-level number is hidden.** The card still shows the level. It no longer shows the Flesch-Kincaid grade. The backend still computes that number. On the metformin line the grade was 6.8 while the line still contained `PO` and `BID`.
4. **The paste button says why it is off.** Until the text is 20 characters, the line under the button is “Need more information.” / “Cần thêm thông tin.”
5. **Start over asks first.** The dialog is in the app. “Keep going” / “Ở lại” is the filled button and takes focus. Confirming clears the paper and the questions.
6. **English passages are marked as English** when the page is Vietnamese: the paragraph, the clinician’s original, and the cited source. The answer stays in the patient’s language.
7. **Lab flags are shown before translation.** On the English text the patient sees first, `HIGH` becomes `CAO (HIGH)`, and the same for `LOW`, `NORMAL`, `ABNORMAL`, `CRITICAL`, `POSITIVE`, and `NEGATIVE`. The original under a simplification stays word for word.
8. **The level chip does not advance when the sentence did not change.** A real wording change still moves the chip.
9. **On a phone the question box stays on screen,** pinned to the bottom.

The build order and the items still ahead are in `../planning/prototype_features.md`.

## What is still open for the final report

These are unchanged from the midterm brief, except where a row above says otherwise.

- **A skipped paragraph in whole-document translation is silent.** `translateAll` leaves a failed paragraph in English and continues, with no reason on the card. That is the next interface item.
- **Bare numerals in a range are now tracked.** `1.5 to 2 L` rounded to `2 to 2 L` is blocked. This was 0 of 3 before the change. The measured table in the midterm brief is the old number.
- **Negation scope is 18.2%.** Set comparison checks that a prohibition is present, not which clause it governs. That limit was deliberate for the semester.
- **The safety numbers are one synthetic discharge sheet.** The translation comparison is 10 paragraphs, run once. Fault injection, not a natural catch rate, is the gate’s 82.4%.
- **The exemplar arm was not tested the way the app runs it.** The evaluation used four fixed pairs, not retrieved ones.
- **Two colloquial Vietnamese permission questions still reach the model.**
- **Final report, demonstration, and presentation.** The weekly reports plus this note are the draft of the evidence. A README at the repository root now says how to install and run the system.

## Where this update lives

| Change | Where |
|---|---|
| Inspection of Personas B and C, and the accessibility check | `../interface/interface_walkthrough.md` §§9–14 |
| Glossary wording | `../../backend/data/glossary_directive_DONE.jsonl` |
| Patient-interface changes | `../../frontend/src/` |
| Build order | `../planning/prototype_features.md` |
| Measured results, unchanged | `midterm_status.md` §§6 and 11 |
