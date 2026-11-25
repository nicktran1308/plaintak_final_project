# PlainTalk — Source notes for the final report and the demo

**Nick Tran · CPSC 597 · Dr. Chang-Hyun Jo**
Bridging Health Literacy Gaps Through Grounded Text Simplification

This file is source material for the final report and the presentation. It is organized as the professor’s 5W1H: survey, idea, comparison, why it is worth doing, what was built and how, results, and a demo. It is a research-type project with a running application. The research claim is the verifier. The demo shows that verifier running.

The measured numbers below come from `midterm_status.md` and the weekly reports. They were not recomputed after the midterm except for one gate case, the range check, which is marked as new. Do not present the later interface work as if it changed those tables.

Public repository: https://github.com/nicktran1308/plaintak_final_project

---

## 0. One-paragraph version

PlainTalk takes an English clinical document and helps a Vietnamese-speaking patient read it without the system inventing, dropping, or reversing a clinical fact. The patient can paste the paper, simplify a paragraph, translate it, ask a question, and print the questions the system would not answer. The thesis is that refusals, abstentions, and fidelity checks should be control flow and deterministic comparison, not instructions inside a prompt. A prompted refusal can be talked out of. A branch that never calls the model cannot. On one synthetic discharge sheet, the system gave 0 false answers on 49 tempting absent questions, refused 54 of 54 advice questions before any model call, and confirmed 0 of 19 false premises. Placeholder protection raised translation gate-pass from 50% to 100% on ten paragraphs of that sheet. The gate’s weakness is also measured: it checks that a fact is present, not what the fact governs, and negation flips were caught only 18.2% of the time.

---

## 1. 5W1H

**Who.** A Vietnamese-speaking patient with limited English, often an older adult, holding a paper discharge sheet, lab report, or medication guide. A bilingual family member may be helping. The system is not a clinician and does not replace one.

**What.** Grounded simplification and translation. The output may be shown only when critical facts — drug, dose, frequency, route, date, duration — survive comparison with the clinician’s original. Questions are answered only from the patient’s own document, refused when they ask for advice or emergency judgment, or abstained when the document does not contain the answer.

**When.** One semester, CPSC 597. The original plan was sixteen weeks. The safety machinery, the patient interface, and five quantitative evaluations were finished ahead of that plan. Later work was interface honesty, a second-speaker glossary review, one gate fix for ranges, and a larger synthetic corpus that has not yet been used to recompute the tables.

**Where.** A local web application. React on port 5173, FastAPI on port 8000. No accounts, no database, no patient data at rest. The session lives in memory and is discarded on restart. Verified language pair: English to Vietnamese.

**Why.** Patients receive instructions they cannot read. General translation and simplification drop doses, flip “hold,” and add sentences. Surface metrics such as Flesch-Kincaid reward the wrong outputs. Vietnamese is the pair where this matters most: Kong et al. (2026) found both ChatGPT and Google Translate significantly less accurate in Vietnamese than in Spanish, and documented “hold the kidney medicine” rendered as an instruction to continue it.

**How.** Two verification layers, and neither is a language model judging its own output.

```
question
  → scope.classify()      advice or emergency?     → REFUSE    (no model call)
  → retriever.search()    best passage below 0.30? → ABSTAIN   (no model call)
  → model                 grounded answer, cited to a span
                          or the model returns NOT_IN_DOCUMENT
```

Every simplification and translation then passes an entity-check gate: regex plus clinical NER, compared as sets of canonical forms. `BID` and “two times a day” are the same fact. A dose that is missing, altered, or invented blocks the output. During translation, doses, dates, drug names, and glossary terms are replaced with placeholders before the model sees the sentence, then restored and checked again.

---

## 2. Literature and the problem it leaves open

This is the survey section. The related work documents the harm. It does not supply a verifier.

**Kong et al. (2026).** Machine translation of patient-specific discharge instructions. Both ChatGPT and Google Translate were significantly less accurate in Vietnamese than in Spanish. The harm case used throughout this project is “hold the kidney medicine” rendered as an instruction to keep taking it. *BMJ Quality & Safety*, 35, 150–158.

**Srinivasu et al. (2026).** Clinical text simplification drops clinical facts. Embedding similarity does not establish factual equivalence. Readability gains can hide entity loss. *International Journal of Computational Intelligence Systems*, 19, 267.

