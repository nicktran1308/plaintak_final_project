import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api.js'
import { useStrings } from './i18n.js'
import Chat from './components/Chat.jsx'
import HandoffSheet from './components/HandoffSheet.jsx'
import LanguagePick from './components/LanguagePick.jsx'
import Paragraph from './components/Paragraph.jsx'
import Upload from './components/Upload.jsx'

/**
 * PlainTalk.
 *
 * Four screens: pick a language, add a document, read it, print the handoff.
 * All state is held here and lost on refresh, matching the backend, which
 * keeps sessions in memory and has no database by design.
 *
 * No timeouts anywhere. An older reader may leave a page open for an hour.
 */
export default function App() {
  const [session, setSession] = useState(null)
  const [lang, setLang] = useState('vi')
  const [doc, setDoc] = useState(null)
  const [screen, setScreen] = useState('language')  // language | upload | read | handoff
  const [handoff, setHandoff] = useState([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [progress, setProgress] = useState(null)
  const [translatingAll, setTranslatingAll] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const keepGoingRef = useRef(null)
  const cancelRef = useRef(false)

  const t = useStrings(lang)

  async function pickLanguage(code) {
    setBusy(true); setError(null)
    try {
      const s = await api.newSession(code)
      setSession(s.session_id)
      setLang(code)
      document.documentElement.lang = code
      setScreen('upload')
    } catch (e) {
      console.error('newSession failed:', e)
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  /**
   * Translate the whole document on request.
   *
   * Deliberately NOT automatic at intake. Auto-translation meant roughly forty
   * model calls and a minute of waiting before the patient saw anything, with
   * no way to skip parts they did not care about. Per-paragraph translation
   * stays the default and this is offered as one press for the patient who
   * wants everything.
   *
   * Cancellable, and failures are swallowed per paragraph: one paragraph that
   * will not translate stays in English rather than stopping the run.
   */
  async function translateAll() {
    if (!doc || lang === 'en' || translatingAll) return
    setTranslatingAll(true)
    cancelRef.current = false
    const paras = doc.paragraphs
    for (let i = 0; i < paras.length; i++) {
      if (cancelRef.current) break
      const p = paras[i]
      setProgress(`${t.translatingDoc} ${i + 1}/${paras.length}`)
      if (!p.text || p.text.length < 3 || p.vi) continue
      try {
        const r = await api.translate(session, p.text)
        if (r.passed) {
          setDoc((d) => ({
            ...d,
            paragraphs: d.paragraphs.map((x) =>
              x.para_id === p.para_id ? { ...x, vi: r.translation } : x),
          }))
        }
      } catch { /* leave this paragraph in English and continue */ }
    }
    setProgress(null)
    setTranslatingAll(false)
  }

  async function handleFile(file) {
    setBusy(true); setError(null)
    try {
      setDoc(await api.upload(session, file))
      setScreen('read')
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleText(text) {
    setBusy(true); setError(null)
    try {
      setDoc(await api.uploadText(session, 'pasted', text))
      setScreen('read')
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const refreshHandoff = useCallback(async () => {
    if (!session) return
    try {
      const r = await api.handoff(session)
      setHandoff(r.questions || [])
    } catch { /* the list is a convenience; a failure here must not block the UI */ }
  }, [session])

  useEffect(() => { refreshHandoff() }, [refreshHandoff, screen])

  async function ask(question) {
    const r = await api.ask(session, question)
    if (r.added_to_handoff) refreshHandoff()
    return r
  }

  const simplify = (paraId) => api.simplify(session, doc.doc_id, paraId)
  const translate = (text) => api.translate(session, text)

  function startOver() {
    if (session) api.endSession(session).catch(() => {})
    setConfirming(false)
    setSession(null); setDoc(null); setHandoff([]); setScreen('language')
  }

  useEffect(() => {
    if (!confirming) return
    keepGoingRef.current?.focus()
    function onKey(e) {
      if (e.key === 'Escape') setConfirming(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [confirming])

  if (screen === 'language') {
    return (
      <div className="shell">
        <LanguagePick onPick={pickLanguage} busy={busy} error={error} />
      </div>
    )
  }

  return (
    <div className="shell">
      <header className="topbar no-print">
        <div className="brand">
          <span className="brand-name">{t.appName}</span>
          <span className="brand-tag">{t.tagline}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span className="lang-badge">{lang === 'vi' ? 'Tiếng Việt' : 'English'}</span>
          <button className="btn-ghost" onClick={() => setConfirming(true)}>{t.startOver}</button>
        </div>
      </header>

      {screen === 'upload' && (
        <Upload t={t} onFile={handleFile} onText={handleText}
                busy={busy} error={error} />
      )}

      {screen === 'handoff' && (
        <HandoffSheet t={t} questions={handoff} onBack={() => setScreen('read')} />
      )}

      {screen === 'read' && doc && (
        <div className="columns">
          <main>
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              gap: 14, flexWrap: 'wrap', marginBottom: 10,
            }}>
              <span className="section-label" style={{ margin: 0 }}>{t.document}</span>
              {lang !== 'en' && (
                <div style={{ textAlign: 'right' }}>
                  <button onClick={translatingAll
                            ? () => { cancelRef.current = true }
                            : translateAll}>
                    {translatingAll
                      ? <><span className="spin" />{progress} · {t.stopTranslating}</>
                      : t.translateAll}
                  </button>
                  {!translatingAll && (
                    <p className="muted" style={{ fontSize: 14, margin: '6px 0 0' }}>
                      {t.translateAllHelp}
                    </p>
                  )}
                </div>
              )}
            </div>
            {doc.paragraphs.map((p) => (
              <Paragraph
                key={p.para_id}
                para={p}
                t={t}
                lang={lang}
                onSimplify={simplify}
                onTranslate={translate}
              />
            ))}
          </main>

          <aside style={{ position: 'sticky', top: 24 }}>
            <Chat
              t={t}
              lang={lang}
              onAsk={ask}
              handoffCount={handoff.length}
              onOpenHandoff={() => setScreen('handoff')}
            />
          </aside>
        </div>
      )}

      {confirming && (
        <div className="confirm-backdrop" onClick={() => setConfirming(false)}>
          <div
            className="card confirm"
            role="dialog"
            aria-modal="true"
            aria-labelledby="confirm-title"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="confirm-title">{t.startOverAsk}</h2>
            <p className="muted">{t.startOverHelp}</p>
            <div className="confirm-actions">
              <button ref={keepGoingRef} className="btn-primary" onClick={() => setConfirming(false)}>
                {t.startOverNo}
              </button>
              <button onClick={startOver}>{t.startOverYes}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
