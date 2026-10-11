# PlainTalk — Integration Report and Remaining Work

**Nick Tran · CPSC 597 · Dr. Chang-Huyn Jo**
Continues from `week1_week4.md` and `week5_week8.md`

---

## 1. Status

The system runs end to end. Every backend component is implemented, tested, and wired behind a REST API, with live model access confirmed.

| Milestone | Planned | Actual | Status |
|---|---|---|---|
| Corpus construction | Week 2 | Week 2 | Complete |
| Retrieval pipeline | Week 5 | Week 4 | Complete |
| Abstention and scope | Week 6 | Week 4 | Complete |
| Entity-check gate | Week 7 | Week 4 | Complete |
| Translation pipeline | Week 8 | Week 4 | Complete |
| API and integration | Week 10 | Week 4 | Complete |

Six weeks of scheduled work were delivered by the end of Week 4. The remaining Phase 2 item is the frontend.

---

## 2. What was built in this period

### 2.1 Configuration layer (`backend/config.py`)

Centralises API keys, model selection, and thresholds. Reads `.env` without requiring `python-dotenv`, so the project has one fewer dependency in an environment that has proven fragile.

Two choices worth recording:

**Claude Haiku rather than a larger model.** If a small model combined with verification outperforms a large model without it, that is a stronger result for the project's thesis than using the most capable model available.

**Temperature is requested but not required.** The installed SDK rejected `temperature` on `messages.create`, so the client attempts the call with it and falls back without. Determinism is preferable for reproducibility but not essential, and the fallback keeps the project runnable across SDK versions.

### 2.2 API layer (`backend/main.py`)

FastAPI application exposing eight endpoints. All logic remains in `pipeline/`; the routes only marshal input and output.

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Configuration and key presence |
| `POST /api/session` | Create a session, select language |
| `POST /api/upload` | Upload a PDF, returns paragraphs |
| `POST /api/upload_text` | Paste-in path |
| `POST /api/simplify` | Add one ladder rung |
| `POST /api/ask` | Answer, refuse, or abstain |
| `POST /api/translate` | Verified translation |
| `GET /api/handoff` | Deferred questions for the clinician sheet |

Session state is held in a process-local dictionary. There is no database, no account model, and no patient data at rest, per the SRS. State is lost on restart, which is the intended behaviour.

**The `/api/ask` response returns `model_called` deliberately.** It is the evidence that refusals and abstentions never reach the model, exposed so the frontend and the evaluation harness can both assert on it rather than trust it.

**The `/api/simplify` response returns the gate verdict as data.** The client renders one of three states — passed, blocked, or exhausted — from a single response shape. The frontend never decides whether content is safe; it displays what the gate already decided.

### 2.3 Smoke test (`backend/smoke_test.py`)

Exercises the full pipeline against the synthetic discharge sheet and counts API calls per operation, so the zero-cost property of refusals is observable rather than asserted.

---

## 3. Environment findings

### 3.1 The NumPy 1/2 split is a hard constraint on this project

Three separate installations silently broke the clinical NLP stack during development. All three trace to the same root cause.

| Trigger | Mechanism | Resolution |
|---|---|---|
| `medspacy` (Week 1) | Upgraded spaCy 3.7.4 → 3.8.16, invalidating both scispaCy models | Reinstalled spaCy and models; medspaCy removed |
| `sentence-transformers` (Week 4) | Pulled torch, which requires NumPy ≥ 2; spaCy 3.7.4 requires NumPy 1 | Removed torch; embeddings moved to a hosted API |
| `voyageai` SDK (Week 4) | Imports `langchain_text_splitters` → `nltk` → SciPy ≥ 1.14, which requires NumPy 2 | Pinned `scipy<1.14` |

The clinical NLP stack (spaCy 3.7.4, scispaCy 0.5.4, thinc 8.2.3) pins NumPy 1.x. The modern ML ecosystem — PyTorch, recent SciPy, most embedding libraries — requires NumPy 2.x. **These cannot coexist in one environment.**

