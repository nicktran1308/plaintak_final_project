# Prototype features — what is left

Work on the `prototype_features` branch. `main` is the snapshot that already includes everything marked done below. Do not redo the done items.

The longer product catalog is `plaintalk-startup-roadmap.md` in this folder. This file is the build order. The record of what changed after the midterm brief is `../reports/post_midterm_update.md`.

## Next

**8. Say when whole-document translation skipped a paragraph.** `translateAll` in `frontend/src/App.jsx` walks every paragraph. If the gate does not pass, or the call throws, that paragraph stays in English and the run continues. Nothing on the card says it was skipped. Show a short reason on that card, in English and Vietnamese (`frontend/src/i18n.js`). One failure must still not stop the rest of the document.

## After that

Do these before building a new screen. The current safety numbers are one synthetic discharge sheet, and the translation result is 10 paragraphs run once.

12. **More discharge sheets.** `eval/synthetic_docs/make_doc_pdf.py` already builds one sheet. Generate 15 to 20 more with different drugs, doses, dates, and negations. A few days of authoring. The generator already exists.

13. **Run the translation arms more than once.** Repeat naive, protected, and full several times. Report a range. A few days, plus API cost. One run of 10 paragraphs is too thin to stand on.

14. **Turn known failures into tests.** The colloquial misses (`Thuốc này uống được không bác?`, `Chỉ số này có cao lắm không?`), the negation cases, and the back-translation restore bug. The range-rounding case is already in `backend/tests/test_gate.py`. The test files already accept an injected model, so these can run offline. About a week.

## First product surface

Do this after the items above. It is weeks, not hours.

15. **A warning on text a person has not reviewed.** One banner. Machine translation of a critical document is supposed to be reviewed by a person.

16. **A reviewer view.** One screen with the original, the simplification, the translation, and the back-translation. The gate’s reason sits on the sentence that failed. The reviewer approves, edits, or rejects that flag and signs the document. Record minutes per document. The patient app already shows the original and the gate badge.

17. **Hide identity the way doses are hidden.** Name, date of birth, and record number should be placeholders before the model sees the text. Intake already treats some of those lines as headers.

## Later safety work

18. **Negation scope.** Weakest measured behavior, at 18.2%. It is not the next build. Do not install medspaCy. That install broke the pinned clinical stack once already. A narrower check that pairs a negation with its own clause, without that dependency, is the practical version. Do it after the regression tests exist.

19. **Run the exemplar arm the way the app runs it.** The app retrieves similar pairs. The evaluation inserted four pairs from the top of the file. No conclusion was drawn. Re-run that arm with retrieval before claiming that examples help or hurt.

## After a clinic is using it

Do not build these until someone asks.

20. Minutes per document on the reviewer view.
21. Side-by-side PDF of both languages.
22. A link or QR code on the printed sheet that opens the translated version.
23. A second, larger text size. Body text is already 20px and document text 22px.
24. A medication checklist drawn from the entities the gate already extracts, such as “HOLD metformin until 11/14.”
25. Audio of the Vietnamese text, checked by a native speaker before it is offered.
26. Spanish as the second language, only after the Vietnamese numbers are repeated on more than one sheet. Each language needs its own glossary, its own forbidden renderings, and a second native speaker.

## Do not build

Electronic health record integration, single sign-on, SOC 2, text-message reminders, caregiver accounts, teach-back alerts, pediatric mode, fax intake, and a public API. Consent forms, end-of-life discussions, and behavioral health stay with a human interpreter. Do not add advice or recommendations.

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
