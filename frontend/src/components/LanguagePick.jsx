import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { STRINGS } from '../i18n.js'

/**
 * First screen. Shown in both languages at once, because a patient who cannot
 * read English must still be able to find the Vietnamese option, and a
 * caregiver helping them must be able to find the English one.
 */
const OPTIONS = [
  { code: 'vi', native: 'Tiếng Việt', english: 'Vietnamese' },
  { code: 'en', native: 'English', english: 'English' },
]

export default function LanguagePick({ onPick, busy, error }) {
  // Probe the backend on mount. If it is unreachable the user finds out here,
  // rather than after tapping a language and watching a spinner forever.
  const [health, setHealth] = useState('checking')
  const [detail, setDetail] = useState('')

  useEffect(() => {
    api.health()
      .then((h) => {
        setHealth('ok')
        setDetail(`${h.glossary_terms} terms · threshold ${h.threshold}` +
          (h.api_key_present ? '' : ' · NO ANTHROPIC KEY') +
          (h.voyage_key_present ? '' : ' · NO VOYAGE KEY'))
      })
      .catch((e) => { setHealth('down'); setDetail(e.message) })
  }, [])

  return (
    <div className="center">
      <div style={{ marginBottom: 32 }}>
        <div className="brand-name" style={{ fontSize: 40 }}>PlainTalk</div>
        <p className="muted" style={{ margin: '6px 0 0' }}>
          {STRINGS.vi.tagline} · {STRINGS.en.tagline}
        </p>
      </div>

      <div className="card">
        <h2 style={{ marginBottom: 6 }}>{STRINGS.vi.pickLanguage}</h2>
        <p className="muted" style={{ marginBottom: 22 }}>{STRINGS.en.pickLanguage}</p>

        <div style={{ display: 'grid', gap: 14 }}>
          {OPTIONS.map((o) => (
            <button
              key={o.code}
              onClick={() => onPick(o.code)}
              disabled={busy}
              style={{
                minHeight: 76, textAlign: 'left', fontSize: 24,
                display: 'flex', flexDirection: 'column', alignItems: 'flex-start',
                justifyContent: 'center', gap: 2, padding: '14px 22px',
              }}
            >
              <span style={{ fontWeight: 600 }}>{o.native}</span>
              {o.native !== o.english && (
                <span style={{ fontSize: 16, color: 'var(--ink-faint)' }}>{o.english}</span>
              )}
            </button>
          ))}
        </div>
        {busy && <p className="muted" style={{ marginTop: 18 }}><span className="spin" />…</p>}
        {error && <div className="error" style={{ marginTop: 18 }}>{error}</div>}
      </div>

      <div style={{ marginTop: 18, fontSize: 15, color: 'var(--ink-faint)' }}>
        {health === 'checking' && <><span className="spin" />Checking backend…</>}
        {health === 'ok' && <>Backend connected · {detail}</>}
        {health === 'down' && (
          <div className="error">
            <strong>Backend not reachable.</strong>
            <div style={{ marginTop: 6, fontSize: 15 }}>{detail}</div>
            <div style={{ marginTop: 10, fontSize: 15 }}>
              Start it with:<br />
              <code>uvicorn backend.main:app --reload --port 8000</code>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
