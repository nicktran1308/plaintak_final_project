# PlainTalk: features and languages for a company

Nick Tran · 2026-09-29

## 1. Positioning

Do not sell PlainTalk as an AI translator. Translation is already offered by vendors such as Jaide Health and Opalite Health, and by the EHR vendors.

Sell it as **the fidelity and review layer for translated discharge instructions**: it proves a dose, date or "do not take" survived translation, and it shows a human reviewer exactly which sentences need attention.

Why this holds up:
- Federal guidance (HHS, December 2024) says machine-translated critical documents must be reviewed by a qualified human translator. Your gate makes that review fast.
- Your own ablation shows the pitch in one line: a naive model translation failed half the paragraphs (50%), and placeholder protection passed all of them (100%).
- The gate works on any translator's output, so it can be sold on its own.

Caveat: the 50% vs 100% result is n=10 on one synthetic document. It is a strong lead, not a claim a hospital will accept yet (see section 3, features E1 to E3).

## 2. Feature list

Priority: **P0** do before any pilot, **P1** needed to sell, **P2** grows the business, **P3** later.
Effort: **S** days, **M** weeks, **L** months.

### A. Reviewer workspace (the thing a hospital pays for)

| # | Feature | Why it matters | Pri | Effort |
|---|---|---|---|---|
| A1 | Side-by-side view: original, simplified, translation, back-translation | Reviewer sees everything in one place | P0 | M |
| A2 | Gate flags highlighted inline (missing dose, date, drug, negation) with the reason | Reviewer checks flagged sentences first instead of rereading everything | P0 | M |
| A3 | One-click approve, edit, or reject per flag, then sign-off | Creates the human review the rules require | P0 | M |
| A4 | Audit trail: who reviewed, when, what changed, model and prompt version | Compliance teams ask for this first | P1 | M |
| A5 | Reviewer time tracking (minutes per document) | This is the metric you sell on | P1 | S |
| A6 | Reviewer roles: interpreter, nurse, pharmacist, admin | Real workflows have several people | P2 | M |
| A7 | Reviewer queue with priority (urgent discharges first) | Discharge happens within hours, not days | P2 | M |

### B. Patient delivery

| # | Feature | Why it matters | Pri | Effort |
|---|---|---|---|---|
| B1 | Link or QR code on the printed sheet that opens the translated version | No app install, works on any phone | P1 | S |
| B2 | Large-print and high-contrast versions | Many patients are older adults | P1 | S |
| B3 | Audio read-aloud in the patient's language | Some patients read poorly in any language | P1 | M |
| B4 | Medication schedule extracted as a checklist with reminders ("HOLD metformin until 11/14") | The most useful part of a discharge sheet, and it makes the gate's entities visible | P1 | M |
| B5 | Text-message reminders for follow-up dates and medication restarts | Measurable outcome: fewer missed follow-ups | P2 | M |
| B6 | Caregiver sharing (family member gets the same version) | Family often manages care | P2 | S |
| B7 | Print-ready PDF with both languages side by side | Nurses can hand it over with the English original | P1 | S |

### C. Patient understanding

| # | Feature | Why it matters | Pri | Effort |
|---|---|---|---|---|
| C1 | Q&A that answers only from the patient's own sheet and says "call your care team" otherwise (you already built the abstention) | Patients do have questions at home | P1 | M |
| C2 | Teach-back check: 2 or 3 questions after reading ("When do you restart metformin?") | Hospitals already do teach-back verbally; this records it | P2 | M |
| C3 | Flag when a patient's answers suggest confusion, and notify the care team | Turns understanding into a signal | P3 | M |
| C4 | Visual explanations (pill icons, timeline) | Helps low-literacy patients | P3 | L |

Keep C1 strictly grounded. If it starts giving medical advice, the regulatory picture changes.

### D. Safety and compliance

| # | Feature | Why it matters | Pri | Effort |
|---|---|---|---|---|
| D1 | Fix negation detection (18.2% measured) | This is the harm class Kong et al. documented; a hospital will test it first | P0 | M |
| D2 | Extend placeholder protection to patient identity (name, date of birth, record number) | Almost no identifying data reaches the model; strong security pitch | P0 | M |
| D3 | Business associate agreements with every vendor touching patient data (LLM provider, embeddings provider, hosting) | Required before any real patient data | P0 | S |
| D4 | Data retention controls (delete after N days, per-customer) | Standard procurement question | P1 | M |
| D5 | Role-based access and single sign-on | Hospitals will not use separate passwords | P1 | M |
| D6 | Encryption at rest and in transit, access logging | Baseline for SOC 2 | P1 | M |
| D7 | SOC 2 Type I, then Type II | Larger systems will not sign without it | P2 | L |
| D8 | Keep the product a communication tool: restate what the clinician wrote, never add clinical advice | Stays clear of clinical decision support rules; confirm with a healthcare lawyer | P0 | S |
| D9 | Warning banner on any unreviewed machine translation | HHS guidance expects a warning about potential errors | P1 | S |

