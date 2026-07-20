import { useI18n } from '../i18n/index.jsx';

/**
 * AnswerCard — a grounded assistant reply: the answer text plus the source
 * road-tests it was drawn from, shown as clickable citation chips.
 */
export default function AnswerCard({ message }) {
  const { t } = useI18n();
  const { content, sources = [] } = message;

  // Render the answer as paragraphs (the model returns plain text with blank
  // lines between paragraphs).
  const paragraphs = String(content || '').split(/\n{2,}/).filter(Boolean);

  return (
    <div className="answer-card">
      <div className="answer-content">
        {paragraphs.map((p, i) => (
          // dir="auto" lets each paragraph pick its own base direction from its
          // text, so a Hebrew reply renders RTL (with English car names/numbers
          // ordered correctly) even when the UI chrome is LTR, and vice-versa.
          <p key={i} dir="auto">{p}</p>
        ))}
      </div>

      {sources.length > 0 && (
        <div className="answer-sources">
          <div className="answer-sources-label">{t('answer.sources')}</div>
          <div className="answer-sources-list">
            {sources.map((s, i) => (
              <a
                key={i}
                className="source-chip"
                href={s.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                {s.car}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
