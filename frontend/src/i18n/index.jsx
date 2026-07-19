import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { LANGUAGES, MESSAGES, DEFAULT_LANG } from './translations.js';

/**
 * i18n runtime. Wrap the app in <LanguageProvider> and call useI18n() anywhere to
 * get { t, lang, setLang, dir, languages }. The chosen language persists in
 * localStorage and drives the <html> lang/dir attributes (so RTL languages lay
 * out right-to-left automatically).
 */

const STORAGE_KEY = 'autosage_lang';
const I18nContext = createContext(null);

function readInitialLang() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && LANGUAGES[saved]) return saved;
  } catch {
    /* localStorage unavailable — fall through to default */
  }
  return DEFAULT_LANG;
}

// Replace {name} placeholders with values from `vars`.
function interpolate(str, vars) {
  if (!vars) return str;
  return str.replace(/\{(\w+)\}/g, (_, k) => (k in vars ? String(vars[k]) : `{${k}}`));
}

export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState(readInitialLang);
  const dir = LANGUAGES[lang]?.dir || 'ltr';

  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = dir;
  }, [lang, dir]);

  const setLang = useCallback((code) => {
    if (!LANGUAGES[code]) return;
    try {
      localStorage.setItem(STORAGE_KEY, code);
    } catch {
      /* ignore persistence failure */
    }
    setLangState(code);
  }, []);

  // Look up a key for the current language, falling back to English, then to the
  // raw key — so a missing translation degrades gracefully, never to a blank.
  const t = useCallback(
    (key, vars) => {
      const table = MESSAGES[lang] || {};
      const val = key in table ? table[key] : MESSAGES[DEFAULT_LANG][key];
      return interpolate(val ?? key, vars);
    },
    [lang],
  );

  const value = { lang, setLang, t, dir, languages: LANGUAGES };
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error('useI18n must be used within <LanguageProvider>');
  return ctx;
}
