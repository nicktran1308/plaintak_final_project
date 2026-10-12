# Prototype features

What to build on the `prototype_features` branch. `main` stays the course snapshot.

Sorted by what is worth doing and what is practical in this codebase. The longer catalog is `plaintalk-startup-roadmap.md` in this folder. This list is the build order.

## Start here

The first upgrade is a batch of small interface fixes. Each one is hours of work in files that already exist. None of them change the safety numbers. Do them in this order.

1. **Say that a refused question was saved.** Done. When the backend stores the question (`added_to_handoff`), the coral card adds one line: “Added to the list for your doctor.” / “Đã thêm vào danh sách cho bác sĩ.” The line is in `Deferred.jsx`, the words are in `i18n.js`, and `Chat.jsx` passes the line only when the backend set the flag. An emergency card does not show it, so that card stays on calling for help. Refusal and abstention both show it, because both are stored on the clinician list.

2. **Stop showing the reading-level number to the patient.** Done. The card still shows the level. It no longer prints the Flesch-Kincaid grade. The backend still computes that number; the patient view in `Paragraph.jsx` does not display it.

3. **Say why the paste button is disabled.** Done. Until the pasted text is 20 characters, `Upload.jsx` shows a short line under the button: “Need more information.” / “Cần thêm thông tin.” The line goes away once the button turns on.

4. **Ask before Start over.** Done. One press opens a dialog in the app, not a system window. “Keep going” / “Ở lại” is the filled button and takes focus. “Start over” clears the paper and the questions. Escape or a tap outside the dialog closes it.

5. **Fix the faint text and the focus ring.** Done. `--ink-faint` is `#62747C` (about 4.7:1 on the page; the old `#8A9BA1` was about 2.8:1). `--sea`, the focus ring, is `#147A68` (about 5:1; the old `#00A896` was about 2.9:1).

6. **Mark English passages as English.** Done. When the page is Vietnamese, the paragraph, the clinician’s original, and the cited source carry `lang="en"`. The answer itself stays in the patient’s language. `Chat.jsx` passes the page language into `Answer.jsx`.

7. **Show flag words before the patient asks for a translation.** Done. `HIGH` becomes `CAO (HIGH)`, and the same for `LOW`, `NORMAL`, `ABNORMAL`, `CRITICAL`, `POSITIVE`, and `NEGATIVE`, on the English text shown first. The clinician’s original underneath a simplification stays word for word.

8. **Say when whole-document translation skipped a paragraph.** `translateAll` in `App.jsx` leaves a failed paragraph in English and continues. Show a short reason on that card.

9. **Do not advance the level when the text did not change.** Done. `Paragraph.jsx` compares the new sentence with the one on the card. When they match, the level chip and the text stay. The gate result and whether another press is allowed still update.

10. **On a phone, keep the question box reachable.** Done. Under 1000px the question panel is fixed to the bottom of the screen, with the paper padded so the last paragraph can scroll clear of it. Wider screens keep the panel in the side column.

Do items 1 through 7 as one batch. They are hours each. Items 8 through 10 are about a day each.

## First safety change

11. **Track bare numerals next to a unit.** Done. In a range such as `1.5 to 2 L`, the first number inherits the unit. Rounding it to `2 to 2 L` now blocks. A faithful `1.5 to 2 liters` still passes. The cases are in `backend/tests/test_gate.py`.

## Make the numbers defensible

Do this before building a new screen. The current safety numbers are one synthetic discharge sheet, and the translation result is 10 paragraphs run once.

12. **More discharge sheets.** `eval/synthetic_docs/make_doc_pdf.py` already builds one sheet. Generate 15 to 20 more with different drugs, doses, dates, and negations. A few days of authoring. This is the highest-value evidence work because the generator already exists.

13. **Run the translation arms more than once.** Repeat naive, protected, and full several times. Report a range. A few days, plus API cost. One run of 10 paragraphs is too thin to stand on.

14. **Turn known failures into tests.** The colloquial misses (`Thuốc này uống được không bác?`, `Chỉ số này có cao lắm không?`), the rounding cases, the negation cases, and the back-translation restore bug. The test files already accept an injected model, so these can run offline. About a week. After this, a glossary or prompt change cannot silently break a known case.

## First product surface

Do this after the batch above. It is the first thing a hospital would pay for. It is weeks, not hours.

15. **A warning on text a person has not reviewed.** One banner. Small, and it matches the expectation that machine translation of a critical document is reviewed by a person.

16. **A reviewer view.** One screen with the original, the simplification, the translation, and the back-translation. The gate’s reason sits on the sentence that failed. The reviewer approves, edits, or rejects that flag and signs the document. Record minutes per document. That number is what the product can sell. The patient app already shows the original and the gate badge. This view is the same information arranged for a reviewer.

17. **Hide identity the way doses are hidden.** Name, date of birth, and record number should be placeholders before the model sees the text. Intake already treats some of those lines as headers. Extending that is days to a week once the fields are listed.

## Safety work that is not the first task

18. **Negation scope.** This is the weakest measured behavior, at 18.2%, and it is the harm class in the literature this project cites. It is not the first build. Installing medspaCy’s ConText tool broke the pinned clinical stack once already. A narrower check that pairs a negation with its own clause, without that dependency, is the practical version. Do it after the regression tests exist, so the current 18.2% cases cannot silently get worse.

19. **Run the exemplar arm the way the app runs it.** The app retrieves similar pairs. The evaluation inserted four pairs from the top of the file. No conclusion was drawn. Re-run that arm with retrieval before claiming that examples help or hurt.

## After a clinic is using it

Do not build these until someone asks. The order below is the order to offer them.

20. **Warning banner** on any translation a person has not signed. Small, and it belongs on the reviewer view once that view exists.
21. **Minutes per document** on the reviewer view. That is the number a buyer can compare with professional translation.
22. **Side-by-side PDF** of both languages, for a nurse to hand over with the English original.
23. **A link or QR code** on the printed sheet that opens the translated version on a phone.
24. **Large print.** The type is already 20px and 22px. A second text size is a stylesheet change.
25. **A medication checklist** drawn from the entities the gate already extracts, such as “HOLD metformin until 11/14.”
26. **Audio** of the Vietnamese text, checked by a native speaker before it is offered.
27. **Spanish** as the second language, after the Vietnamese numbers are repeated on more than one sheet. Each language needs its own glossary, its own forbidden renderings, and a second native speaker.

## Do not build yet

Electronic health record integration, single sign-on, SOC 2, text-message reminders, caregiver accounts, teach-back alerts, pediatric mode, fax intake, and a public API. Consent forms, end-of-life discussions, and behavioral health stay with a human interpreter. Do not add advice or recommendations. That changes what the product is allowed to be.

## First thing to build

Items 1 through 7 and 9 through 11 are done. Next is item 8, saying when a whole-document translation skipped a paragraph. Then more discharge sheets and the regression tests. The reviewer view comes after those, because it is the first new screen and it should sit on numbers that hold up.