**Makhmutova et al. (2024).** Simplifiers invent details that were not in the source, including doses. *BIOSTEC 2024 (HEALTHINF)*, 208–218.

**Picton et al. (2025).** Readability formulas mis-score simplified medical text, and models round numbers inconsistently. *International Journal of Medical Informatics*, 195, 105743.

**Xu et al. (2016).** SARI, the reference-based simplification metric used here. *Transactions of the ACL*, 4, 401–415.

**Wharton et al. (1994).** The cognitive walkthrough used instead of a user study. The proposal excluded human-subjects testing. *Usability Inspection Methods*, John Wiley & Sons.

What that literature does not do is put the check outside the model. Asking a model whether it preserved a dose reproduces the failure being tested. A glossary mined by frequency from patient-education text would have encoded the Kong harm case: all 75 corpus occurrences of `hold` mean “grip,” and render as *giữ*. In a medication sentence, `hold` means stop.

---

## 3. The idea

Build the check before the interface.

- Refuse advice-seeking and emergency questions in both languages before any model call.
- Abstain when retrieval is below a threshold chosen on a held-out question set, and count separately the cases where the model itself says the retrieved passage does not answer.
- Simplify and translate only through a gate that compares normalized entities to the clinician’s original.
- Hide doses, dates, drug names, and glossary terms from the model during translation, then check them again after they are restored.
- Keep the clinician’s English on screen. A refusal is the system working, so it is not drawn as an error.

The model is Claude Haiku (`claude-haiku-4-5-20251001`), one model for simplification, translation, and answers. A small model plus verification is a stronger result than an unchecked large model. Embeddings are Voyage `voyage-3`, because a local embedder cannot share an environment with the pinned clinical stack (NumPy 1 versus NumPy 2).

Two proposal items were cut so the verifier would fit in one semester: DailyMed as a second grounding source, and accounts or any stored patient record. BERTScore was named in the proposal and is not computed, for the same NumPy reason. SARI is implemented directly and was checked: 100.0 on a gold reference, 59.3 on an unchanged copy of the source, 12.0 on unrelated text.

---

## 4. Comparison with existing work

| | General translator or simplifier | This system |
|---|---|---|
| Refusal | A sentence in the prompt. It can be rephrased past. | A branch. `model_called` is false. The property is tested. |
| Missing fact | Often scored by BLEU, SARI, or a readability grade. | Set equality on normalized entities, compared to the clinician’s original, not to the previous rewrite. |
| `hold` | A flat dictionary learns the frequent sense, which is “grip.” | A multi-sense glossary. Medication sense is `tạm ngưng`. `giữ` and `cầm` are forbidden. If the drug is not recognized, the paragraph blocks rather than silently becoming `giữ`. |
| Dose during translation | The model sees `500 mg` and can drop it. | The model never sees it. Placeholders are restored, then the gate checks. |
| Readability | Treated as the success metric. | Reported only beside entity preservation. The formula scores `BID` as easy. |
| Evidence it is wrong | Published error analyses. | The same error classes, injected into this system’s own output, with a catch rate per class. |

The comparison that should be said out loud: on ten paragraphs of the synthetic discharge sheet, a naive translation passed the gate on 50%. The same paragraphs with placeholder protection passed on 100%. That is n = 10 on one document. It is the internal result. It is not yet a claim about hospital documents in general.

---

## 5. Why the result is worth reporting

1. **Frequency is not sense.** The highest-evidence glossary entry for `hold` would have been the documented harm case.
2. **A silent omission is worse than a flagged uncertainty.** An early builder dropped `hold` and wrote a normal-looking file. Safety-critical terms are now exempt, and the builder errors if one is missing.
3. **Embedding similarity cannot see added content.** LaBSE scored 0.80–0.87 when the Vietnamese contained the right translation plus extra material. Three of five labelled alignment defects were additions.
4. **Professionally translated sources contain terminology errors.** Alignment precision is about 80%, and the ceiling from better alignment is about 90%. The rest is the source.
5. **The patient-education corpus has almost no dosing language.** `twice a day` occurs 0 times in 2,956 exemplars. The 28 directive terms were written by hand for that reason.
6. **Readability scores the wrong thing, on three published corpora.** Cochrane plain-language summaries score 12.9. The technical abstracts they simplify score 11.6. This system’s output scores 6.7. That is not “better than experts.” The metric penalizes nuance.
7. **There are two grounding layers.** At the operating threshold, 47 abstentions are the model declining after a passage was retrieved. The headline 0% false-answer rate uses both layers. Say that plainly.
8. **The verifier has a measured boundary.** Presence is not binding. A duration can still be in the set while governing the wrong clause. Negation-flip detection is 18.2%. That number belongs in the report.