### E. Evidence (hospitals buy proof)

| # | Feature | Why it matters | Pri | Effort |
|---|---|---|---|---|
| E1 | Generate 15 to 20 more discharge sheets with varied drugs, doses, dates and negations | Removes the one-document risk in your Week 12 report | P0 | S |
| E2 | Run every arm 3 to 5 times; report means, ranges and confidence intervals | n=10 with nondeterminism is too weak to sell on | P0 | S |
| E3 | Turn every failure found into a permanent regression test | A glossary or prompt change cannot silently break it | P0 | M |
| E4 | Two certified Vietnamese medical interpreters rate outputs blind; publish results | Independent validation beats self-reported numbers | P1 | M |
| E5 | One de-identified pilot on real documents with a partner clinic (quality-improvement project, with approval) | Real documents are the gap synthetic data cannot close | P1 | L |
| E6 | Public accuracy report per language and per document type | Published transparency is a selling point; the CHCF brief recommends accuracy benchmarks broken down by language | P2 | M |
| E7 | Cost and time per document in every report | Buyers compare against $0.10 to $0.30 per word for professional translation | P1 | S |

### F. Product breadth

| # | Feature | Why it matters | Pri | Effort |
|---|---|---|---|---|
| F1 | More document types: medication lists, procedure prep (colonoscopy), after-visit summaries, referral instructions | Same pipeline, more revenue per hospital | P2 | M |
| F2 | Template library per specialty (cardiac, diabetes, surgery, pediatrics, maternity) | Faster onboarding, better glossary coverage | P2 | M |
| F3 | Reading level control (grade 4, 6, 8) with the simplification ladder | You already have this; expose it to the reviewer | P1 | S |
| F4 | Pediatric mode (instructions for parents, plus child-friendly version) | Children's hospitals are early adopters of this category | P3 | M |
| F5 | Do not build: consent forms, end-of-life discussions, behavioral health | Human interpreters are recommended for these; stay out | | |

### G. Integrations

| # | Feature | Why it matters | Pri | Effort |
|---|---|---|---|---|
| G1 | Paste-in or upload web app | Enough for the first pilot | P0 | done |
| G2 | PDF and Word import with layout preserved | Discharge sheets arrive as documents | P1 | M |
| G3 | EHR integration (Epic via SMART on FHIR; Cerner) | Real scale requires living inside the clinician's workflow | P2 | L |
| G4 | Public API and SDK (fidelity check as a service) | Sell the gate to translation vendors and health-tech companies | P2 | M |
| G5 | Fax and secure-email intake | Small clinics still use both | P3 | M |
| G6 | Webhook events (document approved, flag raised) | Lets customers connect their own systems | P3 | S |

### H. Moat (what gets harder to copy over time)

| # | Feature | Why it matters | Pri | Effort |
|---|---|---|---|---|
| H1 | Verified glossary that grows from reviewer corrections, per language | After a year, a reviewed medical term base a general model lacks | P1 | M |
| H2 | Forbidden-rendering list (like `giữ` for "hold") learned from real errors | Encodes harm cases nobody else tracks | P1 | S |
| H3 | Gate scope patterns per language (negation, hold, conditional) | Language-specific and slow to build | P1 | L |
| H4 | Benchmark dataset of real translation errors (de-identified, consented) | Can become an industry reference | P3 | L |
| H5 | Reviewer feedback loop: each correction becomes a test | Quality improves with usage | P1 | M |

### I. Operations and business

| # | Feature | Why it matters | Pri | Effort |
|---|---|---|---|---|
| I1 | Usage dashboard for customers (documents, reviewer minutes, flags caught) | Proves value at renewal | P2 | M |
| I2 | Per-document cost tracking and spend caps | Protects margins | P1 | S |
| I3 | Model fallback and version pinning | A vendor model update must not change behavior silently | P1 | M |
| I4 | Automated evaluation on every change (regression suite gate) | Keeps quality claims true as you ship | P1 | M |
| I5 | Status page and uptime monitoring | Hospitals ask | P2 | S |

## 3. What to build first

**Next 90 days**

1. E1, E2, E3: more documents, repeated runs, regression tests. This makes your numbers defensible.
2. D1: fix negation.
3. D2, D3, D8: identity protection, business associate agreements, scope boundaries.
4. A1 to A3, A5: reviewer workspace with time tracking.
5. E4: independent interpreter rating.
6. E5: one clinic pilot.

