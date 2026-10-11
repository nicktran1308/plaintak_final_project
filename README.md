# PlainTalk

PlainTalk helps a Vietnamese-speaking patient read an English clinical document — a discharge sheet, a lab report, or a medication guide — without the system inventing, dropping, or reversing a clinical fact.

The patient can:

- paste the paper, or upload a PDF that is already saved on the device
- step a paragraph down a simplification ladder, with each step checked against the clinician’s original
- translate one paragraph, or the whole document, into Vietnamese
- ask a question and get an answer cited to their own document, a refusal, or an abstention
- print the questions the system would not answer and take that sheet to the clinician

The verified language pair is English to Vietnamese. Refusals and abstentions are branches in code, not instructions inside a prompt. A question that asks for medical advice, or for emergency judgment, never reaches the model. A question the document does not answer is declined. Doses, dates, drug names, and glossary terms are replaced with placeholders before translation, then restored and checked.

This is a course project (CPSC 597). It is a communication aid. It restates what the clinician wrote. It does not give medical advice.

## What you need

- Python 3.12
- Node.js (for the React frontend)
- An [Anthropic API key](https://console.anthropic.com/) for Claude Haiku
- A [Voyage API key](https://www.voyageai.com/) for embeddings (`voyage-3`)

The clinical stack is pinned to NumPy 1.26.4, spaCy 3.7.4, and scispaCy 0.5.4. Do not upgrade those packages in this environment. PyTorch and NumPy 2 cannot sit beside them, which is why embeddings are an API call and BERTScore is not computed.

## Set up

From the project root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

cp .env.example .env
```

Edit `.env` and replace the placeholders:

```bash
ANTHROPIC_API_KEY=sk-ant-...
VOYAGE_API_KEY=pa-...
```

`.env` is gitignored. Do not commit it.

Install the frontend once:

```bash
cd frontend
npm install
```

The first `pip install` downloads the scispaCy models. That step is large and needs a network connection.

## Run

Two terminals, both started so that the paths below match.

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

Open http://localhost:5173. The frontend proxies `/api` to port 8000.

If the language screen never leaves its spinner, read the status line under the buttons. “Backend not reachable” means uvicorn is not running, or it was not started from the project root. “NO ANTHROPIC KEY” or “NO VOYAGE KEY” means `.env` is missing that key.

## Use it

1. Choose **Tiếng Việt** or **English**. Everything after this screen follows that choice. The clinician’s English stays visible either way.
2. Paste the document into the text box and press **Đọc giấy của tôi** / **Read my paper**. The box needs at least 20 characters. File upload is the secondary path, and only for a file already on the device. The operating-system file picker is not translated.
3. On each paragraph, **Giải thích đơn giản hơn** / **Explain more simply** adds one simpler version. **Xem bằng tiếng Việt** / **Show in Vietnamese** translates that paragraph. **Dịch toàn bộ giấy tờ** / **Translate the whole paper** walks every paragraph and can be stopped. A paragraph the safety check rejects stays in English.
4. Ask a question in the side panel. An answer includes the sentence it came from. A refusal or an abstention is a coral card, not an error. Those questions are added to the list for the clinician.
5. Open **In** / **Print** to see that list and print it.

There are no accounts and no database. The session lives in memory and is discarded when the server restarts, or when you press **Bắt đầu lại** / **Start over**.

## Tests

The pipeline tests do not call the APIs. From the project root, with the virtual environment active:

```bash
python backend/tests/test_gate.py
python backend/tests/test_translate.py
python backend/tests/test_chat.py
python backend/tests/test_intake.py
```

## Layout

| Path | What it is |
|---|---|
| `backend/` | FastAPI app and the pipeline: intake, simplification, translation, retrieval, scope, and the entity-check gate |
| `frontend/` | React + Vite patient interface. Details are in [frontend/README.md](frontend/README.md) |
| `eval/` | Question set, evaluation harnesses, and result files |
| `backend/data/glossary_directive_DONE.jsonl` | 28 directive terms used at translation time |
| `docs/reports/` | Weekly reports and the status brief |
| `docs/interface/` | Cognitive walkthrough and accessibility inspection |
| `docs/planning/` | Earlier architecture sketch, and a separate product note that is not a course deliverable |
| `medlineplus_scraper/` | How the English–Vietnamese exemplar corpus was built |
| `plaintalk-data/medlineplus-vi/` | Derived pairs and alignment notes. The source PDFs are not in this repository |

## What is not in this repository

- `.env` and any real API keys
- the Python virtual environment and `node_modules`
- glossary backup files (`*.bak`)
- MedlinePlus source PDFs, and the downloaded Cochrane, Med-EASi, and PLABA corpora
- scispaCy model archives

Those corpora can be fetched again with the notes in [backend/data/DATASETS.md](backend/data/DATASETS.md). The MedlinePlus scraper is documented in [medlineplus_scraper/README.md](medlineplus_scraper/README.md).