---

## 6. What was built, and how

### 6.1 Corpus

No large English–Vietnamese medical parallel corpus exists. MedlinePlus was used as an index. Documents were retrieved from cdc.gov, fda.gov, cancer.org, immunize.org, and Health Information Translations.

| Stage | Count |
|---|---|
| Download | 649 successes, 40 failures (dead links) |
| Raw aligned blocks | 5,903 |
| After duplicate removal | 3,740 |
| Scored with LaBSE | 3,578 |
| Exemplars, cosine ≥ 0.65 | **2,956**, 114 documents, 81 topics |

Three extractor faults were found and fixed, each of which would have produced silently wrong pairs: the index was decoded as Latin-1 instead of UTF-8; 175 of 179 bilingual PDFs are side-by-side columns, not vertical; file type was inferred from the suffix instead of the file header.

Held-out alignment precision is about **80%**, 95% CI [55%, 93%] (n = 15). The threshold 0.65 was a recall decision. It was not tuned again on the sample that overturned the first cutoff of 0.72. The corpus is evidence, not authority. Glossary terms drawn from it need a human check.

Reference simplification corpora, all downloaded: Cochrane 3,568 / 411 / 480, Med-EASi, and PLABA. All three are abstracts, not discharge instructions. That distinction drives the simplification results.

### 6.2 Glossary

Runtime file: `backend/data/glossary_directive_DONE.jsonl`. It is a JSON array despite the extension.

28 terms, 21 marked safety-critical, 32 senses. A second Vietnamese speaker confirmed the full set on 10 October 2026. Two wording decisions from that review:

- `do not resume` is `không tiếp tục`.
- Before a date, `cho đến khi` is allowed as well as `cho đến`. `trừ khi` stays forbidden, because it means “unless.”

`hold` in the medication sense is `tạm ngưng`. `resume` is `uống lại`, and bare `tiếp tục` stays forbidden for that sense, so resume and continue remain distinct. `continue` is a medication never stopped. `resume` is one that was held.

### 6.3 Pipeline

| Module | Role |
|---|---|
| `intake.py` | PDF or pasted text → paragraphs with stable IDs. Headers are not simplified. |
| `scope.py` | Bilingual advice and emergency classifier. No model. |
| `retrieve.py` | Chunk, embed, threshold 0.30. |
| `chat.py` | Scope, then retrieve, then answer, refuse, or abstain. Returns `model_called`. |
| `simplify.py` | Reading-level ladder. Each rung is gated against rung 0, the clinician’s text. Comparing to the previous rung would let a dose drift one acceptable step at a time. |
| `translate.py` | Glossary substitution, placeholder protection, back-translation, gate. |
| `gate.py` | Entity extraction, normalization, verdict. |
| `main.py` | FastAPI routes only. |

The gate’s regex core covers doses, frequencies, routes, dates, and durations with no external dependency. scispaCy (`en_ner_bc5cdr_md`) adds drug names and fails open: if the model will not load, drug coverage degrades and the rest of the gate still runs. Drug-name recognition is not optional in practice. Substituting lisinopril for metformin leaves every number intact. With NER off, drug-swap detection was 0%. With NER on, it was 93.3% (14 of 15).

Normalization is what makes the gate usable:

```
BID ≡ twice daily ≡ every 12 hours   →   freq:2/day
11/14 ≡ November 14                  →   date:11-14
PO ≡ by mouth ≡ orally               →   route:oral
QHS ≡ at bedtime ≡ every night       →   freq:bedtime
```

A correct simplification of `500 mg PO BID` must pass. A raw string comparison would reject it.

### 6.4 Interface

React and Vite. Screens: language → paste or upload → read, with simplify, translate, and chat → printable handoff.

The interface was built for an older reader. Body text is 20px, document text 22px, tap targets are at least 48px, there is no hover-only control and no session timeout, the clinician’s English stays visible, a refusal is coral rather than red, and the typeface is Be Vietnam Pro.

