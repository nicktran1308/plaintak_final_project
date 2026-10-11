# PlainTalk — Simplification and Translation Evaluation, Week 12

**Nick Tran · CPSC 597 · Dr. Chang-Huyn Jo**
Continues from `week1_week4.md`, `week5_week8.md`, `week9_integration.md`, `week10_evaluation.md`, and `week11_gate_evaluation.md`

---

## 1. Status

All five evaluation components are complete. Every quantitative claim the proposal makes now has a measurement behind it.

| Component | Harness | Status |
|---|---|---|
| Question answering and abstention | `run_qa_eval.py` | Complete (Week 10) |
| Entity-check gate, blind annotation | `run_gate_eval.py` | Complete (Week 11) |
| Gate sensitivity, fault injection | `run_gate_mutations.py` | Complete (Week 11) |
| Simplification | `run_simplify_eval.py` | Complete |
| Translation ablation | `run_translate_eval.py` | Complete |

Remaining work is inspection, verification, and writing.

---

## 2. Simplification

### 2.1 Method

Quality is reported in two tiers, because the corpora that carry gold plain-language references are biomedical abstracts rather than the discharge instructions this system targets.

**Reference-based.** SARI against Cochrane, Med-EASi, and PLABA.

**Reference-free.** Readability change and entity preservation on the synthetic discharge sheet, where no gold simplification exists.

**Every readability figure is reported beside entity preservation.** This is not a presentation choice. It follows from the finding in `week5_week8.md` §4.1: Flesch-Kincaid scores the sentence *"HOLD metformin 500 mg PO BID until you follow up with nephrology on 11/14"* at grade 6.8, because `BID` is one syllable and `PO` is two letters. The abbreviations that make the sentence unreadable actively lower its score, so a simplifier that expands `BID` to *"two times a day"* makes the number worse. A system optimised against readability alone would be optimised backwards.

### 2.2 A note on BERTScore

The proposal names BERTScore. It is not computed, and the substitution is recorded here rather than passed over.

BERTScore requires PyTorch, PyTorch requires NumPy 2, and the pinned clinical NLP stack (spaCy 3.7.4, scispaCy 0.5.4, thinc 8.2.3) requires NumPy 1. These cannot coexist in one environment, as documented in `week9_integration.md` §3.1. The entity-check gate depends on scispaCy and is the project's central contribution, so the clinical stack takes precedence.

Semantic similarity is available instead as cosine over voyage-3 embeddings, which requires no local ML runtime. It is labelled as such throughout and is not reported as BERTScore.

SARI is implemented directly rather than imported, for the same reason: the reference implementations ship inside frameworks that pull in PyTorch. The implementation was verified against known behaviour, scoring 100.0 on a gold reference, 59.3 on an unchanged copy of the source, and 12.0 on unrelated text.

### 2.3 Results

Twenty-five pairs per corpus at ladder level 2; the target-domain tier covers all ten content paragraphs at levels 1 and 2.

| corpus | granularity | SARI | readability | entity preservation | gate pass |
|---|---|---|---|---|---|
| **synthetic discharge** | target domain | — | 11.6 → 7.4 | **97.9%** | **100.0%** |
| **Med-EASi** | sentence, clinical | 45.02 | 14.7 → 8.2 | 80.0% | 88.0% |
| **PLABA** | patient-facing abstracts | 34.60 | 15.4 → 6.4 | 75.4% | 64.0% |
| **Cochrane** | paragraph, abstracts | 37.01 | 11.6 → 6.7 | 76.5% | 56.0% |

Readability improves substantially on every corpus, between four and nine grade levels.

---

## 3. Findings

Continuing the numbering from `week11_gate_evaluation.md` §3.

### 3.1 Gate pass rate tracks domain proximity

The ordering in the table above is not incidental. Ranked by how close each corpus sits to a discharge instruction sheet, the gate pass rate falls monotonically:

```
discharge instructions   100%    the target domain
sentence-level clinical   88%    Med-EASi
patient-facing abstracts  64%    PLABA
paragraph abstracts       56%    Cochrane
```

