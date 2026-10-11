import { useEffect, useRef, useState } from 'react'
import Answer from './Answer.jsx'
import Deferred from './Deferred.jsx'

/**
 * The question panel.
 *
 * One response shape from /api/ask drives four render branches. The frontend
 * never decides whether an answer was safe to give: scope.py and the retrieval
 * threshold already decided, and this only displays the result.
 */
export default function Chat({ t, lang, onAsk, onOpenHandoff, handoffCount }) {
  const [msgs, setMsgs] = useState([])
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState(false)
  const endRef = useRef(null)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs, busy])

  async function send() {
    const text = q.trim()
    if (!text || busy) return
    setQ('')
    setMsgs((m) => [...m, { role: 'q', text }])
    setBusy(true)
    try {
      const r = await onAsk(text)
      setMsgs((m) => [...m, { role: 'a', ...r }])
    } catch (e) {
      setMsgs((m) => [...m, { role: 'a', type: 'error', text: e.message }])
    } finally {
      setBusy(false)
    }
  }

  const TITLES = {
    refusal: t.refusalTitle,
    abstain: t.abstainTitle,
    emergency: t.emergencyTitle,
  }

  // The backend sets added_to_handoff. This only displays it.
  // Emergency stays on calling for help, so that card does not mention the list.
  function savedNote(message) {
    if (!message.added_to_handoff || message.type === 'emergency') return null
    return t.savedForDoctor
  }

  return (
    <div className="card">
      <div className="section-label">{t.questions}</div>

      <div className="chat chat-scroll">
        {msgs.length === 0 && <div className="empty">{t.askPlaceholder}</div>}

        {msgs.map((m, i) => {
          if (m.role === 'q') return <div className="bubble-q" key={i}>{m.text}</div>
          if (m.type === 'answer')
            return (
              <Answer
                key={i}
                text={m.text}
                source={m.source}
                sourceLabel={t.source}
                passageLang={lang === 'en' ? undefined : 'en'}
              />
            )
          if (m.type === 'error')
            return <div className="error" key={i}>{t.errorTitle}: {m.text}</div>
          return (
            <Deferred
              key={i}
              kind={m.type}
              text={m.text}
              title={TITLES[m.type]}
              savedNote={savedNote(m)}
            />
          )
        })}

        {busy && <p className="muted"><span className="spin" />{t.thinking}</p>}
        <div ref={endRef} />
      </div>

      <div className="composer">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder={t.askPlaceholder}
          aria-label={t.askPlaceholder}
          disabled={busy}
        />
        <button className="btn-primary" onClick={send} disabled={busy || !q.trim()}>
          {t.send}
        </button>
      </div>

      <div className="handoff-bar">
        <span className="handoff-count">
          <span className="count-pill">{handoffCount}</span>
          {t.forDoctor}
        </span>
        <button onClick={onOpenHandoff} disabled={handoffCount === 0}>{t.print}</button>
      </div>
    </div>
  )
}
