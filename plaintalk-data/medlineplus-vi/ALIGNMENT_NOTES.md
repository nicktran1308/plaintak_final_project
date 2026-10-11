# Alignment and quality notes: MedlinePlus Vietnamese corpus

PlainTalk — CPSC 597, Week 2 deliverable

This note documents how the English/Vietnamese sentence pairs in
`pairs_exemplars.jsonl` were produced, how accurate they are, and what the
measured error rate does and does not justify. It is written to be read before
anyone relies on this corpus for glossary construction or as few-shot examples
in a translation pipeline. The short version: the corpus is usable, roughly one
record in five is defective, and the remaining errors are mostly not fixable by
better engineering.

## 1. Where the data comes from

MedlinePlus publishes an index of Vietnamese-language patient education
material. It hosts almost none of it; the documents live on cdc.gov, fda.gov,
cancer.org, immunize.org, and Health Information Translations. The index was
parsed into a manifest, the documents were downloaded, and aligned text was
extracted from them.

| Stage | Records |
|---|---|
| Index entries (after URL deduplication) | 305 |
| Files downloaded successfully | 649 (40 failed, ~6%, dead links) |
| Raw extracted pairs | 5,903 |
| After removing duplicate `(en, vi)` text | 3,740 |
| Bilingual records scored for alignment | 3,578 |
| **Final exemplar set** | **2,956** |

The 36.6% duplication rate in the raw output is an artifact of the index, which
lists the same document under every topic it belongs to. `Heart Cath and Heart
Angioplasty`, for example, appears under Angioplasty, Coronary Artery Disease,
Heart Diseases, and Heart Health Tests.

The final set spans 114 documents across 81 topics.

## 2. Why alignment is non-trivial here

The highest-value documents are bilingual PDFs from Health Information
Translations: 175 of 179 place English and Vietnamese in **two side-by-side
columns on the same row**, rather than interleaving them vertically. A naive
text extraction reads straight across the page and glues each English fragment
to its Vietnamese fragment, producing lines that belong to neither language.

The extractor therefore locates the vertical gutter, reads each column
separately, groups lines into paragraph blocks, and pairs blocks by vertical
position. This works, but introduces the dominant failure mode:

> Vietnamese renders taller than English. Each Vietnamese block therefore sits
> slightly lower than its English counterpart, and **the offset accumulates down
> the page**. Past a certain drift, the *previous* Vietnamese block overlaps the
> English block more than the correct one does, and the pairing silently shifts
> by one item.

Because the substituted block is usually a sibling list item of near-identical
length, a length-ratio filter cannot detect this by construction. An
order-preserving (Needleman–Wunsch) alignment was also tried and did **not** fix
it: the whole column is uniformly offset, so order-preserving alignment
reproduces the shift consistently rather than correcting it. That negative
result is recorded here so it is not re-attempted.

## 3. Filtering method

Two filters produce the exemplar set from the 3,578 scored bilingual records.

**LaBSE cosine similarity.** Both sides of each pair are embedded with
`sentence-transformers/LaBSE`, which maps many languages into a shared space, and
the pair is scored by cosine similarity. A block substituted from elsewhere on
the page scores low regardless of its length or position, which is precisely the
failure a length ratio misses. Records scoring below the threshold are dropped.

**List-number consistency.** Where both sides begin with a list number, the
numbers must agree. This catches a specific case LaBSE cannot: a Vietnamese block
that contains the correct translation *plus* a prepended extra item still scores
high, because the correct content is present. Eight records were removed this
way.

Scores for every record are retained in `pairs_scored.jsonl`, so the threshold
can be changed without re-running the model.

## 4. Threshold: 0.65, and an honest account of how it was chosen

**The first threshold was chosen badly, and the error is worth stating plainly.**

An initial cutoff of 0.72 was derived from 20 hand-labelled records. On that
sample, every correct pair scored ≥ 0.750 and every incorrect one ≤ 0.703, and
0.72 is the midpoint of that gap. The separation looked perfect. It was not:
**the same 20 records were used both to select the threshold and to validate it**,
so the reported accuracy was circular and guaranteed to look good. No independent
evidence supported 0.72.

