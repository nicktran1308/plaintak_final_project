# PlainTalk — Progress Report, Weeks 1–4

**Nick Tran · CPSC 597 · Dr. Chang-Huyn Jo**
Bridging Health Literacy Gaps Through Grounded Text Simplification

---

## 1. Summary

The project is on schedule. Phase 1 (Foundation, Weeks 1–4) is complete, and the first Phase 2 component was delivered early.

The plan called for building the evaluation infrastructure before any prompt engineering, so that later design decisions would be measured rather than guessed. That ordering held, and it paid off: the corpus work surfaced five findings that changed the system's design, including one that would have encoded a documented clinical-harm case directly into the translation glossary.

| Deliverable | Planned | Status |
|---|---|---|
| Literature review | Week 1 | Complete |
| Environment and API access | Week 1 | Complete |
| English–Vietnamese corpus | Week 2 | Complete |
| Reference corpora | Week 1 | 2 of 4 complete |
| Terminology glossary | Week 2 | Mined tier complete; directive tier in authoring |
| Simplification pipeline | Week 3 | Not started |
| Evaluation harness | Week 3 | Not started |
| Entity-check gate | Week 7 | **Complete, ahead of schedule** |

---

## 2. Scope decisions made since the proposal

**Verified language pair: English to Vietnamese.** The architecture is language-agnostic, but each supported language requires a hand-built glossary and exemplar corpus. Vietnamese was selected because prior work summarized by Kong et al. (2026) found both ChatGPT and Google Translate significantly less accurate in Vietnamese than in Spanish, making it the pair where verification matters most.

**Two components deferred to future work** to keep the safety machinery within one semester: DailyMed as a second grounding source with conflict surfacing, and persistent longitudinal storage. Both require an account and identity model, and therefore a considered approach to protected health information. Their removal frees roughly one and a half weeks in Phase 2.

---

## 3. Environment

Python 3.12 in a project-local virtual environment, locked in `backend/requirements.txt`.

| Component | Version | Role |
|---|---|---|
| spaCy | 3.7.4 (pinned) | NLP runtime |
| scispaCy | 0.5.4 | Clinical model loader |
| `en_ner_bc5cdr_md` | 0.5.4 | Drug recognition for the gate |
| LaBSE (sentence-transformers) | — | Cross-lingual alignment scoring |

**A dependency hazard worth recording:** installing medspaCy silently upgraded spaCy to 3.8.16 and broke both scispaCy models. Recovery required reinstalling spaCy 3.7.4 and both models afterward. Any package depending on spaCy can trigger this, so the two-model load is re-verified after every install. medspaCy is not currently used.

---

## 4. Corpus construction

### 4.1 English–Vietnamese parallel corpus

No large Vietnamese medical parallel corpus exists. The simplification corpora in the literature are English, with MultiCochrane adding Spanish, French, and Farsi. The MedlinePlus multilingual collection was therefore built into a corpus with a purpose-written scraper.

MedlinePlus is only an index; documents were retrieved from cdc.gov, fda.gov, cancer.org, immunize.org, and Health Information Translations. Download completed at 649 successes against 40 failures (~6%, all dead links).

| Artifact | Count | Purpose |
|---|---|---|
| `manifest.jsonl` | 440 records | Provenance |
| Source PDFs | 406 documents, 210 MB | Raw material |
| `pairs.jsonl` | 5,903 | Raw aligned blocks |
| `pairs_dedup.jsonl` | 3,740 | After removing 36.6% duplicates |
| `pairs_scored.jsonl` | 3,578 | Each record carries a LaBSE cosine |
| `pairs_exemplars.jsonl` | ~2,800 | Usable set, cosine ≥ 0.65 |

Three implementation faults were found and fixed during the build, each of which would have produced silently wrong output:

1. **Character encoding.** MedlinePlus serves `text/html` without a charset declaration, so the HTTP client defaulted to ISO-8859-1 per specification. Vietnamese link text arrived as mojibake and never matched the parser's suffix patterns, while ASCII English suffixes matched normally. The first index run returned 257 records, all unpaired. Forcing UTF-8 yielded 440 records: 183 bilingual, 257 paired, 0 unpaired.

2. **Document layout.** The extractor assumed bilingual PDFs interleave languages vertically. In fact 175 of 179 are two-column side-by-side. Straight-across text extraction glued each English fragment to its Vietnamese counterpart. A column-splitting pass now detects the vertical gutter, reads each column separately, and assigns Vietnamese blocks to their best-overlapping English block.

3. **File-type dispatch.** Type was inferred from file extension, but the manifest stores one format per record, so a document with an English HTML link and a Vietnamese PDF link saved HTML under a `.pdf` suffix. Dispatch now inspects the file header.

### 4.2 Alignment verification

