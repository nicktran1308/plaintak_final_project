/**
 * The three ways the system declines to answer.
 *
 * This component is the point of the project, so it is the one that had to be
 * right first. A refusal is the system working correctly, not an error, and it
 * must not read as one to an anxious reader: warm coral, never red, and the
 * question always lands somewhere useful rather than in a dead end.
 *
 * The backend decides which of these applies. This component only renders it.
 * savedNote is the same fact: the backend already stored the question, and
 * this line says so. Emergency does not pass one, so that card stays on
 * calling for help.
 */

const ICONS = {
  refusal: (
    <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="2" strokeLinecap="round" aria-hidden="true">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  ),
  abstain: (
    <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="2" strokeLinecap="round" aria-hidden="true">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6M9 15l6-6M15 15l-6-6" />
    </svg>
  ),
  emergency: (
    <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
      <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <path d="M12 9v4M12 17h.01" />
    </svg>
  ),
}

export default function Deferred({ kind, text, title, savedNote }) {
  return (
    <div className={`deferred ${kind === 'emergency' ? 'emergency' : ''}`} role="status">
      <div className="deferred-head">
        <span style={{ color: '#993C1D', display: 'flex' }}>{ICONS[kind] || ICONS.abstain}</span>
        <span className="deferred-title">{title}</span>
      </div>
      <p className="deferred-body">{text}</p>
      {savedNote ? <p className="deferred-saved">{savedNote}</p> : null}
    </div>
  )
}