A second round of 20 labels, drawn from records not previously seen and sampled
deliberately either side of the cutoff, overturned it:

| Sample | Result |
|---|---|
| 10 well above the cutoff | 8 good, 2 defective (20%) |
| 5 just above (0.72–0.78) | 4 good, 1 defective (20%) |
| 5 just below (0.62–0.72), rejected | 3 good, 2 defective |

The defect rate immediately above the cutoff was the same as well above it, and
**60% of what the filter rejected was in fact good**. The cosine score does not
cleanly separate correct from incorrect pairs at any threshold in this range.

The threshold was therefore lowered to **0.65**, on the reasoning that if the
defect rate is comparable either side of the boundary, the larger set gives
better retrieval diversity at no measurable cost in quality. This is a
recall/diversity decision, not a correctness decision. The threshold should be
understood as a dial, not a guarantee.

Deliberately, the threshold was **not** tuned further against the second sample.
Doing so would reproduce exactly the circularity described above.

## 5. Measured accuracy

On the held-out second round, 12 of 15 records above the cutoff were good:

**Precision ≈ 80%, 95% CI [55%, 93%] (n = 15).**

The first round independently gave 8/10 (80%) on a set produced by a different
filter. The agreement is reassuring but the two figures should not be pooled,
since they describe different populations.

Applied to 2,956 exemplars, a 20% defect rate implies roughly **590 defective
records**, and the confidence interval is wide enough that the true figure could
plausibly be anywhere from about 200 to 1,300.

One caveat qualifies that figure. Both labelled groups above the cutoff were
drawn when the cutoff was 0.72. Lowering it to 0.65 admitted a further 173
records whose quality was sampled only by the five rejected records in Group C,
of which 3 of 5 were good. If that thin 60% estimate holds for the newly admitted
band, overall precision of the current set is approximately 79% rather than 80% —
a difference far smaller than the confidence interval, but the newly admitted
records carry weaker evidence than the rest and should not be assumed equivalent.

**The sample size is the binding limitation on everything in this section.**
Twenty labels per round is enough to show the filter is imperfect; it is not
enough to compare two thresholds, and no claim here should be treated as more
precise than it is. Tightening these bounds requires a labelled sample in the low
hundreds.

## 6. The two defect classes

The five defects found in the second round fall into two categories with very
different implications. All examples below are reproduced verbatim.

### Class 1 — Content addition (3 of 5)

Column drift causes the Vietnamese field to carry material with no counterpart in
the English field. The English is correct; the Vietnamese contains it plus
something extra.

**Crutch Walking** — cos 0.770. Correct first sentence, plus an entire extra step 4.

> EN: 1. Reach back for the chair with your other hand.
>
> VI: 1. Dùng tay còn lại với ra ghế ở phía sau. 4. Từ từ ngồi xuống ghế, gập ở hông.

**Kidney Failure** — cos 0.681. "Thận" is correct; "có chức năng:" is appended.

> EN: The kidneys:
>
> VI: Thận có chức năng:

**Exercises to Strengthen Your Shoulder** — cos 0.697. Two extra instruction sentences added.

> EN: Lift your arm out to your side until it is parallel to the floor.
>
> VI: Nâng tay lên ngang sườn cho đến khi song song với sàn. Giữ nguyên rồi hạ từ từ tay xuống. Thư giãn và lặp lại.

This class is structurally invisible to LaBSE. **Cosine similarity measures
absence, never addition**: when the correct translation is present, the score
stays high no matter how much unsourced material rides along with it. The
list-number check catches some instances but not all — in the Crutch Walking
example above, both sides begin with "1.", so the numbers agree and the extra
step 4 passes through undetected.

This class matters more than its frequency suggests. These records model the
behaviour of introducing a sentence that was not in the source, which is the
specific failure a medical translation pipeline exists to prevent. Using them as
few-shot examples would teach the pattern directly.

### Class 2 — Source translation error (2 of 5)

The alignment is correct and the pipeline behaved perfectly. The published PDF
itself is mistranslated.

**Breastfeeding Problems** — cos 0.774. "latching on" is rendered "bám". The
correct clinical Vietnamese is *ngậm bắt vú*.