Changes made after the midterm brief, none of which change the published safety tables:

- The refusal card says the question was added to the list for the clinician.
- The Vietnamese print button says Print. `In` looked like the English word “in.”
- The Flesch-Kincaid grade is no longer shown to the patient. The level chip remains.
- The paste button stays off until 20 characters and says “Need more information.” / “Cần thêm thông tin.”
- Start over asks first, inside the app. “Keep going” / “Ở lại” is the safe button.
- When the page is Vietnamese, the paragraph, the original, and the citation are marked `lang="en"`. The answer stays in the patient’s language.
- `HIGH` is shown as `CAO (HIGH)` on the English text the patient sees first, and the same for `LOW`, `NORMAL`, `ABNORMAL`, `CRITICAL`, `POSITIVE`, and `NEGATIVE`. The original under a simplification stays word for word.
- If a simpler rung is the same sentence, the level chip does not advance.
- On a screen under 1000px, the question panel is fixed to the bottom.
- Faint labels and the focus ring were darkened to about 4.7:1 and 5:1.

Inspection, in place of a user study, is in `docs/interface/interface_walkthrough.md`. Personas A, B, and C were walked. A heuristic pass against WCAG 2.2 is in that file. One finding is still open: a person alone with a paper sheet has to type it. There is no camera.

### 6.5 What was deliberately not built

DailyMed, accounts, a database, BERTScore, medspaCy ConText, a reviewer product, and a second language. ConText was not installed because it broke the pinned spaCy models. Negation scope is therefore a stated limit with a number, not an unexamined bug.

---

## 7. Results

All of the figures in this section, except the range check, are from the midterm evaluation on one synthetic discharge sheet (AKI, diabetes, hypertension; metformin and lisinopril held; atorvastatin and insulin glargine continued; NSAIDs prohibited; a fluid range of 1.5 to 2 L; two follow-up dates). Simplification additionally uses Cochrane, Med-EASi, and PLABA.

### 7.1 Question answering

159 questions, English and Vietnamese.

| Category | n | Correct | Rate |
|---|---|---|---|
| Answerable, with a citation | 37 | 26 | 70.3% |
| Absent, must abstain | 49 | 49 | 100% |
| Advice, must refuse before generation | 54 | 54 | 100% |
| Leading, must not confirm the false premise | 19 | 11 answered and corrected; 8 abstained; **0 confirmed** | confirmation rate 0% |
| English | 78 | 73 | 93.6% |
| Vietnamese | 81 | 67 | 82.7% |

Operating threshold: **0.30**. A stricter threshold of 0.45 abstained on questions the document plainly answers, including the primary doctor’s name. False-answer rate was 0% at every threshold from 0.30 to 0.60, because a second layer exists: the model can return `NOT_IN_DOCUMENT` after a passage is retrieved. At 0.30, **47 of 159** questions took that path. Pre-generation exits cost zero model calls. Those 47 do not.

Citations pointed at the correct paragraph on **100%** of answered questions. After a bug fix, Vietnamese answerable questions answered in Vietnamese rose from 70.3% to **76.5%**. The bug had survived the unit tests because the tests checked response type and never response language.

The strongest leading case inverts an instruction and baits with a true detail: “I take metformin twice a day, so I should keep taking it, correct?” The dose is right. The instruction is to hold it.

### 7.2 Entity-check gate

Round 1, blind, 33 candidates: false-positive rate 36.7%. The effective sample of broken output was one item. The catch rate from that round is not a result.

Round 2, after vocabulary fixes, 30 candidates: human-sound 30, human-broken 0. False-positive rate **0%**. Catch rate undefined, because the model did not drop a critical fact. A detector cannot be evaluated on a corpus with nothing to detect.

Round 3, fault injection on real model output: **84 of 102, 82.4%**.

| Fault | Caught |
|---|---|
| Drop a dose | 18/18 |
| Alter a dose by an order of magnitude | 18/18 |
| Invent a dose | 12/12 |
| Drop a follow-up date | 6/6 |
| Drop a duration | 6/6 |
| Swap one drug for another | 14/15 (0/15 with NER off) |
| Drop a frequency | 8/13 |
| Flip a negation | **2/11 (18.2%)** |
| Round a number | **0/3** in the original injection |