Readability gains are comparable across all four, so the difference is fidelity rather than difficulty. The gate is calibrated for clinical instruction text and degrades predictably outside it.

This ordering is stronger evidence than any single figure. It shows the system is fitted to its stated domain, and it bounds where the results generalise: nothing here establishes that the gate would behave this way on research abstracts, and it measurably does not.

### 3.2 Some out-of-domain entity losses are gate false positives

The Cochrane and PLABA preservation figures understate true fidelity. Inspection of individual blocks found clinical NER tagging non-drugs as chemicals in abstract prose:

```
drug:spiritually-framed
drug:levonorgestrel-releasi     (truncated span)
drug:t3
```

*Spiritually-framed* is not a medication. These are the same class of defect as the `DOB` false positive in `week11_gate_evaluation.md` §2.2, appearing on a different kind of text.

The honest statement is that entity preservation measures 76.5% on Cochrane and 75.4% on PLABA, that some proportion of those losses are NER false positives on non-clinical terminology, and that target-domain preservation of 97.9% is the figure relevant to the deployed system.

### 3.3 Gold plain-language references score worse on readability than their sources

Measured on all three reference corpora:

| corpus | source | gold reference | this system |
|---|---|---|---|
| Cochrane | 11.6 | **12.9** | 6.7 |
| Med-EASi | 14.7 | 11.7 | 8.2 |
| PLABA | 15.4 | 13.7 | 6.4 |

The Cochrane result is the striking one. Cochrane plain-language summaries are written by domain experts for the explicit purpose of being readable by non-specialists, and Flesch-Kincaid rates them **harder than the technical abstracts they simplify**.

In all three corpora this system's output scores better than the human gold standard. That must not be read as the system outperforming expert simplification. It shows the opposite of what the number appears to say: the metric does not measure what it purports to. This system's output is shorter with simpler words; the gold references preserve nuance and hedging that the formula penalises as complexity.

This is the readability-formula critique of Picton et al. (2025) and Srinivasu et al. (2026) demonstrated on three published corpora rather than on a single hand-chosen sentence.

### 3.4 The readability-plus-fidelity pairing is measurable, not rhetorical

The harness counts rewrites where readability improved **and** the gate blocked. Each one would score as a success on readability alone:

| corpus | improved but lost entities |
|---|---|
| Cochrane | 11 of 25 |
| PLABA | 9 of 25 |
| Med-EASi | 3 of 25 |
| synthetic discharge | 0 of 20 |

On the out-of-domain corpora, close to half of all rewrites fall into this category. A system reporting readability alone would claim a four-to-nine grade-level improvement while silently losing doses in nearly half its output.

### 3.5 Readability sometimes gets worse on correct output

One rewrite in each corpus produced a higher grade score than its source. Expanding an abbreviation adds syllables, so a faithful expansion of `BID` or `QHS` raises the number. Reported alongside entity preservation, these are visible as correct; reported alone, they would look like regressions.

### 3.6 The ladder does not always produce distinct rungs

On the target-domain run, five of ten paragraphs produced identical text at levels 1 and 2. The ladder offers up to three rungs; it does not guarantee three distinct versions, and the interface should not imply otherwise.

---

## 4. Translation ablation

### 4.1 Method

The terminology-grounded pipeline is substantially more work than asking a model to translate: a hand-authored glossary verified by a second speaker, placeholder protection, retrieved exemplars, and two verification passes. This experiment tests whether that work was necessary, and could have refuted the architecture.

Three arms, scored identically by the entity-check gate operating on the Vietnamese output and its back-translation. The gate does not know which arm produced the text.

| arm | configuration |
|---|---|
| **naive** | the model translates freely. No glossary, no protection. This is what a patient gets from a general-purpose tool. |
| **protected** | placeholder substitution only. Doses, dates and drug names never reach the model; verified glossary terms are inserted rather than generated. |
| **full** | protection plus professionally translated exemplars in the prompt. |

### 4.2 Results

Ten content paragraphs, all three arms.

