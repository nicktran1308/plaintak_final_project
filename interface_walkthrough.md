# PlainTalk — Interface Inspection: Cognitive Walkthrough

**Nick Tran · CPSC 597 · Dr. Chang-Huyn Jo**

**Status, 10 October 2026.** Sections 1–8 are the first inspection. They describe the upload screen as it was then: file choice first, paste second. That screen has since changed. Sections 9–14 inspect the interface that is in the repository now, close or keep each earlier finding against that screen, walk Personas B and C, and record the heuristic evaluation. A finding in sections 1–8 is historical. A finding in section 13 is current.

---

## 1. Why this method

The proposal excludes human-subjects testing: no IRB approval, no patient recruitment. Two structured inspection methods were committed to in its place, and this document records the first.

A cognitive walkthrough evaluates an interface by stepping through a task as a specific person, asking four questions at every action (Wharton et al., 1994):

1. Will the user try to achieve the right effect?
2. Will they notice that the correct action is available?
3. Will they connect the action with the effect they want?
4. Will they see that progress has been made?

Any "no" is a finding. The method is deliberately slow and states the obvious, which is its value: it surfaces assumptions the author stopped noticing while building.

**What it cannot do.** A walkthrough predicts where a user would struggle; it does not observe one. Every finding here is a hypothesis about behaviour, not a measurement of it. Findings are stated as such.

---

## 2. Personas

Personas are labelled A, B and C rather than given names. They are analytic
constructs, not descriptions of any individual, and naming them would imply a
specificity the method does not have.

| | background | device | relevance |
|---|---|---|---|
| **Persona A**, 71 | Immigrated at 58. Reads Vietnamese fluently, English poorly. Low technology confidence; a family member set up the device. | tablet | the primary user |
| **Persona B**, 34 | Bilingual adult child assisting a parent after a hospital discharge. Reads both languages. | laptop | the assisted case, which the proposal identifies as most common |
| **Persona C**, 68 | Vietnamese only, lives alone, mild presbyopia. | phone | the hardest case, and the one the proposal names as its motivation |

---

## 3. Walkthrough: Persona A, laboratory report

**Task.** Understand her potassium result and find out when to repeat the blood test.

**Starting state.** She holds a paper laboratory report from the hospital and opens PlainTalk on her tablet.

### Step 1 — language selection

| question | answer |
|---|---|
| Q1 goal | **Yes.** Two buttons, nothing else on screen. The intent is unambiguous. |
| Q2 visible | **Yes.** "Tiếng Việt" is written in Vietnamese and appears first. |
| Q3 connection | **Yes.** Tapping a language obviously selects it. |
| Q4 feedback | **Yes.** The next screen renders in Vietnamese. |

No finding. Showing both languages simultaneously on this screen is what makes it work: a Vietnamese-only reader can find their option without reading English, and a bilingual helper can find theirs.

### Step 2 — document intake

| question | answer |
|---|---|
| Q1 goal | **Uncertain.** She understands the app needs her paper. She does not have a digital file: her report is a physical sheet in her purse. |
| Q2 visible | **Partially.** "Chọn tập tin" is a full-width primary button. "Hoặc dán nội dung" sits below it in a smaller heading, visually secondary. |
| Q3 connection | **No.** "Tập tin" is technical vocabulary. A reader who has never managed files does not know what one is, and cannot map "choose a file" onto the paper in her hand. |
| Q4 feedback | **No.** Tapping the button opens an operating-system file picker rendered in English, listing folder names she cannot read. |

**Finding 1 — HIGH.** The intake screen assumes the patient possesses a digital file and understands file systems. The primary path is unusable for a patient holding paper, which is the common case for this population.

**Finding 2 — MEDIUM.** "Chọn tập tin" uses technical vocabulary. "Tập tin" presumes a mental model of computer storage.

**Finding 3 — HIGH.** The file picker is an operating-system dialog outside the application's control. It cannot be translated, resized, or simplified. Any path that reaches it exits the accessible interface entirely.

**Finding 4 — MEDIUM.** The paste path, which is the one Persona A could actually complete with a family member typing for her, is presented as the secondary option.

### Step 3 — reading the document

Assume a family member pasted the report text.