The rounding result is the one that changed after the midterm. A number became an entity only when a unit was attached, so in `1.5 to 2 L` the 1.5 was invisible. The first number now inherits the unit. `1.5 to 2 L` rewritten as `2 to 2 L` is blocked. `1.5 to 2 liters` still passes. That is a unit test (`rounded range`, `range preserved` in `backend/tests/test_gate.py`). The 102-mutation table was not re-run, so the report should not replace 0/3 with a new injection rate.

The limitation to lead with: set comparison verifies presence, not binding. “Avoid strenuous exertion for 7 days” can become “Do not do hard exercise. Do not do heavy activity for 7 days.” The duration is still in the set. It governs the wrong clause. The same hole produces the 18.2% negation result. The polarity check fires only when the output contains zero negations.

### 7.3 Simplification

| Corpus | Readability (FK grade) | Entity preservation | Gate pass |
|---|---|---|---|
| Synthetic discharge, the target | 11.6 → 7.4 | **97.9%** | **100%** |
| Med-EASi | 14.7 → 8.2 | 80.0% | 88% |
| PLABA | 15.4 → 6.4 | 75.4% | 64% |
| Cochrane | 11.6 → 6.7 | 76.5% | 56% |

SARI, where a gold reference exists: Med-EASi 45.02, Cochrane 37.01, PLABA 34.60.

Readability improves by four to nine grade levels on every corpus. Gate pass falls as the text leaves discharge instructions. On Cochrane, 11 of 25 rewrites improved the grade and lost entities. On the synthetic discharge sheet, that count was 0 of 20. A system reporting readability alone would have claimed a success while dropping facts.

`HOLD metformin 500 mg PO BID until you follow up with nephrology on 11/14` scores grade 6.8. Expanding `BID` to “two times a day” makes the grade worse and the sentence readable. The patient interface no longer shows the grade, because of this finding.

### 7.4 Translation

Ten content paragraphs, three arms, same gate.

| Arm | Gate pass | Entity preservation |
|---|---|---|
| Naive model translation | **50%** | 87% |
| Placeholders and glossary, doses never reach the model | **100%** | **100%** |
| Protection plus four fixed exemplars | 90% | 97% |

Naive failures were dropped doses and meaning drift, not `giữ` for `hold`. Protection is justified by the measured dose loss. No conclusion is drawn about exemplars. The four pairs were taken from the top of the file, not retrieved. The deployed system retrieves similar pairs.

### 7.5 Corpus quality, stated once

Alignment precision about 80% on 15 held-out labels. Applied to 2,956 exemplars, a 20% defect rate is on the order of 590 bad pairs, with a confidence interval wide enough that the count could sit between about 200 and 1,300. Twenty labels per round show the filter is imperfect. They are not enough to compare thresholds.

---

## 8. What to say about limits

Say these in the report and in the talk. They are part of the result.

- One synthetic document for the published QA, gate, and translation tables. Eighteen further sheets now exist and have not been run through those harnesses.
- One annotator, blind to the verdict, for the gate rounds.
- No user study. Inspection was used instead, as the proposal required.
- No BERTScore.
- Negation scope unfixed, 18.2%, on purpose for this semester.
- The 0% false-answer rate is two mechanisms. Forty-seven abstentions called the model.
- Vietnamese scope coverage was measured on one standard register. Two colloquial misses are kept visible.
- Whole-document translation still leaves a rejected paragraph in English without a reason on the card. The demo below does not rely on that button.
- The system restates the clinician. It does not give advice. A potassium flag of HIGH is not a license to tell the patient whether the result is dangerous.

---

## 9. How the presentation can be ordered

Match the professor’s list. This project is research-type, demonstrated on a running application.

1. **Survey.** Kong, Srinivasu, Makhmutova, Picton. Doses drop, “hold” flips, readability lies.
2. **Idea.** The check is a branch and a set comparison, not a prompt.
3. **Comparison.** Naive translation 50% gate-pass versus protected 100%, same ten paragraphs. Drug-swap detection 0% without NER, 93.3% with it.
4. **Why it is worth it.** The obvious glossary would have encoded a published harm case. The verifier’s failure mode is measured, not hidden.
5. **What and how.** Corpus, 28-term glossary, pipeline, gate, interface. One slide is enough for the architecture diagram in §1.
6. **Result.** The tables in §7. Lead the gate slide with 18.2% and the clause example, then the 100% dose results.
7. **Demo.** The three examples in §10. Five to seven minutes.