**After a clinic uses it on real patients**: B, C, F and G in the order the clinic asks for them. Do not build them before someone asks.

## 4. Languages

### 4.1 What makes a language easy to add

Your architecture has two kinds of components:

- **Language-independent, so free to reuse:** placeholder protection for doses, dates and drug names; the entity gate on the source side; the reviewer workspace; back-translation checking.
- **Language-specific, so the real cost of each new language:**
  - the verified glossary (28 directive terms so far, checked by a second speaker),
  - forbidden renderings (for example `giữ` for "hold"),
  - negation, hold and conditional scope patterns for the gate,
  - a native reviewer to verify all of the above.

The bottleneck is **finding two trustworthy native speakers**, not the model. The proposal's method (glossary written by one person, verified by a second) needs both for every language.

Criteria used below:
- **Model quality:** current models translate high-resource languages better; quality drops for less-resourced languages and complex content, as the CHCF brief states.
- **Demand:** how many patients in California hospitals need it. California's threshold-language lists vary by county and change, so check the current Medi-Cal list for your target county before committing.
- **Script:** Latin script and space-separated words make the gate's matching simpler.
- **Competition:** how many vendors already serve it.
- **Reviewer availability:** how easy it is to find certified medical interpreters.

Ratings are my judgment, not measured. Check each against your own ablation before promising anything.

### 4.2 Tier 1: add first (high demand, strong model support, reviewers available)

| Language | Model quality | Demand (California) | Script and gate notes | Competition |
|---|---|---|---|---|
| **Spanish** | Strongest | Largest by far | Latin script; many glossary sources exist (MedlinePlus, published clinical glossaries); negation patterns are simple (`no`, `no tome`, `evite`) | Highest; every vendor starts here. Your differentiator is the fidelity gate, not coverage |
| **Chinese (Simplified and Traditional; Cantonese and Mandarin speakers)** | Strong for written text | Very high | No spaces between words, so matching is by character; two written standards must be handled separately, and Cantonese speakers usually read Traditional; negation and "hold/stop" have several forms | High, but written medical accuracy is uneven |
| **Korean** | Good to strong | High in Southern California | Hangul; agglutinative, so negation sits in verb endings (`하지 마세요`) and pattern matching is harder than Spanish; honorific level must be fixed by policy | Moderate |
| **Tagalog (Filipino)** | Good, weaker on medical terms | High | Latin script; heavy English and Spanish borrowing in medical speech, which helps and complicates glossary choices | Lower than Spanish, often thin |

Recommended order: **Spanish or Chinese second**, depending on whether you want the biggest market (Spanish) or a market where a Vietnamese-style community pilot generalizes (Chinese). Spanish wins on model quality and demand; Chinese wins on differentiation.

### 4.3 Tier 2: add after a paying customer asks

| Language | Notes |
|---|---|
| **Arabic** | Right-to-left layout in the reviewer UI and PDFs; diacritics and dialect variation; formal written Arabic is the safe standard; digits may appear as Arabic-Indic numerals, which the placeholder step must handle |
| **Russian** | Cyrillic; rich morphology makes glossary matching harder (inflected forms); good model quality |
| **Farsi (Persian)** | Right-to-left; moderate model quality; large Los Angeles population |
| **Armenian (Eastern and Western)** | Distinct script; two written variants; concentrated in Los Angeles County; model quality is weaker than the languages above |
| **Hindi** | Devanagari; good model quality; code-mixing with English medical terms is common |
| **Punjabi** | Gurmukhi script; weaker model quality; significant Central Valley population |
| **Japanese** | High model quality, smaller demand; useful for research and some clinics |

### 4.4 Tier 3: strategic bets (high need, lower model quality, few competitors)

These are where "accuracy drops for less-resourced languages" is most true. That is also where a reviewed glossary and a fidelity gate are most valuable, because generic translation is weakest there. Treat each as a research project with a partner community organization, not a quick add.

| Language | Notes |
|---|---|
| **Khmer** | Large Long Beach population; script has no spaces between words; low-resource; very few competitors |
| **Hmong** | Central Valley communities; oral tradition, and many older patients do not read the written form, so audio matters more than text |
| **Lao** | Similar to Khmer in script and resource level |
| **Burmese** | Growing refugee communities; low-resource |
| **Haitian Creole** | Strong on the East Coast; not a California priority |
| **Somali, Amharic, Tigrinya** | Refugee-resettlement markets; low-resource |
| **Indigenous languages (Mixtec, Zapotec, Mam)** | Many patients speak these; largely unwritten in practice, so **audio and interpreter workflows**, not text translation |