Alignment quality was measured rather than assumed. Twenty records were manually labeled, LaBSE cosine similarity was computed for all 3,578 bilingual records, and the threshold was calibrated against the labels.

Cosine scoring outperformed the length-ratio heuristic it replaced in both directions: it removed 360 records the ratio filter had admitted (including *"The kidneys make urine"* paired with an unrelated sentence at cosine 0.110) and rescued 470 the ratio filter had wrongly excluded for being short — a category that matters here, because short strings are where glossary terms live.

Measured precision on held-out manual review is approximately 80%.

### 4.3 Reference corpora

| Corpus | Status | Detail |
|---|---|---|
| Cochrane | Complete | 3,568 / 411 / 480 splits |
| Med-EASi | Pending | Straightforward load |
| PLABA | Pending | Manual download |

**A reproducibility note:** the HuggingFace GEM Cochrane repository relies on a loading script that current `datasets` versions reject. The data was obtained instead from the authors' GitHub repository as line-aligned `.source` / `.target` / `.doi` files, with split counts matching the published figures exactly.

---

## 5. Findings

These emerged from building the corpus and are reportable results, not implementation notes.

### 5.1 Frequency and sense are orthogonal

A candidate glossary term was required to appear in at least five distinct documents, on the reasoning that an individual translator's error will not recur across independent translations. This works for its intended case: `latching on → bám` (the clinically correct term is *ngậm bắt vú*) appears in one document and is excluded.

It is structurally blind to a different failure. The term `hold` appears in 33 documents at Dice 0.506 and clears the threshold comfortably — because the physical-manipulation sense ("hold both crutches on your injured side") is genuinely correct and genuinely recurs. Frequency evidence says nothing about which *sense* is being attested.

This is why the hand-authored glossary tier must be a separate mechanism rather than a fallback for terms with thin evidence.

### 5.2 Automatic glossary mining would have encoded a documented harm case

All 75 corpus occurrences of `hold` are physical manipulation, rendering as *giữ* (keep, grip). In a medication context, `hold` means **stop**; the corpus supports *ngưng* in exactly one record.

A flat `{term: translation}` glossary would therefore have encoded `hold → giữ` with 75 records of supporting evidence. Kong et al. (2026) documented precisely this inversion — *"hold the kidney medicine"* rendered as an instruction to continue it — as a translation error with potential for clinical harm.

The glossary schema was consequently redesigned to carry multiple senses per term, each with a context rule, so that sense selection happens at translation time rather than through dictionary lookup.

### 5.3 A silent omission is worse than a flagged uncertainty

An early glossary builder dropped `hold` entirely through a generic deduplication heuristic, producing an output file that appeared normal. Safety-critical terms are now exempt from that filter, and the builder raises a hard error if any listed safety term is absent from its output. This is the same fail-closed principle the gate applies.

### 5.4 Semantic similarity cannot detect content addition

LaBSE reliably detects missing content but scores 0.80–0.87 on records where the Vietnamese contains the correct translation *plus* extra material, because the correct content is present. Manual review confirmed this: three of five labeled defects were content additions.

This independently reproduces Srinivasu et al.'s (2026) finding that embedding similarity does not establish factual equivalence, and it is the direct argument for an entity-based gate over BERTScore.

### 5.5 Professionally translated source material contains terminology errors

Manual review of twenty records found two cases where alignment was correct but the published translation was wrong: `latching on → bám`, and *"talk to you about your surgery"* rendered as *kết quả phẫu thuật* (surgical **results**).

No alignment filter can detect these; the pipeline performed correctly and the source is at fault. Measured precision of ~80% therefore has a ceiling set by source translation quality rather than by the alignment method. This matters for the project's premise: professionally translated material was treated as the trustworthy baseline against which glossary entries are verified, and that baseline is imperfect.

### 5.6 The corpus contains almost no medication-directive language

Measured across 3,740 records:

| Category | Occurrences |
|---|---|
| `do not` / `don't` | 341 |
| `hold` | 109 (all physical sense) |
| `stop taking` / `keep taking` | 54 |
| `every N hours` | 21 |
| Dosage patterns (`\d+ mg\|ml\|mcg\|units`) | 15 |
| Dosing frequency (`twice daily`, etc.) | **0** |

The corpus is patient-education prose, not directive medication text. It cannot supply medication-instruction terminology, and no additional filtering changes this. The ~28 directive terms are therefore hand-authored from FDA medication guides and independently verified by a second Vietnamese speaker — a decision now supported by measurement rather than assumption.

---

## 6. Implemented components

### 6.1 Entity-check gate (`backend/pipeline/gate.py`) — complete

Scheduled for Week 7, delivered in Week 4. The gate decides whether a transformed span may be shown to the patient or whether the system falls back to the clinician's original text.

