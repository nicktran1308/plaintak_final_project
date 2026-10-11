# PlainTalk — Progress Report, Weeks 5–8

**Nick Tran · CPSC 597 · Dr. Chang-Huyn Jo**
Continues from `week1_week4.md`

---

## 1. Summary

The backend pipeline is complete. All seven modules are implemented and tested, four weeks ahead of the original schedule.

Every module was built and verified **without an API key**, using injected stub models. This was deliberate: the project's central claim is that refusals and abstentions happen *before* a language model is called, and that property is only testable if the model can be replaced with something that counts its own invocations.

| Module | Purpose | Tests | Planned | Status |
|---|---|---|---|---|
| `intake.py` | PDF to paragraphs, stable IDs | 12 | Week 3 | Complete |
| `gate.py` | Entity check and verdict | 20 | Week 7 | Complete |
| `scope.py` | Advice-seeking classifier | 17 | Week 6 | Complete |
| `retrieve.py` | Chunking, embedding, threshold | — | Week 5 | Complete |
| `chat.py` | Orchestration and abstention | 7 | Week 6 | Complete |
| `simplify.py` | Reading-level ladder | 8 | Week 3 | Complete |
| `translate.py` | Glossary-grounded translation | 22 | Week 8 | Complete |

**86 tests passing**, none requiring network access.

---

## 2. Architecture

The pipeline has two verification layers, and neither is a language model.

**Control-flow exits.** A question passes through a scope classifier and a retrieval threshold. Both exit before generation:

```
question
  → scope.classify()      advice-seeking?   → REFUSE   (no model call)
  → retriever.search()    below threshold?  → ABSTAIN  (no model call)
  → model                 grounded answer with span citation
```

A prompted refusal is advisory and can be argued past by rephrasing. A branch cannot. `Response.model_called` records which path ran, so the property is asserted in tests rather than claimed in prose.

**The entity-check gate.** Every transformation is verified by regex extraction plus clinical NER, compared as sets. Asking a model whether it preserved a dose would reproduce the failure being tested for.

---

## 3. Implementation decisions

### 3.1 Normalization is what makes the gate usable

A *correct* simplification rewrites `500 mg PO BID` as `500 mg by mouth two times a day`. Comparing raw strings would reject every faithful rewrite. Entities are therefore normalized to canonical forms before comparison:

```
BID ≡ twice daily ≡ every 12 hours   →   freq:2/day
11/14 ≡ November 14                  →   date:11-14
PO ≡ by mouth ≡ orally               →   route:oral
```

Without this the gate would block all output, useful and harmful alike.

### 3.2 The gate anchors to the original, not the previous rung

Each simplification rung is compared against rung 0, the clinician's text, rather than against the rung above it. Comparing to the previous rung would allow a dose to drift away gradually, one individually-acceptable step at a time, with every comparison passing.

### 3.3 Scope classification is bilingual by necessity

The patient asks in Vietnamese. Translating the question to English before classifying would require a model call *before* the refusal, defeating the purpose. Patterns are therefore matched in both languages, and `Tôi có thể uống lại metformin không?` refuses with no model contact.

### 3.4 Critical content never reaches the model

Translation protects doses, dates, drug names, and glossary terms with opaque placeholders before generation:

```
source     Hold metformin 500 mg twice daily until you follow up on 11/14.
protected  ⟦0⟧ ⟦1⟧ ⟦2⟧ ⟦3⟧ ⟦4⟧ you follow up on ⟦5⟧.
```

Only `you follow up on` is sent. A model that cannot see `500 mg` cannot drop it, round it, or alter it. This is structurally stronger than checking afterwards, and the gate still checks afterwards.

### 3.5 Layered failure behavior

The gate's regex core covers doses, frequencies, routes, dates, and durations with no external dependency. The scispaCy layer adds drug-name recognition and fails *open*, so an installation problem degrades drug coverage rather than disabling the gate. Everything else fails *closed*.

Verified against the live model:

```
input:  Hold metformin 500 mg PO BID until 11/14.
output: ['date:11-14', 'dose:500mg', 'drug:metformin',
         'freq:2/day', 'route:oral']
```

---

## 4. Findings

Continuing the numbering from `week1_week4.md` §5.

### 4.1 Readability formulas score clinical abbreviations as easy

Measured with Flesch-Kincaid on two sentences from the project's synthetic discharge sheet:

| Sentence | Grade |
|---|---|
| `Hold metformin 500 mg PO BID until you follow up with nephrology on 11/14.` | **5.9** |
| `Decreased urine output or anuria; new or worsening lower-extremity edema; dyspnea or orthopnea.` | **14.9** |

The first sentence is rated as sixth-grade reading level while containing `PO` and `BID`, abbreviations no patient can interpret. The formula counts syllables and sentence length; `BID` is one syllable. The abbreviations that make the sentence unreadable actively lower its score.

This has a direct consequence for evaluation. A simplifier that expands `BID` to `two times a day` — an unambiguous improvement — makes the Flesch-Kincaid score *worse*, because it adds syllables. If readability were the metric, correct simplification would register as failure.