| question | answer |
|---|---|
| Q1 goal | **Yes.** Paragraph cards are visible with clear action buttons. |
| Q2 visible | **Yes.** "Giải thích đơn giản hơn" and "Xem bằng tiếng Việt" appear on every content card. |
| Q3 connection | **Yes.** Both labels are plain Vietnamese and describe their effect. |
| Q4 feedback | **Yes.** A spinner appears, then the text changes, a level chip appears, and the original is shown below. |

**Finding 5 — HIGH.** The document body renders in English until she presses translate on each paragraph individually. A laboratory report of this length is roughly fifteen presses before the page is readable. The proposal states that every screen appears in the patient's language from intake onward; the implementation does not meet this for document text.

**Finding 6 — MEDIUM.** Result flags read `HIGH` and `LOW` in English. These are the most consequential words in a laboratory report, they appear five times, and they remain untranslated until the paragraph is translated. A reader could scan the numbers and miss the flags entirely.

**Finding 7 — LOW.** The report's tabular layout (analyte, value, flag, reference range) passes through an intake splitter written against prose. Column structure is not preserved, and alignment between a value and its reference range may be lost.

### Step 4 — asking a question

She asks: *"Khi nào tôi thử máu lại?"*

| question | answer |
|---|---|
| Q1 goal | **Yes.** The input field carries a Vietnamese placeholder. |
| Q2 visible | **Yes.** The field and the "Hỏi" button are adjacent and both are large. |
| Q3 connection | **Yes.** |
| Q4 feedback | **Yes.** The answer arrives in Vietnamese with the source passage shown beneath it. |

No finding. The cited source remains in English, which is deliberate: Kong et al. (2026) recommend keeping the original visible beside any translation so a clinician who reads English can be shown it.

### Step 5 — a question the system must refuse

She asks: *"Chỉ số kali của tôi có cao không?"*

| question | answer |
|---|---|
| Q1 goal | **Yes.** |
| Q2 visible | **Yes.** |
| Q3 connection | **Yes.** |
| Q4 feedback | **Partially.** A coral card appears with the heading "Câu hỏi cho bác sĩ" and an explanation. The handoff counter increments. |

**Finding 8 — MEDIUM.** The refusal is clear, but the connection between the refusal and the counter at the bottom of the panel is not drawn. Nothing animates or points from one to the other, so a first-time user may not realise their question was preserved rather than discarded.

This step is worth noting as a design success. The document literally contains the word `HIGH` beside the potassium value, so a system willing to interpret would answer. It refuses, which is correct: reading a flag is not the same as telling a patient whether their result is dangerous.

---

## 4. Findings summary

| # | severity | finding | screen |
|---|---|---|---|
| 1 | HIGH | Intake assumes a digital file; patient has paper | upload |
| 3 | HIGH | OS file picker is outside the accessible interface | upload |
| 5 | HIGH | Document body stays English until translated per paragraph | reading |
| 2 | MEDIUM | "Chọn tập tin" is technical vocabulary | upload |
| 4 | MEDIUM | The usable paste path is visually secondary | upload |
| 6 | MEDIUM | `HIGH` / `LOW` flags remain untranslated | reading |
| 8 | MEDIUM | Refusal-to-handoff connection is not drawn | chat |
| 7 | LOW | Tabular layout not preserved by the prose splitter | reading |

**Three of eight findings, and two of three high-severity ones, concern document intake.** The step before the system does anything is where it is weakest. Every component that was measured — the gate, abstention, translation — sits downstream of a screen the target user may not get past.

---

## 5. Recommendations

**Reverse the intake priority.** Make the text area the primary path and file upload secondary. A patient holding paper can complete the paste path with help; nobody can complete the file path without a file.

**Replace "Chọn tập tin".** "Chụp hình hoặc chọn từ máy" describes an outcome rather than a storage concept.

**Translate the document body automatically at intake.** This is what the proposal specifies. It costs roughly two model calls per paragraph and a minute of waiting, and Finding 5 is the price currently being paid to avoid that. A progress indicator during intake is a better trade than fifteen presses.

**Translate result flags before display.** `HIGH` and `LOW` are short, closed-vocabulary, and safety-relevant. They can be substituted from the glossary without a model call.

**Draw the refusal-to-handoff connection.** A brief animation or an inline "đã thêm vào danh sách" line inside the refusal card.

---

## 6. On hospital-system integration

The intake findings suggest a structural answer: if the hospital transmitted the document directly, the patient would never face a file picker. This is the natural resolution and it is already recorded in the proposal's future scope.

It should not be presented as the answer to Findings 1 through 4, for two reasons.

