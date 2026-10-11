/**
 * A grounded answer with its citation.
 *
 * The source passage is shown, not linked to, because a patient should be able
 * to check the answer against their own paper without navigating away.
 */
export default function Answer({ text, source, sourceLabel, passageLang }) {
  return (
    <div className="answer">
      <p className="answer-text">{text}</p>
      {source && (
        <div className="cite">
          <div className="cite-label">{sourceLabel}</div>
          <p className="cite-body" lang={passageLang}>{source.text}</p>
        </div>
      )}
    </div>
  )
}
