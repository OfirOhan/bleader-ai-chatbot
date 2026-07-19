import { useState } from 'react';
import * as api from '../api.js';
import Logo from './Logo.jsx';
import { useI18n } from '../i18n/index.jsx';

/**
 * Sign in / sign up with just an email — entering one logs you straight in,
 * creating the account on first use (email is the credential; fine for a POC).
 */
export default function AuthPage({ onAuthSuccess }) {
  const { t } = useI18n();
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await api.emailAuth(email.trim().toLowerCase());
      onAuthSuccess(data.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <span className="auth-logo"><Logo size={40} /></span>
          <h1>AutoSage</h1>
          <p className="auth-subtitle">{t('auth.subtitle')}</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="auth-field">
            <label htmlFor="email">{t('auth.email')}</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
              autoFocus
              required
            />
            <span className="auth-hint">{t('auth.emailHint')}</span>
          </div>

          {error && <div className="auth-error">{error}</div>}

          <button type="submit" className="auth-submit" disabled={loading || !email.trim()}>
            {loading ? t('auth.pleaseWait') : t('auth.continueEmail')}
          </button>
        </form>
      </div>
    </div>
  );
}
