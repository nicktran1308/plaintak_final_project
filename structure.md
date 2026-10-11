plaintalk/

│

├── backend/

│ ├── [main.py](http://main.py) # FastAPI routes only, no logic

│ ├── [config.py](http://config.py) # thresholds, model names, keys from env

│ ├── requirements.txt

│ │

│ ├── pipeline/

│ │ ├── **init**.py

│ │ ├── [gate.py](http://gate.py) ✅ DONE — entity check + verdict

│ │ ├── [intake.py](http://intake.py) # PDF → paragraphs, stable IDs

│ │ ├── [simplify.py](http://simplify.py) # paragraph + level → simpler, gated

│ │ ├── [retrieve.py](http://retrieve.py) # chunk, embed, search, threshold

│ │ ├── [scope.py](http://scope.py) # is this advice-seeking?

│ │ ├── [chat.py](http://chat.py) # scope → retrieve → answer or abstain

│ │ └── [translate.py](http://translate.py) # glossary sub → translate → verify

│ │

│ ├── data/ # small files the APP loads at runtime

│ │ ├── glossary.json # merged mined + directive tiers

│ │ └── exemplars.jsonl # filtered subset for few-shot

│ │

│ └── tests/

│ ├── test\_[gate.py](http://gate.py) ✅ DONE — 20/20

│ ├── test\_[scope.py](http://scope.py)

│ └── test\_[retrieve.py](http://retrieve.py)

│

├── eval/

│ ├── adversarial_set.json # ~150 questions, 4 categories

│ ├── synthetic_docs/ # your fake discharge sheets, labs

│ ├── error_annotations.jsonl # hand-labeled, for gate precision/recall

│ ├── run*qa*[eval.py](http://eval.py) # → false-answer rate (headline metric)

│ ├── run*simplify*[eval.py](http://eval.py) # → SARI, BERTScore, readability

│ ├── run*gate*[eval.py](http://eval.py) # → catch rate, false positives, misses

│ ├── run*translate*[eval.py](http://eval.py) # → entity preservation, ablation

│ └── results/ # generated tables for your report

│

├── frontend/

│ ├── package.json

│ ├── vite.config.js

│ └── src/

│ ├── App.jsx

│ ├── pages/

│ │ ├── LanguagePick.jsx

│ │ ├── DocumentView.jsx

│ │ ├── Chat.jsx

│ │ └── Handoff.jsx

│ └── components/

│ ├── Paragraph.jsx

│ ├── LadderControls.jsx

│ ├── OriginalPanel.jsx

│ ├── GateBadge.jsx

│ ├── Answer.jsx

│ └── Deferred.jsx # refusal + abstention states

│

├── docs/

│ ├── ALIGNMENT\_[NOTES.md](http://NOTES.md) ✅ written by Cursor

│ ├── [architecture.md](http://architecture.md)

│ └── [deployment.md](http://deployment.md)

│

├── .env # ANTHROPIC_API_KEY — gitignored

├── .env.example # committed, no real key

├── .gitignore

└── [README.md](http://README.md)