**No language model is called.** Asking a model whether it preserved a dose reproduces the failure being tested for. Extraction is regex plus clinical NER; comparison is deterministic set logic.

**Normalization is the central design decision.** A correct simplification rewrites `500 mg PO BID` as `500 mg by mouth two times a day`. Comparing raw strings would reject every faithful rewrite, so entities normalize to canonical forms before comparison:

```
BID ≡ twice daily ≡ every 12 hours   →   freq:2/day
11/14 ≡ November 14                  →   date:11-14
```

**Two verification modes.** Same-language checking runs NER on both texts. Because clinical NER models are English-only, translations are verified in two passes instead: a literal-string check of numbers, units, and dates directly against the Vietnamese, and an entity comparison against an English back-translation. A span passes only if both pass.

**Layered failure behavior.** The regex core covers doses, frequencies, routes, dates, and durations with no external dependency. The scispaCy layer adds drug-name recognition and fails *open*, so an installation problem degrades drug coverage rather than disabling the gate. Everything else fails *closed*.

**Test coverage: 20 of 20 passing.** Each case is a documented failure mode or a faithful rewrite that must be allowed:

| Case | Expected | Source |
|---|---|---|
| Faithful rewrite with normalized frequency | Pass | — |
| Dropped dose | Block | Srinivasu et al. 2026 |
| Altered dose (500 → 50 mg) | Block | — |
| Invented dose not in source | Block | Makhmutova et al. 2024 |
| Negation removed | Block | — |
| Negation reworded (`do not` → `avoid`) | Pass | — |
| `hold → giữ` in translation | Block | Kong et al. 2026 |
| Negation lost in back-translation | Block | Kong et al. 2026 |

Verified against the live scispaCy model:

```
input:  Hold metformin 500 mg PO BID until 11/14.
output: ['date:11-14', 'dose:500mg', 'drug:metformin',
         'freq:2/day', 'route:oral']
```

**Stated limitation.** Negation detection counts markers and flags polarity reversal but does not track scope; a sentence with multiple negations where only one flips would not be caught. Proper handling requires dependency parsing via medspaCy's ConText module, which is deferred because of the dependency hazard in §3.

### 6.2 Glossary

The mined tier yielded 539 candidates clearing the five-document threshold, of which 115 are flagged for having a rival Vietnamese rendering. Terms are recovered statistically by Dice coefficient over document sets, since the corpus is block-aligned rather than word-aligned.

The directive tier scaffold contains 28 terms with empty Vietnamese fields, 21 marked safety-critical, awaiting hand authoring and independent review.

---

## 7. Revised schedule

Weeks 1–4 complete. The gate arriving three weeks early, plus the deferral of DailyMed and persistent storage, creates roughly two weeks of slack in Phase 2.

| Week | Task | Status |
|---|---|---|
| 5 | Retrieval and grounding pipeline | Next |
| 6 | Abstention path and scope classifier | |
| 7 | ~~Entity-check gate~~ | **Done (Week 4)** |
| 8 | Translation pipeline; extend gate to translations | Blocked on directive glossary |
| 9–10 | Frontend and end-to-end integration | |
| 11 | Full quantitative evaluation | |
| 12 | Manual error annotation; gate precision and recall | |
| 13 | Interface inspection | |
| 14 | Refinement; freeze system and results | |
| 15–16 | Documentation, report, demonstration | |

**Immediate next steps**

1. Author the 28 directive glossary terms and arrange independent verification. This is the only blocker on `translate.py`.
2. Implement `retrieve.py`, `scope.py`, and `chat.py` — the abstention path, which produces the project's headline safety metric.
3. Complete the Med-EASi and PLABA downloads. Neither blocks backend work.

**Risks**

*Directive glossary authoring depends on a second reviewer.* Mitigated by the slack gained from the early gate delivery.

*The gate's measured catch rate is unknown until Week 12.* The 20 test cases confirm it catches known failure modes; they do not establish performance on unseen clinician text. An unflattering number remains a valid result, since measuring the gate's limits is itself a stated contribution.

---

## 8. References

Kong, M., Fernandez, A., Bains, J., et al. (2026). Evaluation of the accuracy and safety of machine translation of patient-specific discharge instructions. *BMJ Quality & Safety*, 35, 150–158.

Makhmutova, L., Salton, G., Perez-Tellez, F., & Ross, R. (2024). Automated medical text simplification for enhanced patient access. *BIOSTEC 2024 (HEALTHINF)*, 208–218.

Picton, B., Andalib, S., Spina, A., et al. (2025). Assessing AI simplification of medical texts. *International Journal of Medical Informatics*, 195, 105743.

Srinivasu, P. N., Samudrala, A., Devesh, P. G., et al. (2026). Quantized low-rank adaptation in large language models for clinical text simplification. *International Journal of Computational Intelligence Systems*, 19, 267.