Because the entity-check gate depends on scispaCy, and the gate is the project's central contribution, the clinical stack takes precedence and everything else adapts around it.

**Working pinned set:** `numpy 1.26.4`, `scipy 1.13.1`, `thinc 8.2.3`, `spacy 3.7.4`, `scispacy 0.5.4`. Locked in `backend/requirements.txt`.

Two of these failures were silent — the package installed successfully and the breakage appeared only on the next model load. This is why the two-model verification is re-run after every install.

### 3.2 This validates the layered-failure design

The gate was built so its regex core requires no external dependency, with scispaCy adding drug-name recognition and failing *open*. That was designed as a robustness measure. In practice the environment broke three times, and on each occasion the regex core — which covers doses, frequencies, routes, dates, and durations — would have continued to function.

The design decision was correct for reasons stronger than anticipated.

### 3.3 Embeddings moved off-device

LaBSE was originally chosen for retrieval because it is cross-lingual and was already a project dependency from corpus alignment. The NumPy conflict made this impossible.

Retrieval now uses the Voyage API (`voyage-3`), which is cross-lingual and requires no local ML runtime. Nothing was lost: LaBSE was needed only for the one-off corpus alignment, which is complete, and its scores are preserved in `pairs_scored.jsonl`.

The trade-off is a second API dependency and a second key. The alternative — translating each question to English before retrieval so an English-only embedder could be used — was rejected because it requires a model call *before* the abstention check, which would undermine the project's central claim.

### 3.4 Readability finding reproduced on the real document

Section 4.1 of `week5_week8.md` reported that Flesch-Kincaid scores clinical abbreviations as easy. This reproduced on the generated PDF rather than a hand-typed string:

```
rung 0 (grade 6.8): 1. HOLD metformin 500 mg PO BID until you follow up...
```

A line containing `HOLD`, `PO`, and `BID` measures at sixth-to-seventh grade. The finding is not an artefact of the test sentence.

---

## 4. Current system state

```
backend/
  config.py            API keys, model selection, thresholds
  main.py              8 REST endpoints
  smoke_test.py        end-to-end verification with call counting
  pipeline/
    intake.py          PDF → paragraphs           12 tests
    gate.py            entity check + verdict     20 tests
    scope.py           advice-seeking classifier  17 tests
    retrieve.py        chunk, embed, threshold     —
    chat.py            orchestration, abstention   7 tests
    simplify.py        reading-level ladder        8 tests
    translate.py       glossary-grounded MT       22 tests
  data/
    glossary_directive_DONE.jsonl    28 terms, 21 safety-critical
```

**86 tests pass without network access.** Every module accepts an injected model, so the entire pipeline is verifiable offline. This is what allowed the back-translation bug (§4.4, `week5_week8.md`) to be caught — with a live API it would have produced plausible output and failed silently.

Verified working end to end: intake of the synthetic PDF (21 paragraphs, 11 content), Voyage embedding of 21 chunks, ladder initialisation with readability scoring, and live Claude access.

---

## 5. Remaining work

### 5.1 Adversarial question set — highest priority

**Blocks:** threshold calibration, false-answer rate, the entire evaluation.

Approximately 150 questions in four categories, in English and Vietnamese:

| Category | Expected behaviour | Purpose |
|---|---|---|
| Answerable | Answer with span citation | Confirms the system is useful, not merely cautious |
| Plausible-but-absent | Abstain | **The headline safety metric** |
| Advice-seeking | Refuse before generation | Scope boundary enforcement |
| Leading / false premise | Correct, never confirm | Sycophancy resistance |

The plausible-but-absent category is the most demanding to author. Questions must be topically close to the document — asking about cholesterol when the document reports glucose — so that retrieval is tempted rather than obviously unrelated.

This is authoring work that cannot be delegated and cannot be shortened. It is the longest-lead item remaining.

### 5.2 Threshold calibration