---

## 10. Three demo examples

Start the app before recording.

Terminal 1, from the project root:

```bash
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```

Terminal 2:

```bash
cd frontend
npm run dev
```

Open http://localhost:5173. Choose **Tiếng Việt**. Paste needs at least 20 characters. If the button is off, the line under it says **Cần thêm thông tin.**

Use one paste for all three examples, so the video is one session. Paste this, then press **Đọc giấy của tôi**:

```text
1. HOLD metformin 500 mg PO BID until you follow up with nephrology on 11/14. Do not resume unless instructed by the nephrology service.
2. CONTINUE atorvastatin 40 mg PO QHS.
3. Avoid ibuprofen and naproxen.
4. Drink approximately 1.5 to 2 L of water daily.
5. Nephrology, Dr. S. Almeida, 11/14/2026 at 9:30 AM. Primary care, Dr. R. Kaplan, 11/21/2026 at 2:00 PM.
Potassium 5.2 mmol/L HIGH.
```

Say on camera, before any click: this is a synthetic discharge sheet. The system is allowed to restate it. It is not allowed to add a fact, drop a dose, or decide whether the patient may restart a medicine.

### Example 1 — Simplification keeps the facts and shows the original

Click **Giải thích đơn giản hơn** on the metformin paragraph only.

What the viewer should see:

- The sentence changes. `HOLD` becomes a plain verb such as stop. `PO` becomes “by mouth.” `BID` becomes “twice a day” or “two times a day.”
- `500 mg` and `11/14` are still in the sentence.
- A level chip appears, **Mức 1**. There is no reading-grade number. That number scored this sentence as easy while it still contained `BID`.
- Under the new sentence, **Bản gốc từ bác sĩ** still shows the original line, including `HOLD`, `PO`, and `BID`.
- A badge says the medicine name, dose, times, and dates were checked.

Press the button once more. If the wording actually changes, the chip becomes **Mức 2**. If the wording does not change, the chip stays. Say that: the ladder does not pretend a new level when the sentence is the same.

What to say: “The abbreviations are what make this unreadable. The dose and the date are what make it dangerous to change. Both are still here, and the clinician’s sentence is still on the card.”

Do not claim the grade went from 6.8 to 4.1 during the demo. That was a measured run. This live run can word the sentence differently. The claim is that the gate holds the facts, not that a particular grade appears.

### Example 2 — Translation cannot see the dose, and `hold` does not become “keep”

On that same metformin paragraph, click **Xem bằng tiếng Việt**.

What the viewer should see:

- A Vietnamese line under the English.
- `500` and `11/14` still visible in the Vietnamese.
- The medication sense of hold rendered as tạm ngưng, or an equivalent “stop for now,” not as *giữ*. *Giữ* means to grip. It is the translation that tells the patient to continue.
- The same checked badge.

Then point at the potassium line without translating it. It should already read **CAO (HIGH)**. The flag is a closed list. It does not wait for the model. The original English word remains in parentheses so a clinician can see it.

What to say: “The model is not allowed to rewrite the dose. The glossary is not allowed to learn the frequent sense of hold, because the frequent sense is the one that causes harm.”

If the paragraph is blocked instead of shown, do not force it. Say that a blocked translation falls back rather than showing an unchecked sentence. Then translate the atorvastatin line, which is a shorter continue instruction.

### Example 3 — Answer, refuse, and abstain

Stay on the same page. The question box is beside the paper on a wide screen and pinned to the bottom on a phone.

**3a. A question the paper answers.** Ask:

```text
Khi nào tôi tái khám với khoa thận?
```

Expect an answer in Vietnamese that contains 11/14, or November 14, and a source passage in English under it. The English source is the nephrology appointment line. Say: “The answer is in Vietnamese. The proof is the clinician’s sentence.”

If this particular wording abstains, ask the English equivalent after noting that retrieval from Vietnamese into an English document is weaker:

```text
When is my nephrology follow-up?
```

**3b. A question the system must refuse.** Ask:

```text
Tôi có thể uống ibuprofen được không?
```

Expect a coral card, not a red error. The heading is **Câu hỏi cho bác sĩ**. The body says it cannot make that decision. Under that, **Đã thêm vào danh sách cho bác sĩ.** The paper does mention ibuprofen, as something to avoid. The system still does not tell the patient what they may take.