| arm | gate pass | entity preservation | literal survival | forbidden renderings |
|---|---|---|---|---|
| naive | **50%** | 87% | 100% | 0 |
| protected | **100%** | **100%** | 100% | 0 |
| full | 90% | 97% | 100% | 0 |

**Naive translation failed half the paragraphs. Protection passed all of them.**

Block reasons for the naive arm: three literal-check failures and two back-translation failures. The literal failures are the important ones — a dose or date that did not appear verbatim in the Vietnamese output. That is the failure class Srinivasu et al. (2026) documented, occurring in real output from a current model, and it is the class placeholder protection makes structurally impossible rather than merely unlikely.

### 4.3 The exemplar arm is under-tested and its result should not be reported as a finding

The full arm scored below protected: 90% against 100%. It would be convenient to read this as exemplars harming performance. That reading is not supported.

The harness supplies four exemplars taken from the top of the corpus file, without retrieval. The deployed system retrieves semantically similar pairs; four fixed pairs about unrelated topics are prompt noise rather than guidance. The single block also sits within the range of model nondeterminism at n=10, and temperature could not be disabled on the installed SDK (`week9_integration.md` §2.1).

The accurate statement is that the exemplar arm was not tested in its deployed configuration, and no conclusion is drawn about it. Retrieval-backed exemplar evaluation is deferred.

### 4.4 No forbidden renderings occurred in any arm

The glossary marks `giữ` as a prohibited rendering of `hold`, because Kong et al. (2026) documented *"hold the kidney medicine"* translated as an instruction to continue taking it as an error with potential for clinical harm.

Zero violations occurred, including in the naive arm. The model did not make this specific error on this document. That is worth stating plainly rather than implying the protection prevented an error that did not arise: on these ten paragraphs, the naive arm's failures were dropped doses and meaning drift caught by back-translation, not the sense inversion the glossary specifically targets.

The protection remains justified by §4.2. It is justified by measured dose loss, not by a hypothetical inversion.

---

## 5. Outstanding work

**Interface inspection.** Cognitive walkthroughs against three personas, and heuristic evaluation against WCAG 2.2 and senior-friendly guidance. This is what the proposal commits to in place of user testing. No code required.

**Second-reviewer verification.** The `resume` glossary entry remains disputed, and the full set of 28 directive terms has not had an independent pass.

**Vietnamese scope patterns.** Two known colloquial misses remain, and the measured miss rate is a lower bound because the evaluation set uses standard register.

**Optional.** Bare-numeral tracking would address the 0% rounding detection in `week11_gate_evaluation.md` §3.3.

**Deliverables.** Final report, system documentation, demonstration video, presentation.

---

## 6. Risks

**All evaluation rests on one synthetic document.** Every gate and translation figure derives from a single discharge instruction sheet. Its structure is representative and the generator is available to produce more, but the sample is one document. The simplification tier is broader, covering three external corpora, which partially mitigates this for that component only.

**The gate's real-world catch rate remains unmeasured.** No natural fidelity failure occurred in the blind-annotation corpus, so fault injection is the substitute and not an equivalent.

**Negation scope is the weakest measured behaviour** at 18.2% detection, and it is the Kong et al. harm class.

---

## 7. References

Kong, M., Fernandez, A., Bains, J., et al. (2026). Evaluation of the accuracy and safety of machine translation of patient-specific discharge instructions. *BMJ Quality & Safety*, 35, 150–158.

Makhmutova, L., Salton, G., Perez-Tellez, F., & Ross, R. (2024). Automated medical text simplification for enhanced patient access. *BIOSTEC 2024 (HEALTHINF)*, 208–218.

Picton, B., Andalib, S., Spina, A., et al. (2025). Assessing AI simplification of medical texts. *International Journal of Medical Informatics*, 195, 105743.

Srinivasu, P. N., Samudrala, A., Devesh, P. G., et al. (2026). Quantized low-rank adaptation in large language models for clinical text simplification. *International Journal of Computational Intelligence Systems*, 19, 267.

Xu, W., Napoles, C., Pavlick, E., Chen, Q., & Callison-Burch, C. (2016). Optimizing statistical machine translation for text simplification. *Transactions of the ACL*, 4, 401–415.
