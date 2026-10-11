/**
 * PlainTalk API client.
 *
 * Mirrors backend/main.py exactly. Note the argument styles differ per route:
 * /api/upload and /api/upload_text take session_id as a QUERY parameter,
 * while /api/ask, /api/simplify and /api/translate take a JSON body.
 */

const BASE = '/api'

/**
 * Every request carries a timeout. A hung fetch would otherwise leave the
 * interface spinning with no way for the user to recover, which for this
 * audience is worse than an error message.
 */
async function req(path, { method = 'GET', body, form, timeout = 90000 } = {}) {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), timeout)
  const opts = { method, signal: ctrl.signal }

  if (form) {
    opts.body = form
  } else if (body) {
    opts.headers = { 'Content-Type': 'application/json' }
    opts.body = JSON.stringify(body)
  }

  let res
  try {
    res = await fetch(BASE + path, opts)
  } catch (e) {
    clearTimeout(timer)
    if (e.name === 'AbortError') {
      throw new Error(`Request timed out after ${timeout / 1000}s: ${path}`)
    }
    throw new Error(
      `Cannot reach the backend at ${BASE}${path}. ` +
      `Is uvicorn running on port 8000?`)
  }
  clearTimeout(timer)

  const text = await res.text()

  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      detail = JSON.parse(text).detail || detail
    } catch { /* body was not JSON */ }
    throw new Error(detail)
  }

  // A dev server that is not proxying /api returns index.html with status 200.
  // Parsing that as JSON fails confusingly, so name the actual problem.
  if (text.trim().startsWith('<')) {
    throw new Error(
      `${path} returned HTML instead of JSON. The Vite proxy is not ` +
      `forwarding /api to port 8000. Run npm run dev from the frontend folder.`)
  }

  try {
    return JSON.parse(text)
  } catch {
    throw new Error(`${path} returned a malformed response: ${text.slice(0, 80)}`)
  }
}

export const api = {
  health: () => req('/health'),

  newSession: (language) =>
    req('/session', { method: 'POST', body: { language } }),

  endSession: (sessionId) =>
    req(`/session?session_id=${encodeURIComponent(sessionId)}`, { method: 'DELETE' }),

  /** session_id is a query parameter; the file goes in a multipart body. */
  upload: (sessionId, file) => {
    const form = new FormData()
    form.append('file', file)
    return req(`/upload?session_id=${encodeURIComponent(sessionId)}`, {
      method: 'POST', form,
    })
  },

  /** All three arguments are query parameters on this route. */
  uploadText: (sessionId, docId, text) =>
    req(
      `/upload_text?session_id=${encodeURIComponent(sessionId)}` +
      `&doc_id=${encodeURIComponent(docId)}&text=${encodeURIComponent(text)}`,
      { method: 'POST' },
    ),

  simplify: (sessionId, docId, paraId) =>
    req('/simplify', {
      method: 'POST',
      body: { session_id: sessionId, doc_id: docId, para_id: paraId },
    }),

  ask: (sessionId, question) =>
    req('/ask', { method: 'POST', body: { session_id: sessionId, question } }),

  translate: (sessionId, text) =>
    req('/translate', { method: 'POST', body: { session_id: sessionId, text } }),

  handoff: (sessionId) =>
    req(`/handoff?session_id=${encodeURIComponent(sessionId)}`),
}