> EN: If latching on still painful, talk to a lactation specialist.
>
> VI: Nếu vú vẫn đau khi bám, hãy cho chuyên gia tư vấn về sữ̃a mẹ biết.

**Appendectomy** — cos 0.772. "talk to you about your surgery" becomes "kết quả
phẫu thuật" — surgical *results*. A meaning shift introduced by the human
translator.

> EN: Your doctor will talk to you about your surgery and when you can expect to go home.
>
> VI: Bác sĩ sẽ cho quý vị biết kết quả phẫu thuật và thời điểm quý vị có thể được về nhà.

## 7. The ceiling is source quality, not alignment

Class 2 is the important finding in this note. These records are not alignment
failures — the pipeline paired exactly the right blocks. The defect is in the
published source document, and **no filter operating on this corpus can detect
it**, because detecting it requires knowing the correct translation, which is the
very thing the corpus is supposed to supply.

Two of five defects, or roughly 10% of all records, are correctly aligned but
badly translated. That sets a hard ceiling:

- Observed precision: **~80%**
- Achievable maximum through better alignment: **~90%**

The remaining 10-point gap is a property of the source material. Further
engineering effort on the aligner is not warranted; the sensible target for any
future filtering work is Class 1 (content addition) only.

The practical consequence is that this corpus is **evidence, not authority**. It
is a reasonable source of candidate terms and translation exemplars, and it is
not a validated reference. Every glossary term drawn from it needs human
verification by a Vietnamese-reading clinician or translator before use, and
where the evidence for a term is thin or the corpus disagrees with itself, the
term should be flagged rather than resolved from this data alone.

## 8. Known limitations

- **Sample size.** All accuracy figures rest on 20 labels per round. The
  confidence intervals are wide and are reported alongside every estimate.
- **Directive language is nearly absent.** This is patient-education prose, not
  medication instruction. Counts in the 2,956-record exemplar set:

  | Pattern | Records |
  |---|---|
  | "do not" / "don't" | 208 |
  | "every N hours" | 15 |
  | dosage (`mg`/`ml`/`mcg`/`units`) | 9 |
  | "stop taking" / "keep taking" | 3 |
  | "twice a day" / "once a day" | **0** |

  Prohibitions are well covered; dosing frequency is entirely absent. **A
  separate corpus is required for medication instruction language**, and the
  glossary should not claim coverage of dosing terminology on this evidence.
- **Document-level records are excluded.** 162 `kind="document"` records are
  whole-document EN/VI pairs with no internal alignment. They are retained in
  `pairs_dedup.jsonl` but are not exemplars and would need sentence alignment
  first.
- **Trace contamination.** About 1% of deduplicated records carry Spanish text
  from multilingual source PDFs. None survive into the current exemplar set, but
  the check should be repeated if the threshold changes.
- **Incomplete documents.** 22 downloaded documents produced no pairs at all: 18
  cancer.org documents whose English side downloaded but whose Vietnamese URL
  returned 404, 2 posters with too little text to meet the minimum, and 2 pages
  that MedlinePlus links as HTML rather than PDF (these were recovered once the
  reader was changed to detect format from file contents rather than extension).

## 9. Reproducing

```
python scrape_medlineplus.py --index        # -> manifest.jsonl
python scrape_medlineplus.py --download     # ~15 min, 1 req/sec, resumable
python extract_pairs.py                     # -> pairs.jsonl
python verify_alignment.py --rescore        # -> pairs_scored.jsonl, pairs_exemplars.jsonl
python verify_alignment.py --threshold 0.7  # re-threshold without re-running LaBSE
```

Artifacts, in dependency order:

| File | Contents |
|---|---|
| `manifest.jsonl` | One record per indexed document |
| `pairs.jsonl` | Raw extracted pairs, 5,903 |
| `pairs_dedup.jsonl` | Duplicate text removed, 3,740 |
| `pairs_scored.jsonl` | Bilingual records with LaBSE `cos`, 3,578 |
| `pairs_exemplars.jsonl` | Filtered exemplar set, 2,956 |
| `spot_check.md`, `spot_check_v2.md` | The two hand-labelled evaluation samples |

Downloaded PDFs are excluded from version control. They are US federal and
nonprofit patient-education materials; using them as research inputs is normal,
redistributing them is not.
