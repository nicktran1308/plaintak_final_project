# PlainTalk frontend

React + Vite. Talks to the FastAPI backend on port 8000.

## Run

Terminal 1 — backend:

    source .venv/bin/activate
    uvicorn backend.main:app --reload --port 8000

Terminal 2 — frontend:

    cd frontend
    npm install
    npm run dev

Open http://localhost:5173

Vite proxies /api to localhost:8000, so no CORS configuration is needed
beyond what main.py already allows.

## Screens

    language -> upload -> read -> handoff

## Structure

    src/api.js            one function per backend route
    src/i18n.js           every label in English and Vietnamese
    src/styles.css        design tokens and senior-friendly base rules
    src/App.jsx           screen state and session handling
    src/components/
      LanguagePick.jsx    shown in both languages at once
      Upload.jsx          PDF or pasted text
      Paragraph.jsx       simplification ladder + translation + gate badge
      Chat.jsx            question panel, four render branches
      Answer.jsx          grounded answer with its source passage
      Deferred.jsx        refusal / abstention / emergency
      HandoffSheet.jsx    printable clinician list

## The rule this frontend follows

The frontend never decides whether content is safe to show. The gate returns a
verdict and the scope classifier returns a response type; these components
render what was already decided. Any logic that looks like a safety judgment
belongs in backend/pipeline/, not here.

## Accessibility constraints, as concrete numbers

- 20px body text, 22px document text
- 48px minimum on every tappable target
- no hover-only controls and no session timeouts
- the clinician's original English is always on screen, never behind a toggle
- deferrals are coral, never red: a refusal is the system working
- prefers-reduced-motion respected; focus rings are 3px and always visible

## If the language screen spins forever

The screen now probes the backend on load and shows its status underneath the
language buttons. Read that line first.

    "Backend connected"      the API is reachable; the problem is elsewhere
    "Backend not reachable"  uvicorn is not running, or not on port 8000

Every request also carries a 90 second timeout, so a hung call surfaces as an
error rather than an endless spinner.

Common causes, in the order worth checking:

1. **uvicorn is not running.** Start it from the PROJECT ROOT, not from
   frontend/:

       cd ~/Folders/plaintak_final_project
       source .venv/bin/activate
       uvicorn backend.main:app --reload --port 8000

2. **npm run dev was started from the wrong folder.** The Vite proxy only
   applies when the dev server runs inside frontend/. If /api returns HTML
   instead of JSON, this is the cause, and the error message says so.

3. **A missing API key.** POST /api/session constructs the Voyage and Anthropic
   clients. The status line reports NO ANTHROPIC KEY or NO VOYAGE KEY when
   either is absent from .env.

4. **Check the browser console.** Failures are logged there with the full
   error, and the uvicorn terminal shows whether the request arrived at all.
