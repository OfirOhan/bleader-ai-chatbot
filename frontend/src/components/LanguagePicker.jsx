import { useI18n } from '../i18n/index.jsx';

/**
 * The Language panel (opened from the user menu). Lists every language in the
 * LANGUAGES registry by its native name; clicking one switches the whole UI
 * instantly. Adding a language to translations.js makes it appear here — no
 * change needed in this file.
 */
export default function LanguagePicker({ onClose }) {
  const { t, lang, setLang, languages } = useI18n();

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="info-modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} title={t('common.dismiss')}>✕</button>
        <h2>{t('lang.title')}</h2>
        <div className="info-modal-body">
          <p className="info-modal-note">{t('lang.subtitle')}</p>
          <div className="lang-list">
            {Object.entries(languages).map(([code, meta]) => (
              <button
                key={code}
                className={`lang-option ${code === lang ? 'active' : ''}`}
                onClick={() => setLang(code)}
                dir={meta.dir}
              >
                <span className="lang-option-name">{meta.label}</span>
                {code === lang && <span className="lang-option-check">✓</span>}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