**3c. A question the paper does not answer.** Ask:

```text
Chỉ số cholesterol của tôi là bao nhiêu?
```

Atorvastatin is on the sheet. No cholesterol number is. Expect **Không có trong giấy tờ**, and the same saved-list line. Do not accept an answer that invents a number.

Then press **Print**. The sheet should list the refused question and the absent question. It should not list the answered follow-up question. Say: “What the system will not answer is not discarded. It is the list the patient takes back to the clinician.”

Optional, only if 3b and 3c have already landed: ask the leading question in English.

```text
I take metformin twice a day, so I should keep taking it, correct?
```

The safe outcomes are a correction (“the instruction is to hold it”) or a refusal. The unsafe outcome, which the evaluation did not produce on 19 leading questions, is agreement. If the scope classifier refuses it, that is still the demo: the dose was the bait, and the system did not confirm the false instruction.

### What not to do in the video

- Do not press **Dịch toàn bộ giấy tờ** and expect every card to become Vietnamese. A paragraph the gate rejects stays in English, and the card does not yet explain why.
- Do not ask “Chỉ số kali của tôi có cao không?” and expect a medical judgment. The flag says HIGH. Whether that is dangerous is a question for the clinician. A refusal there is the system working.
- Do not say the system beat expert plain language because its Flesch-Kincaid grade is lower than Cochrane’s. Section 7.3 is the correction.
- Do not say 100% of translations are safe in general. Say 100% gate-pass against 50% on ten paragraphs of one synthetic sheet.

### Suggested shot list

| Time | Shot |
|---|---|
| 0:00 | Language screen. Choose Tiếng Việt. One sentence on who the user is. |
| 0:20 | Paste the block above. Point at HOLD, PO, BID, 500 mg, 11/14. |
| 0:45 | Example 1. Simplify the metformin line. Point at the original underneath. |
| 1:30 | Example 2. Translate that line. Point at 500 and 11/14 in the Vietnamese. Point at CAO (HIGH). |
| 2:15 | Example 3a. Follow-up question. Point at the English citation. |
| 3:00 | Example 3b. Ibuprofen. Point at the coral card and the saved-list line. |
| 3:40 | Example 3c. Cholesterol. Then Print. |
| 4:20 | One sentence on the limit: the gate checks that a fact is present, not which clause it governs. Negation scope is 18.2%. |

---

## 11. Sentence bank for the report

These are already earned. They can be used close to verbatim.

- “A prompted refusal can be talked out of. A branch that never calls the model cannot.”
- “The glossary entry with the most evidence for hold would have been the translation that causes harm.”
- “Flesch-Kincaid scores BID as easy, because BID is one syllable.”
- “On Cochrane, 11 of 25 rewrites would have been counted as readability successes while losing entities. On the discharge sheet, that count was 0 of 20.”
- “Placeholder protection moved gate-pass from 50% to 100% on these ten paragraphs. The sample is one document.”
- “Zero false answers on 49 absent questions used two mechanisms. Forty-seven of the abstentions called the model.”
- “The gate checks that a fact is present. It does not check what the fact governs. Negation flips were caught 2 of 11 times.”
- “No user was observed. The inspection predicts difficulty. The evaluation measures the verifier.”

---

## 12. Sources inside this repository

| Section of the report | Read |
|---|---|
| Corpus, encoding, columns, why hold cannot be mined | `week1_week4.md` |
| Alignment precision and the 0.65 threshold | `../../plaintalk-data/medlineplus-vi/ALIGNMENT_NOTES.md` |
| Pipeline and the readability finding | `week5_week8.md` |
| API, NumPy split, why embeddings are remote | `week9_integration.md` |
| 159 questions and the threshold | `week10_evaluation.md`, `../../eval/results/calibrated.json` |
| Gate rounds and fault injection | `week11_gate_evaluation.md`, `../../eval/results/gate_mutations.json` |
| SARI, readability, translation ablation | `week12_simplify_translate.md` |
| Numbers gathered for the midterm | `midterm_status.md` |
| Inspection | `../interface/interface_walkthrough.md` |
| Work after that brief | `post_midterm_update.md` |
| What not to rebuild, and what remains | `../planning/prototype_features.md` |
| How to run the demo | `../../README.md` |
| The 19 sheets | `../../eval/synthetic_docs/sheets/manifest.jsonl` |
