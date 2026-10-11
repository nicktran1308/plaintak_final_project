import { useState } from 'react'

/**
 * One paragraph of the patient's document.
 *
 * The signature element of the interface: the simplified text and the
 * clinician's original sit on the same card, separated by a rule rather than
 * hidden behind a tab. The whole argument this system makes is that nothing
 * was lost, so the proof stays on screen.
 *
 * The gate verdict arrives from the backend as data. This component renders
 * three states from one response shape and never decides safety itself.
 */

const ENTITY_RE =
  /(\d+(?:[.,]\d+)?\s*(?:mg|mcg|ml|g|l|units?|tablets?|capsules?)\b|\d{1,2}\/\d{1,2}(?:\/\d{2,4})?|\b\d{1,2}:\d{2}\s*(?:am|pm)?\b)/gi

/** Mark doses, dates and times inline, so "checked" is visible rather than claimed. */
function markEntities(text) {
  const parts = text.split(ENTITY_RE)
  return parts.map((p, i) =>
    ENTITY_RE.test(p) && i % 2 === 1
      ? <mark className="entity" key={i}>{p}</mark>
      : <span key={i}>{p}</span>,
  )
}

/**
 * Laboratory result flags. Short, closed-vocabulary and safety-relevant: these
 * are the most consequential words on a lab report and a Vietnamese-only
 * reader would otherwise scan past them (walkthrough finding 6). Substituted
 * directly rather than through the model, since the set is fixed.
 */
const FLAGS = {
  HIGH: 'CAO', LOW: 'THẤP', NORMAL: 'BÌNH THƯỜNG',
  ABNORMAL: 'BẤT THƯỜNG', CRITICAL: 'NGUY HIỂM', POSITIVE: 'DƯƠNG TÍNH',
  NEGATIVE: 'ÂM TÍNH',
}
const RE_FLAG = new RegExp(`\\b(${Object.keys(FLAGS).join('|')})\\b`, 'g')

function markFlags(text, lang) {
  if (lang === 'en') return text
  return text.replace(RE_FLAG, (m) => `${FLAGS[m]} (${m})`)
}

export default function Paragraph({ para, t, lang, onSimplify, onTranslate }) {
  const [state, setState] = useState(null)   // simplify response
  // A translation supplied at intake, if the document was translated on load.
  const [vi, setVi] = useState(para.vi ? { translation: para.vi, passed: true } : null)
  const [busy, setBusy] = useState(null)     // 'simplify' | 'translate'
  const [err, setErr] = useState(null)

  const isHeader = para.kind === 'header'
  const shown = state?.text ?? para.text
  const blocked = state?.gate === 'blocked'

  async function simplify() {
    setBusy('simplify'); setErr(null)
    try { setState(await onSimplify(para.para_id)) }
    catch (e) { setErr(e.message) }
    finally { setBusy(null) }
  }

  async function translate() {
    setBusy('translate'); setErr(null)
    try { setVi(await onTranslate(shown)) }
    catch (e) { setErr(e.message) }
    finally { setBusy(null) }
  }

  if (isHeader) {
    return (
      <div className="card para header-para">
        <p className="para-text header-text">{para.text}</p>
        {vi?.translation && (
          <p className="vi-text header-text">{markFlags(vi.translation, lang)}</p>
        )}
        {lang !== 'en' && !vi && (
          <button className="btn-ghost" style={{ marginTop: 8, minHeight: 40, padding: '6px 0' }}
                  onClick={translate} disabled={busy}>
            {busy === 'translate' ? <><span className="spin" />{t.translating}</> : t.showVietnamese}
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="card para">
      <div className="para-head">
        {state && state.level > 0
          ? <>
              <span className="level-chip">{t.level} {state.level}</span>
              {state.readability != null && (
                <span className="grade-chip">{t.reading} {state.readability}</span>
              )}
            </>
          : <span className="level-chip plain">{t.original}</span>}
      </div>

      <p className="para-text">{markEntities(shown)}</p>

      {vi?.translation && (
        <p className="vi-text">{markEntities(markFlags(vi.translation, lang))}</p>
      )}

      {err && <div className="error" style={{ marginTop: 14 }}>{err}</div>}

      <div className="para-actions">
        <button onClick={simplify} disabled={!!busy || state?.can_simplify === false}>
          {busy === 'simplify'
            ? <><span className="spin" />{t.simplifying}</>
            : state?.can_simplify === false ? t.ladderDone : t.simplify}
        </button>
        {lang !== 'en' && (
          <button onClick={translate} disabled={!!busy}>
            {busy === 'translate' ? <><span className="spin" />{t.translating}</> : t.showVietnamese}
          </button>
        )}
      </div>

      {/* The clinician's original is always available, never behind a toggle. */}
      {state && state.level > 0 && (
        <div className="original-panel">
          <div className="original-label">{t.original}</div>
          <p className="original-body">{state.original}</p>
        </div>
      )}

      {(state || vi) && (
        <div className={`gate-badge ${blocked || vi?.passed === false ? 'blocked' : ''}`}>
          <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            {!(blocked || vi?.passed === false) && <path d="m9 12 2 2 4-4" />}
          </svg>
          <span>{blocked || vi?.passed === false ? t.gateBlocked : t.checked}</span>
        </div>
      )}
    </div>
  )
}
