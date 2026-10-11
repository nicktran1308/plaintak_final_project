/**
 * The printable clinician handoff.
 *
 * Every question the system declined lands here, so its limits terminate in a
 * physical artifact the patient carries to their appointment rather than in a
 * dead end. Print styles strip the interface and leave the list.
 */
export default function HandoffSheet({ t, questions, onBack }) {
  return (
    <div className="sheet">
      <div className="no-print" style={{ marginBottom: 20 }}>
        <button className="btn-ghost" onClick={onBack}>← {t.back}</button>
      </div>

      <div className="card">
        <h2>{t.handoffTitle}</h2>
        <p className="muted no-print" style={{ marginTop: 6 }}>{t.handoffHelp}</p>

        {questions.length === 0
          ? <div className="empty">{t.handoffEmpty}</div>
          : <div style={{ marginTop: 18 }}>
              {questions.map((q, i) => (
                <div className="sheet-q" key={i}>
                  <div className="sheet-num">{i + 1}</div>
                  <p className="sheet-text">{q}</p>
                </div>
              ))}
            </div>}

        <div className="no-print" style={{ marginTop: 26 }}>
          <button className="btn-primary" onClick={() => window.print()}
                  disabled={questions.length === 0}>
            {t.print}
          </button>
        </div>
      </div>
    </div>
  )
}
