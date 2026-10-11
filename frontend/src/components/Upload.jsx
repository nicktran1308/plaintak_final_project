import { useRef, useState } from 'react'

/**
 * Document intake.
 *
 * THE PASTE PATH IS PRIMARY. This inverts the original layout, in response to
 * findings 1 through 4 of the cognitive walkthrough.
 *
 * The reasoning: a patient holding a paper discharge sheet cannot complete a
 * file upload at all, while they can complete the paste path with help from a
 * family member. Making the file picker the prominent button put the unusable
 * option first. The picker is also an operating-system dialog rendered in
 * English and outside this application's control, so any path reaching it
 * leaves the accessible interface entirely.
 *
 * "Chọn tập tin" was replaced for the same reason: "tập tin" presumes a mental
 * model of computer storage that the target reader may not have.
 */
export default function Upload({ t, onFile, onText, busy, error, progress }) {
  const fileRef = useRef(null)
  const [pasted, setPasted] = useState('')
  const enough = pasted.trim().length >= 20

  return (
    <div className="center">
      <div className="card">
        <h2 style={{ marginBottom: 6 }}>{t.uploadTitle}</h2>
        <p className="muted" style={{ marginBottom: 22 }}>{t.uploadHelp}</p>

        {error && <div className="error" style={{ marginBottom: 18 }}>{error}</div>}

        {/* Primary path: type or paste. Works from paper. */}
        <label htmlFor="paste" className="section-label" style={{ display: 'block' }}>
          {t.pasteLabel}
        </label>
        <textarea
          id="paste"
          value={pasted}
          onChange={(e) => setPasted(e.target.value)}
          placeholder={t.pastePlaceholder}
          disabled={busy}
          style={{ minHeight: 220, fontSize: 19 }}
        />
        <button
          className="btn-primary"
          style={{ marginTop: 14, width: '100%', minHeight: 64, fontSize: 21 }}
          onClick={() => onText(pasted)}
          disabled={busy || !enough}
        >
          {busy ? <><span className="spin" />{progress || t.uploading}</> : t.usePasted}
        </button>

        {/* Secondary path, for a patient who does have a digital file. */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 14,
          margin: '26px 0 18px', color: 'var(--ink-faint)', fontSize: 16,
        }}>
          <span style={{ flex: 1, height: 1, background: 'var(--line)' }} />
          {t.orFile}
          <span style={{ flex: 1, height: 1, background: 'var(--line)' }} />
        </div>

        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.txt,.md"
          className="sr-only"
          onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
        />
        <button style={{ width: '100%' }} onClick={() => fileRef.current?.click()} disabled={busy}>
          {t.chooseFile}
        </button>
        <p className="muted" style={{ fontSize: 15, marginTop: 10, marginBottom: 0 }}>
          {t.chooseFileHelp}
        </p>
      </div>
    </div>
  )
}