The current retrieval threshold of 0.45 is a placeholder chosen before real embeddings existed. Calibration requires sweeping thresholds against the adversarial set and selecting the point that minimises false answers on absent-information questions while keeping answerable questions answerable.

Both failure directions must be reported: a threshold that abstains on everything achieves a perfect false-answer rate and is useless.

### 5.3 Frontend

Ten components. The document view, chat with the three response states, and the printable bilingual handoff sheet.

`Deferred.jsx` — the refusal and abstention component — should be built first. It is the state the project is actually about, and the rest of the interface follows from getting it right.

### 5.4 Vietnamese scope patterns

The pattern set was derived from English constructions and requires systematic native review. Manual probing found two misses in the first three phrasings tested:

- `Thuốc này uống được không bác?` — drops the `có` particle the pattern expected
- `Chỉ số này có cao lắm không?` — uses `lắm` where the pattern expected `quá`

Both were classified as informational, meaning both would have reached the model. Under-matching here is a safety failure. Every pattern added should be logged with its rationale; the count and character of the additions is itself a reportable result.

### 5.5 Second-reviewer verification

The `resume` entry gives `dùng lại` and explicitly rules out `tiếp tục`. On review the author raised that `dùng lại` reads as "reuse" rather than "restart." The distinction is clinically meaningful: `continue` describes a medication never stopped, `resume` one that was held. Referred to the second Vietnamese reviewer as a specific question.

### 5.6 Remaining reference corpora

Med-EASi and PLABA. Needed for Week 11 evaluation only; neither blocks development.

---

## 6. Revised schedule

| Week | Task | Status |
|---|---|---|
| 1–4 | Foundation, corpus, glossary | Complete |
| 4 | Full backend pipeline and API | Complete, ~6 weeks early |
| 5–6 | Adversarial question set; Vietnamese pattern review | **Next** |
| 6–7 | Frontend implementation | |
| 8 | Threshold calibration | |
| 9–10 | Buffer, second-reviewer verification, remaining corpora | |
| 11 | Full quantitative evaluation | |
| 12 | Manual error annotation; gate precision and recall | |
| 13 | Interface inspection | |
| 14 | Refinement; freeze system and results | |
| 15–16 | Documentation, report, demonstration | |

Roughly four weeks of slack now exist. The deferral of DailyMed and persistent storage (§2, `week1_week4.md`) accounts for part of it; the remainder came from building the safety machinery before the interface, which meant no rework when components were wired together.

---

## 7. Risks

**The adversarial set is on the critical path and cannot be parallelised.** Calibration, the false-answer rate, and the gate evaluation all depend on it. Mitigated by the available slack, but it should be started immediately rather than treated as an evaluation-phase task.

**The gate's catch rate on unseen text is unknown.** 86 tests confirm it catches documented failure modes; they establish nothing about clinician free-text it has not seen. An unflattering number in Week 12 remains a valid result, since measuring the gate's limits is a stated contribution rather than an incidental check.

**Vietnamese pattern coverage is unquantified.** Two misses in three probes suggests the initial set is materially incomplete. The true miss rate will not be known until the Vietnamese adversarial questions are written and run.

**Environment fragility is ongoing.** Three silent breaks occurred in four weeks. Any future install can recur the problem, so the pinned `requirements.txt` and the post-install verification step must both be maintained.

---

## 8. References

Kong, M., Fernandez, A., Bains, J., et al. (2026). Evaluation of the accuracy and safety of machine translation of patient-specific discharge instructions. *BMJ Quality & Safety*, 35, 150–158.

Picton, B., Andalib, S., Spina, A., et al. (2025). Assessing AI simplification of medical texts. *International Journal of Medical Informatics*, 195, 105743.

Srinivasu, P. N., Samudrala, A., Devesh, P. G., et al. (2026). Quantized low-rank adaptation in large language models for clinical text simplification. *International Journal of Computational Intelligence Systems*, 19, 267.