**It is out of scope and unverifiable here.** No health-system partnership exists, and EHR integration requires an account and identity model, and therefore a considered approach to protected health information. That was deferred deliberately in Week 1.

**The proposal's own argument works against it.** Current Solutions states that patient portals solve document delivery rather than comprehension, and that *portal adoption is lowest among precisely the older and limited-English-proficiency populations who need comprehension support most*. A patient who cannot navigate a file picker is unlikely to have an active portal account. Proposing portal delivery as the fix assumes exactly the digital access the project was built because this population lacks.

Integration remains the right long-term direction. It does not remove the obligation to make paper intake work, because paper is what the patient is holding.

---

## 7. Limitations

At the time it was written, this walkthrough covered one persona and one task. Personas B and C, the discharge sheet, and the medication guide are walked in sections 10 and 11, against the screen as it stands after the intake change.

No user was observed. Every finding is a predicted difficulty, and the method is known to over-predict problems that users solve by trial and error, and to under-predict problems arising from fatigue, interruption, or emotional state, all of which apply to a patient recently discharged from hospital.

---

## 8. References

Kong, M., Fernandez, A., Bains, J., et al. (2026). Evaluation of the accuracy and safety of machine translation of patient-specific discharge instructions. *BMJ Quality & Safety*, 35, 150–158.

W3C (2023). *Web Content Accessibility Guidelines (WCAG) 2.2*. W3C Recommendation.

Wharton, C., Rieman, J., Lewis, C., & Polson, P. (1994). The cognitive walkthrough method: A practitioner's guide. In *Usability Inspection Methods*. John Wiley & Sons.

---

## 9. The current screen, scored against the first eight findings

The inspection below reads the interface in `frontend/src/` as of this writing: `Upload.jsx`, `Paragraph.jsx`, `Chat.jsx`, `Deferred.jsx`, `HandoffSheet.jsx`, `LanguagePick.jsx`, `App.jsx`, `i18n.js`, and `styles.css`. The same four questions from §1 are asked at each step. A "no" is a finding. Nothing here is an observation of a user.

Intake was rebuilt after §5. The text area is the primary control, full width, with a 64px "Đọc giấy của tôi" button. File upload sits below a divider labelled "hoặc", with the button "Lấy từ trong máy này" and the note "Chỉ dùng nếu giấy tờ đã được lưu sẵn trong máy." A "Dịch toàn bộ giấy tờ" control was added on the reading screen. It walks the paragraphs, shows "Đang dịch… n/N", and can be stopped. It does not run at intake.

| # | first inspection | against the current screen |
|---|---|---|
| 1 | HIGH. Intake assumed a digital file | **Closed.** Paste is the primary path. A person holding paper can complete it if someone types or pastes for them. |
| 2 | MEDIUM. "Chọn tập tin" | **Closed.** The label no longer names a file-system object. |
| 3 | HIGH. The operating-system file picker cannot be translated | **Open, and now confined to the secondary path.** The picker is unchanged. Reaching it still leaves the interface. |
| 4 | MEDIUM. Paste was visually secondary | **Closed.** The text area and the filled button come first. |
| 5 | HIGH. The body stays English until each paragraph is translated | **Open, with a mitigation.** Per-paragraph "Xem bằng tiếng Việt" is still the default. One button translates the whole paper and can be stopped. The body is English until that press. The proposal's "from intake onward" is still unmet. |
| 6 | MEDIUM. `HIGH` / `LOW` stay English | **Open on the text the reader sees first.** A closed substitution (`HIGH` → `CAO (HIGH)`, and the same for `LOW`, `CRITICAL`, and four other flags) runs only inside the Vietnamese rendering, after a translation exists, and only if the English token is still in that string. The English paragraph is not rewritten. |
| 7 | LOW. Tables are flattened | **Open.** Intake is still a prose splitter. |
| 8 | MEDIUM. A refusal does not show that the question was kept | **Open.** `Deferred.jsx` renders the coral card and nothing else. The counter at the bottom of the question panel increments, with no line tying the card to the list. |

Three of the four intake findings are closed. The two high-severity findings that sit on the reading screen, 5 and the secondary-path case of 3, are not.

---

## 10. Walkthrough: Persona B, discharge instructions

**Persona B, 34.** Bilingual adult child, helping a parent after discharge. Laptop. This is the assisted case the proposal treats as the common one.