### 4.5 Order of expansion

1. **Vietnamese**: finish and validate (current).
2. **Spanish**: largest market and easiest to build; proves the pipeline is not Vietnamese-specific.
3. **Chinese** (Traditional first if you start with Cantonese-speaking communities, otherwise Simplified): tests the gate on a language without spaces.
4. **Korean or Tagalog**, by which partner clinic you land.
5. **Tier 2 languages** only on customer request.
6. **Tier 3** when you have funding for community partnerships.

### 4.6 Checklist for adding one language

Copy this per language. A language is not "supported" until every item is done.

- [ ] Two native speakers identified: one writes, one verifies (at least one with medical background)
- [ ] Glossary of directive terms (hold, stop, take, avoid, until, only if, call, emergency) written and second-verified
- [ ] Forbidden renderings listed (translations that flip meaning, such as "hold" read as "continue")
- [ ] Negation, hold and conditional scope patterns written for the gate
- [ ] Number, date and unit formats handled (Arabic-Indic digits, era years, date order)
- [ ] Script handling tested (spacing, right-to-left, fonts in PDF export)
- [ ] Ablation run: naive vs protected, at least 3 runs each, on 20 or more documents
- [ ] Blind rating by two certified interpreters
- [ ] Gate fault-injection run on this language (drop a dose, flip a negation) and detection rate recorded per fault type
- [ ] Published accuracy numbers for the language, including negation detection
- [ ] Regression tests added for every error found
- [ ] Audio voice checked by a native speaker (if read-aloud is offered)

## 5. Business path

**Who buys**
- Community health centers and clinics serving one large language group (fastest decisions)
- Children's and safety-net hospitals (early adopters of AI language tools)
- Language-service vendors adding AI, as a partner rather than a competitor: sell them the fidelity check

**How to price**
- Professional document translation costs about $0.10 to $0.30 per word (CHCF brief), so a 600-word discharge sheet costs roughly $60 to $180.
- Start with per-document pricing well below that, including reviewer tooling.
- Move to a per-site subscription once volume is predictable.
- Price the fidelity API per checked document.

**Milestones**
1. Defensible evaluation (section 3, items 1 to 3)
2. First clinic pilot on real documents
3. Two paid pilots with a measured result (reviewer minutes per document, errors caught)
4. Second language live
5. SOC 2 Type I and one EHR integration
6. Third language and first non-clinic customer (vendor partnership)

## 6. Risks

| Risk | Why it matters | Mitigation |
|---|---|---|
| Incumbents add fidelity checking | Jaide, Opalite and EHR vendors have distribution | Move faster on measured safety; sell the gate as a service |
| Regulation shifts | Enforcement priorities can change between administrations; the human-review expectation may soften | Lead with time saved and safety; California requirements (Medi-Cal contracts, threshold languages) are more durable than federal enforcement |
| One model vendor dependency | Behavior changes when the vendor updates a model | Pin versions, keep regression suite, support a second model |
| Evaluation gap | One synthetic document and 18.2% negation detection will not pass hospital review | Section 3, items 1 to 5 |
| Liability | A missed dose error could harm a patient | Human sign-off on every document, warning banners, lawyer review of contracts and terms |
| Reviewer supply | Every language needs certified reviewers | Partner with interpreter services; pay reviewers; keep reviews short through the gate |
| Overreach | Adding advice features moves into regulated territory | Keep C1 grounded; do not add recommendations |

## 7. Verify before relying on this

- California threshold languages for your target county (they vary by county and change over time)
- Current HHS and state guidance on machine translation review (the source used here is dated December 2024)
- Competitor claims (CHLA time savings and Opalite site counts come from a 2026 CHCF brief and press coverage, not from your own testing)
- Legal advice on HIPAA, business associate agreements, and FDA scope, from a healthcare lawyer, before any real patient data

## Sources

- [AI and Language Access in Health Care (California Health Care Foundation, March 2026)](https://www.chcf.org/wp-content/uploads/2026/03/AILanguageAccess.pdf)
- [HHS reaffirms language access requirements under Section 1557 (National Law Review)](https://natlawreview.com/article/hhs-letter-reiterates-expectations-language-accessibility)
- [LA hospital tests Jaide Health AI to translate discharge notes (STAT)](https://www.statnews.com/2024/11/11/childrens-hospital-los-angeles-tests-generative-ai-translate-discharge-notes/)
- [Opalite Health (YC W2026)](https://www.startuphub.ai/ai-news/claudes-corner/2026/claudes-corner-opalite-health-yc-w2026)
- Your own `../reports/week12_simplify_translate.md` (ablation and gate results)