This is measured confirmation of Picton et al. (2025) and Srinivasu et al. (2026) on the limits of surface metrics, and it is the reason every result in this project is reported alongside entity preservation.

### 4.2 Corpus-derived context rules do not generalize to drug names

The reviewed glossary gates the medication sense of `hold` behind a `require_any` list: `medicine, medication, dose, pill, tablet, capsule, insulin`. The sentence `Hold metformin 500 mg twice daily` contains none of those words, so no sense matched and the paragraph blocked.

Enumerating every drug name is not possible. The resolution was to let entity extraction establish context: when a drug entity, dose entity, or frequency entity is detected, synthetic context tokens (`medication`, `dose`, `frequency`) are appended before sense selection runs. The glossary required no edits.

### 4.3 Most glossary terms did not need context gating

An audit found 25 of 28 directive terms configured with `requires` rules, causing them to block outside medication context. Review showed the correct question was not "is this a medication term" but **"would the Vietnamese be wrong if applied elsewhere?"**

Three groups emerged:

- **Genuinely context-dependent** (`hold`, `resume`, `do not resume`, `tablet`) — the Vietnamese is medication-specific. `resume → dùng lại` applied to "do not resume driving" would be wrong.
- **Self-disambiguating in English** (`stop taking`, `skip a dose`, `double dose`) — the phrase already contains the medication context.
- **General-purpose Vietnamese** (`until → cho đến khi`, `at bedtime`, `with food`) — ordinary constructions that work in any sentence.

Twenty-two terms were relaxed to `default`. `hold` retains strict gating and gained a second sense for physical manipulation (`giữ`), deliberately **not** configured as a default: if scispaCy fails to recognise a drug name, the paragraph must block rather than silently resolve to `giữ`, which would reproduce the Kong et al. (2026) inversion.

### 4.4 Stub models surface bugs that live APIs conceal

Back-translation verification was restoring placeholders to *Vietnamese* rather than to the original English, so the gate compared Vietnamese text against English entity patterns and reported every entity as missing.

With a live API this would have produced plausible-looking back-translations and a silent, systematic verification failure. The stub made it immediately visible. Fixed with two restore maps: `restore_vi` for the patient-facing output, `restore_en` for the text the gate inspects.

---

## 5. Corpora and environment

`pdfplumber`, `textstat`, and `reportlab` were added; spaCy remains pinned at 3.7.4 and both scispaCy models verified intact after installation. The dependency hazard recorded in `week1_week4.md` §3 continues to require verification after every install.

A synthetic discharge instruction sheet was generated with a real text layer for intake testing. Intake produced 21 paragraphs, correctly separating all five numbered medication instructions as individual items with line wraps rejoined. Metadata lines (patient name, MRN, signature block) are conservatively classified as headers and excluded from simplification; this is acceptable, as none is content a patient would simplify.

Cochrane is complete. Med-EASi and PLABA remain outstanding and do not block development.

---

## 6. Outstanding items

**Vietnamese scope patterns require native review.** The initial pattern set was derived from English constructions. Manual probing found two misses in the first three test phrasings: `Thuốc này uống được không bác?` (drops the `có` particle) and `Chỉ số này có cao lắm không?` (uses `lắm` where the pattern expected `quá`). Both were classified as informational, meaning they would have reached the model. Under-matching here is a safety failure, and the pattern set needs systematic expansion by a native speaker.

**The `resume` translation is disputed.** The authored entry gives `dùng lại` and explicitly rules out `tiếp tục`. On review the author raised that `dùng lại` reads as "reuse" rather than "restart," and that `tiếp tục` may be correct. The distinction is clinically meaningful: `continue` describes a medication never stopped, `resume` one that was held. This entry has been referred to the second Vietnamese reviewer as a specific question rather than a general check.

---

## 7. Next steps

1. `main.py` with FastAPI routes, an embedding provider, and the Anthropic client — the remaining wiring.
2. Calibrate the retrieval threshold against the adversarial question set. The current 0.45 is a placeholder and requires real embeddings.
3. Frontend implementation.
4. Complete Med-EASi and PLABA downloads.

**Risks.** The retrieval threshold cannot be calibrated until an embedding provider is wired, and calibration determines the project's headline safety metric. The gate's measured catch rate on unseen clinician text remains unknown until Week 12; the 86 tests confirm it catches known failure modes but do not establish performance in the wild.

---

## 8. References

Kong, M., Fernandez, A., Bains, J., et al. (2026). Evaluation of the accuracy and safety of machine translation of patient-specific discharge instructions. *BMJ Quality & Safety*, 35, 150–158.

Picton, B., Andalib, S., Spina, A., et al. (2025). Assessing AI simplification of medical texts. *International Journal of Medical Informatics*, 195, 105743.

Srinivasu, P. N., Samudrala, A., Devesh, P. G., et al. (2026). Quantized low-rank adaptation in large language models for clinical text simplification. *International Journal of Computational Intelligence Systems*, 19, 267.