**Task.** Work out which of the parent's medicines are held, when they restart, and leave with a list of questions for the clinician.

**Paper.** The synthetic discharge sheet used throughout the evaluation (`eval/synthetic_docs/make_doc_pdf.py`). The line that matters is: "HOLD metformin 500 mg PO BID until you follow up with nephrology on 11/14."

**Starting state.** The parent is beside them. The laptop is open to PlainTalk. The paper is in the parent's hand.

### Step 1 — language

| question | answer |
|---|---|
| Q1 goal | **Yes.** They need a language the parent can follow. |
| Q2 visible | **Yes.** "Tiếng Việt" is the first button, with "Vietnamese" under it, and "English" beside it. |
| Q3 connection | **Yes.** |
| Q4 feedback | **Yes.** The next screen is in the language they tapped, and a badge in the header repeats it. |

No finding. Choosing Vietnamese is the choice that lets the parent read the chrome. The English of the discharge stays on the cards either way, which is what a bilingual helper needs in order to check the model's Vietnamese against the sheet.

### Step 2 — getting the sheet in

| question | answer |
|---|---|
| Q1 goal | **Yes.** They can type from the paper, paste from a notes file, or, if they already saved the PDF, use the secondary button. |
| Q2 visible | **Yes.** The text area is the large control. |
| Q3 connection | **Yes.** "Gõ hoặc dán nội dung trên giấy" describes both things they can actually do. |
| Q4 feedback | **Partial.** "Đọc giấy của tôi" stays disabled until 20 characters, at half opacity, with no sentence explaining why. A single medication line ("metformin 500 mg") is 16 characters and does not enable it. |

**Finding 9 — MEDIUM.** The primary button gives no reason when it will not proceed. Persona B will try a longer paste and succeed. The same silence is much more costly for Persona C, who may stop at the first line.

The secondary path is usable for this persona: they read the English file picker. Finding 3 stays high for a reader who does not, and low for Persona B.

### Step 3 — reading the medication block

Assume the sheet has been pasted. Intake splits the numbered medication lines into separate cards. That split is the one the Week 5 report already checked on this PDF.

| question | answer |
|---|---|
| Q1 goal | **Yes.** Each medicine is its own card, with "Giải thích đơn giản hơn" and "Xem bằng tiếng Việt". |
| Q2 visible | **Yes.** "Dịch toàn bộ giấy tờ" is at the top, with "Mất khoảng một phút." |
| Q3 connection | **Yes.** Both labels say what they do. |
| Q4 feedback | **Partial.** A whole-document run shows "Đang dịch… n/N" and a Stop control. A paragraph the gate rejects stays in English, and the run continues. Nothing on that card says it was skipped. |

**Finding 10 — MEDIUM.** A failed paragraph inside "Dịch toàn bộ giấy tờ" is silent. The reader sees a Vietnamese paper with one English card left in it and no stated reason. The code comment in `App.jsx` says this is intentional: one failure must not abort the run. The absence of a reason is the problem, not the decision to continue.

Pressing "Giải thích đơn giản hơn" on the metformin line is the action this persona came for. `HOLD`, `PO`, and `BID` are the words the parent cannot read. The ladder is allowed to return the same sentence at two levels: on the measured target-domain run, five of ten paragraphs were identical at levels 1 and 2 (`week12_simplify_translate.md` §3.6).

**Finding 11 — MEDIUM.** When two rungs are the same sentence, the level chip still advances. Question 4 fails: the press appears to have done nothing, or to have failed. The button does not say that a rung may repeat.

The card also shows "Trình độ đọc" and a Flesch-Kincaid number. On this line the source scores 6.8 while still containing `PO` and `BID`. That number is the result §4.1 of `week5_week8.md` says must not be read as ease.

**Finding 12 — MEDIUM.** The grade is printed on the patient card. A helper may treat 6.8 as a property of the medicine, or may believe a lower grade means a safer simplification. The badge beside it ("Đã kiểm tra: tên thuốc, liều lượng, số lần, ngày tháng") is the check that actually bears on safety, and it is easy to read the grade as the result of that check.

Doses and dates are marked in the sentence. Drug names are not. The badge claims the names were checked. The mark shows the numbers.

### Step 4 — a question the sheet answers

They ask, for the parent: "Khi nào mẹ tôi gặp bác sĩ thận?"

