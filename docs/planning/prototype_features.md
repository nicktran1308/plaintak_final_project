# Prototype features

What to build on the `prototype_features` branch. `main` stays the course snapshot.

Sorted by what is worth doing and what is practical in this codebase. The longer catalog is `plaintalk-startup-roadmap.md` in this folder. This list is the build order.

## Start here

The first upgrade is a batch of small interface fixes. Each one is hours of work in files that already exist. None of them change the safety numbers. Do them in this order.

1. **Say that a refused question was saved.** Done. When the backend stores the question (`added_to_handoff`), the coral card adds one line: “Added to the list for your doctor.” / “Đã thêm vào danh sách cho bác sĩ.” The line is in `Deferred.jsx`, the words are in `i18n.js`, and `Chat.jsx` passes the line only when the backend set the flag. An emergency card does not show it, so that card stays on calling for help. Refusal and abstention both show it, because both are stored on the clinician list.

2. **Stop showing the reading-level number to the patient.** Done. The card still shows the level. It no longer prints the Flesch-Kincaid grade. The backend still computes that number; the patient view in `Paragraph.jsx` does not display it.

3. **Say why the paste button is disabled.** Done. Until the pasted text is 20 characters, `Upload.jsx` shows a short line under the button: “Need more information.” / “Cần thêm thông tin.” The line goes away once the button turns on.

4. **Ask before Start over.** `App.jsx` drops the session on one press. Add a confirmation. On a phone that button is in thumb range.

5. **Fix the faint text and the focus ring.** In `frontend/src/styles.css`, `--ink-faint` is about 2.8:1 and the focus color is about 2.9:1. Both fail the accessibility check. Change the two tokens. Body text and the 48px buttons already pass.

6. **Mark English passages as English.** On the paragraph, the original panel, and the citation, set `lang="en"` when the surrounding page is Vietnamese. Screen readers otherwise pronounce the dose line as Vietnamese. This is a few attributes in `Paragraph.jsx` and `Answer.jsx`.

7. **Show flag words before the patient asks for a translation.** `markFlags` in `Paragraph.jsx` already maps `HIGH` to `CAO (HIGH)` and the same for `LOW` and a few others. It runs only on the Vietnamese string after a translation exists. Run it on the English text the patient sees first.

8. **Say when whole-document translation skipped a paragraph.** `translateAll` in `App.jsx` leaves a failed paragraph in English and continues. Show a short reason on that card.

9. **Do not advance the level when the text did not change.** On the measured discharge sheet, five of ten paragraphs were identical at levels 1 and 2. The chip still increments, so the press looks like a failure. Compare the new text to the current text in `Paragraph.jsx` and keep the chip still when they match.

10. **On a phone, keep the question box reachable.** Under 1000px, `App.jsx` stacks the question panel under every paragraph. Add a jump link, or pin the ask box. This is one or two days, and it is the layout the phone persona cannot use.

Do items 1 through 7 as one batch. They are hours each. Items 8 through 10 are about a day each.

## First safety change

11. **Track bare numerals next to a unit.** Rounding `1.5 to 2 L` to `2 to 2 L` was caught 0 of 3 times. A number becomes an entity only when a unit is attached, so the first value in a range is invisible. The extraction is in `extract_entities` in `backend/pipeline/gate.py`. Add a case to `backend/tests/test_gate.py`. This is one or two days, and it is the easy safety fix to do before any larger gate work.

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

Items 1 through 3 are done. Next is item 4, asking before Start over. Then items 5 through 7. Then bare numerals. Then more discharge sheets and the regression tests. The reviewer view comes after those, because it is the first new screen and it should sit on numbers that hold up.
