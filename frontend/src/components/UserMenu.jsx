import { useState, useRef, useEffect } from 'react';
import LanguagePicker from './LanguagePicker.jsx';
import { useI18n } from '../i18n/index.jsx';
import { useTheme } from '../useTheme.js';

/**
 * Account bar at the bottom of the sidebar. Click to open a small popover:
 * theme toggle, language, log out.
 */
export default function UserMenu({ user, onLogout }) {
  const { t } = useI18n();
  const [theme, toggleTheme] = useTheme();
  const [open, setOpen] = useState(false);
  const [langOpen, setLangOpen] = useState(false);
  const rootRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onDocClick = (e) => {
      if (rootRef.current && !rootRef.current.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', onDocClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const name = user.display_name || user.email || 'You';

  return (
    <div className="user-menu" ref={rootRef}>
      {open && (
        <div className="user-menu-popover" role="menu">
          <div className="user-menu-header">{user.email}</div>

          <button className="user-menu-item" onClick={toggleTheme}>
            {theme === 'dark' ? '☀️' : '🌙'}&nbsp;
            {theme === 'dark' ? t('menu.lightMode') : t('menu.darkMode')}
          </button>
          <button className="user-menu-item" onClick={() => { setLangOpen(true); setOpen(false); }}>
            🌐&nbsp; {t('menu.language')}
          </button>

          <div className="user-menu-divider" />

          <button
            className="user-menu-item user-menu-item-danger"
            onClick={() => { setOpen(false); onLogout(); }}
          >
            ⎋&nbsp; {t('menu.logout')}
          </button>
        </div>
      )}

      <button className="user-menu-trigger" onClick={() => setOpen((v) => !v)}>
        <span className="sidebar-user-avatar">{name[0].toUpperCase()}</span>
        <span className="sidebar-user-name">{name}</span>
      </button>

      {langOpen && <LanguagePicker onClose={() => setLangOpen(false)} />}
    </div>
  );
}