| question | answer |
|---|---|
| Q1 goal | **Yes.** |
| Q2 visible | **Yes, on a laptop.** The question panel is a second column, sticky, beside the paper. |
| Q3 connection | **Yes.** |
| Q4 feedback | **Yes.** The answer comes back in Vietnamese. The cited sentence stays in English underneath, so the helper can match it to the sheet. |

No finding on this step for this persona. The same panel is not beside the paper on a phone. That is Finding 14, under Persona C.

### Step 5 — a question the system must refuse

The parent asks whether ibuprofen is all right for the pain. That is a permission question. The scope check refuses it before any model call.

| question | answer |
|---|---|
| Q1 goal | **Yes.** |
| Q2 visible | **Yes.** |
| Q3 connection | **Yes.** |
| Q4 feedback | **Partial.** The coral card is titled "Câu hỏi cho bác sĩ". The count beside "Câu hỏi cho bác sĩ" at the bottom of the panel becomes 1. Nothing on the card says the question was added there. |

Finding 8 stands. Severity for Persona B is medium rather than high: they can see the counter without scrolling, and "In" becomes enabled. They can still believe the card was only a warning.

### Step 6 — the handoff sheet

| question | answer |
|---|---|
| Q1 goal | **Yes.** They came to leave with something for the appointment. |
| Q2 visible | **Yes.** "In" is on the panel once the count is at least one. |
| Q3 connection | **Yes.** The next screen says "Hãy in trang này và mang theo khi đi khám." |
| Q4 feedback | **Yes, on a laptop with a printer.** The sheet lists the refused questions, numbered, and the browser print dialog opens. |

No new finding for Persona B. The sheet contains the questions and not the answers, which is what a clinician visit needs. The print dialog itself is the operating system's, in the laptop's language. Persona B can operate it.

**What this walk supports.** The assisted case is the one the current screen fits. Paste, a side-by-side question panel, English kept visible for the helper, and a printable list all line up with someone who reads both languages and is sitting at a laptop with the parent.

---

## 11. Walkthrough: Persona C, medication guide

**Persona C, 68.** Vietnamese only, lives alone, mild presbyopia. Phone. The proposal names this as the motivating case.

**Task.** Decide what "HOLD metformin 500 mg" requires of her before the next blood test. She holds a paper medication instruction, not a file.

**Starting state.** She is alone. The phone browser is open to PlainTalk. No one is there to type for her.

### Step 1 — language

| question | answer |
|---|---|
| Q1 goal | **Yes.** |
| Q2 visible | **Yes.** "Tiếng Việt" is a 76px button. Body text is 20px, which is the right direction for mild presbyopia, and the page allows pinch zoom. |
| Q3 connection | **Yes.** |
| Q4 feedback | **Partial.** Under the buttons, a status line is always in English: "Backend connected", a term count, and the retrieval threshold, or, if the server is down, "Backend not reachable" plus a shell command. |

**Finding 13 — MEDIUM, and HIGH when the server is down.** The first screen a Vietnamese-only reader sees includes an English diagnostic. On the success path it is noise at 15px in `#8A9BA1` (contrast 2.8:1 against the page, §12). On the failure path it is the only recovery instruction, and she cannot read it. She also cannot act on it: starting the server is not her task.

### Step 2 — getting a paper medication line in, alone

| question | answer |
|---|---|
| Q1 goal | **No.** Her goal is to have the paper explained. The screen's goal for her is to transcribe it. |
| Q2 visible | **Partial.** The text area is obvious. "Lấy từ trong máy này" does not offer the camera, which is the capture device she is holding. |
| Q3 connection | **No.** "Gõ hoặc dán" assumes text she already has in the machine. She has ink on paper. |
| Q4 feedback | **No**, if she types one short line and the button stays disabled (Finding 9). **No**, in the stronger sense that a dose she mistypes becomes the clinician's text: the gate checks later output against whatever she entered. |

**Finding 14 — HIGH.** Paste-first fixed the assisted case and left the unassisted case as transcription. There is no camera path. The earlier recommendation, "Chụp hình hoặc chọn từ máy", was not what shipped. "Lấy từ trong máy này" still opens the English system picker (Finding 3). For this persona the primary path is possible and the cost of a wrong character is a wrong dose in the source the gate trusts.

This is the same structural point §6 made about hospital integration, applied one step earlier. A file dropped in by a clinic would skip the picker. A photograph would still be something she can produce alone. Neither exists. The screen that remains asks her to type the instruction she came because she cannot confidently read.

### Step 3 — reading it on a phone

Assume she has typed the metformin line and enough surrounding text to pass the 20-character bar.

| question | answer |
|---|---|
| Q1 goal | **Yes.** She wants "HOLD" and "BID" in Vietnamese. |
| Q2 visible | **Partial.** "Xem bằng tiếng Việt" is on the card. "Dịch toàn bộ giấy tờ" is at the top. Both are in range if the paper is short. |
| Q3 connection | **Yes.** |
| Q4 feedback | **Yes** for a single paragraph that passes the gate. The Vietnamese appears under the English, the original stays, and the badge names what was checked. |

No new finding on a single short card. Findings 10, 11, and 12 apply if she simplifies or translates a longer guide: a skipped paragraph is silent, a repeated rung looks like a failure, and the grade number is on the card. At phone width the grade chip and the level chip wrap onto a second line. They remain readable. They remain easy to misread.

The header of a pasted guide is a separate, quieter card. Its translate control is 40px tall, below the 48px floor the stylesheet sets for every other control. It still clears the WCAG 2.2 AA target-size minimum of 24px. It misses the project's own rule. Recorded under §12, not as a separate walkthrough finding.

### Step 4 — asking, after the whole paper

On a viewport under 1000px the two columns become one. The question panel is rendered after every paragraph.

| question | answer |
|---|---|
| Q1 goal | **Yes.** "Thuốc này tôi có được uống tiếp không?" is the question she came with. |
| Q2 visible | **No**, until she scrolls past the paper. On a discharge-length paste that is the entire document. |
| Q3 connection | **Yes**, once she finds the field. The placeholder "Hỏi về giấy tờ" is plain. |
| Q4 feedback | **Yes** for the answer itself. A permission question returns the coral refusal. The counter sits under the field, on the same card, so she can see it if she is still looking at the card. Finding 8 still holds: the card does not say the question was saved. |

**Finding 15 — HIGH.** The question panel, which is the reason this persona opens the app, is the last region on the phone page. The laptop layout that serves Persona B hides the panel from Persona C behind the document. Nothing pins it, and there is no skip control.

She then has to keep the refused question. "In" opens the handoff screen. That screen's instruction is to print it and bring it to the appointment. The print dialog is the phone operating system's, in English (the same class as Finding 3). She lives alone and is unlikely to have a printer. The list itself is useful if she can show the phone to the clinician. The screen tells her to print.

**Finding 16 — MEDIUM.** The handoff's only completion path is print. For this persona the artifact that matters is the list on the phone, and the instruction describes a printer.

### Step 5 — leaving by accident

"Bắt đầu lại" is in the header on every screen after language. It ends the session immediately. There is no confirmation. Refresh does the same, by design: the backend keeps nothing. She is not told that before it happens.

**Finding 17 — MEDIUM.** One press in the header discards the paper, the translations, and the questions for the clinician. On a phone that control sits in the same bar as the language badge, in thumb range.

**What this walk supports.** Persona C is the case the interface still fails. The failures are at the two ends: getting paper in without a helper, and reaching a question on a phone. The middle, a single card with a translation and a visible English original, is the part that holds.

---

## 12. Heuristic evaluation

The proposal commits to this evaluation in place of user testing. Two checklists are applied. WCAG 2.2 level AA is the external one. The numbers in `frontend/README.md` and `styles.css` are the project's own senior-friendly rules: 20px body text, 22px document text, 48px targets, no hover-only control, no session timeout, the clinician's English always visible, deferrals in coral rather than red, a 3px focus ring, and `prefers-reduced-motion` honoured.

Contrast figures below are for the declared colours, computed as WCAG relative luminance. They are properties of the stylesheet, not of a particular monitor.

### 12.1 WCAG 2.2 AA

| Criterion | Result | Evidence |
|---|---|---|
| 1.1.1 Non-text content | Pass | Icons inside the gate badge and the deferral cards are `aria-hidden`. The status is the adjacent words. |
| 1.3.1 Info and relationships | Fail | The reading screen's title is a `<span class="section-label">`, not a heading. Upload, language, and handoff use an `<h2>`. A heading navigation skips the document. |
| 1.3.2 Meaningful sequence | Pass on a laptop, fail on a phone | DOM order is paper, then questions. That matches the two-column layout. On one column it places the question field after every paragraph (Finding 15). |
| 1.3.4 Orientation | Pass | No orientation lock. |
| 1.3.5 Identify input purpose | Not applicable | No field asks for a name, email, or other user-specific token. The paste area is document content. |
| 1.4.1 Use of colour | Pass | The gate badge pairs colour with an icon and a sentence. A deferral pairs coral with a title. The count is a number plus a label. |
| 1.4.3 Contrast (minimum) | Fail | `--ink` `#16272D` on white is 15.4:1. `--ink-soft` `#5F7078` on white is 5.2:1. `--ink-faint` `#8A9BA1` is 2.9:1 on white and 2.8:1 on the page `#FBFAF7`. Faint is used for section labels (14px, semibold), the grade chip (15px), the original-text label (14px), the citation label (13px), empty states (18px), and the handoff numbers (15px). None of those sizes reach the large-text threshold. All of them need 4.5:1. |
| 1.4.4 Resize text | Pass | The viewport sets `width=device-width, initial-scale=1` and does not set `maximum-scale` or `user-scalable=no`. |
| 1.4.10 Reflow | Pass, with Finding 15 | At 320px CSS width the columns collapse to one. Content is not in a horizontal scroller. The cost is vertical: the question panel moves to the bottom. |
| 1.4.11 Non-text contrast | Fail | The focus ring is `#00A896` on `#FBFAF7`, 2.9:1. The criterion asks for 3:1 against the adjacent colour. The ring is 3px and offset by 3px, so it is large enough to see and too close to the page colour to meet the ratio. |
| 1.4.12 Text spacing | Pass | Spacing is not locked. The paragraph text uses `pre-wrap`, so an override can widen lines without clipping them. |
| 1.4.13 Content on hover | Pass | No control reveals its label only on hover. |
| 2.1.1 Keyboard | Pass | Every action is a `<button>`, a text field, or a file input behind a button. |
| 2.1.2 No keyboard trap | Pass | No trap is constructed. The system print dialog is outside the page, same as Finding 3. |
| 2.2.1 Timing adjustable | Pass | No timeout. `App.jsx` states this on purpose. |
| 2.4.1 Bypass blocks | Fail | No skip link. On the phone layout the repeated paragraph actions sit between the top of the page and the question field. |
| 2.4.2 Page titled | Pass | The title is "PlainTalk". It does not change per screen. Acceptable for a single-view app; a screen-reader user is not told when the view becomes the handoff sheet. |
| 2.4.3 Focus order | Pass | Focus follows DOM order, which is the visual order in both layouts. |
| 2.4.6 Headings and labels | Partial | The paste area has a `<label for="paste">`. The question field repeats its placeholder as `aria-label`. The reading view has no heading (1.3.1). |
| 2.4.7 Focus visible | Pass on visibility, fail on contrast | `:focus-visible` draws a 3px outline. The colour fails 1.4.11. |
| 2.4.11 Focus not obscured (AA) | Pass | No sticky bar covers a focused control. The question panel sticks only inside its own column, and only above 1000px. |
| 2.5.1 Pointer gestures | Pass | No path-based gesture. |
| 2.5.2 Pointer cancellation | Pass | Actions run on click, which is the up-event. |
| 2.5.3 Label in name | Pass | Visible button text is the accessible name. |
| 2.5.7 Dragging movements | Pass | Nothing requires a drag. |
| 2.5.8 Target size (minimum) | Pass | The general button rule is 48px. The header-card translate control is forced to 40px, which is still above the 24px minimum. |
| 3.1.1 Language of page | Pass | `pickLanguage` sets `document.documentElement.lang` to `vi` or `en`. The shell in `index.html` starts as `vi`. |
| 3.1.2 Language of parts | Fail | After Vietnamese is chosen, the clinician's paragraph, the original panel, and the citation are English inside a page whose language is Vietnamese. None of those nodes sets `lang="en"`. A screen reader applies Vietnamese pronunciation to the dose line. |
| 3.2.1 On focus | Pass | Focus does not change the screen. |
| 3.2.2 On input | Pass | Typing does not submit. Enter in the question field does, which is the expected behaviour of that field. |
| 3.2.6 Consistent help | Pass | There is one help pattern: a short line under the primary action. It is not offered on the refusal card (Finding 8). The criterion is about consistent placement of help when help exists, and the pages that have it put it in the same role. |
| 3.3.1 Error identification | Partial | Server errors render in a coral block. The disabled paste button does not (Finding 9). |
| 3.3.2 Labels or instructions | Pass | Paste and question each have a visible or accessible name. |
| 3.3.7 Redundant entry | Pass | Nothing asks her to re-enter a value the page already holds. |
| 3.3.8 Accessible authentication | Not applicable | No login. |
| 4.1.2 Name, role, value | Pass | Native controls. The deferral card exposes `role="status"`. |
| 4.1.3 Status messages | Partial | A refusal is a status role, so it can be announced. "Đang dịch… n/N" is text inside a button, not a live region. The language screen's busy state is a spinner and an ellipsis. |

### 12.2 The project's own senior-friendly rules

| Rule | Result |
|---|---|
| Body 20px, document 22px | Met. Be Vietnam Pro is loaded for the diacritics. |
| 48px minimum target | Met, except the translate control on a header card, which is set to 40px. |
| No hover-only control | Met. Hover only recolours a border. |
| No session timeout | Met. |
| Clinician's English always visible | Met. A simplification adds the original underneath. It is never behind a toggle. |
| Deferrals in coral, not red | Met. `--coral` is `#B8461F`. Error text uses the same coral family, so an error and a refusal share a colour. The titles differ. Worth knowing, because §4 of the first inspection treated the colour as the signal that a refusal is not a failure. |
| `prefers-reduced-motion` | Met for CSS. The question list also calls `scrollIntoView({ behavior: 'smooth' })`, which is script, and the media query does not stop it. |
| 3px focus ring | Drawn. The colour fails the non-text contrast ratio, §12.1. |

Two further mismatches with a senior reader are not contrast bugs. They are the grade number on the card (Finding 12) and the English server line on the language screen (Finding 13). Both put a specialist's quantity in front of the person the type size was chosen for.

---

## 13. Findings from this inspection

Historical findings that remain open are listed again so this table can be read alone.

| # | severity | finding | where it bites |
|---|---|---|---|
| 3 | HIGH for A and C, low for B | The system file picker is English and outside the page | secondary upload; also the print dialog |
| 5 | HIGH | The paper stays English until the reader asks, one paragraph at a time or via the optional whole-paper button | reading |
| 6 | MEDIUM | Result flags are rewritten only inside an existing Vietnamese translation | reading, lab report |
| 7 | LOW | A table is flattened to prose | reading, lab report |
| 8 | MEDIUM | The refusal card does not say the question was added to the clinician list | chat |
| 9 | MEDIUM | "Đọc giấy của tôi" stays disabled under 20 characters and does not say why | upload |
| 10 | MEDIUM | A paragraph skipped during whole-paper translation stays English with no reason | reading |
| 11 | MEDIUM | An unchanged ladder rung still advances the level chip | reading |
| 12 | MEDIUM | The Flesch-Kincaid grade is shown on the card | reading |
| 13 | MEDIUM, HIGH if the server is down | The language screen's status line is English technical text | language |
| 14 | HIGH | Alone with paper, the reader must transcribe it. There is no camera. A mistyped dose becomes the source text. | upload, Persona C |
| 15 | HIGH | On a phone the question panel sits below the whole paper, with no skip | reading, Persona C |
| 16 | MEDIUM | The handoff tells her to print. The useful artifact for someone without a printer is the list on the phone. | handoff, Persona C |
| 17 | MEDIUM | "Bắt đầu lại" discards the session with no confirmation | header |

Persona B, on a laptop, with the parent beside them, can complete the discharge task. Persona C, alone, on a phone, with a paper medication line, is stopped at intake and, if she gets past it, has to scroll the length of the paper before she can ask the question she came with.

The heuristic failures that should be named next to those are the faint text at 2.8:1 (1.4.3), the focus ring at 2.9:1 (1.4.11), English passages with no `lang="en"` (3.1.2), and the missing skip and heading on the reading view (2.4.1, 1.3.1).

---

## 14. What this inspection does not do

No user was observed. The method over-predicts some problems and under-predicts fatigue, interruption, and the state of mind of a person recently discharged. Those limits are unchanged from §7.

The three walks now cover the three personas and the three document types the proposal named. Laboratory, discharge, and medication guide share one reading screen, so the document-type difference is in the paper and the question, not in a separate layout. A second screen for labs was not available to walk.

The evaluation is one inspector, the author of the surrounding reports, reading the current source. A second inspector would change the wording of findings. It should not change the contrast ratios or the DOM order, which are measured.
