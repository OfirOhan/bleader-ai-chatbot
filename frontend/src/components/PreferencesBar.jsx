import { useI18n } from '../i18n/index.jsx';

/**
 * Shows the preferences AutoSage has gradually inferred from the conversation —
 * making the "understands the user over time" behavior visible instead of hidden
 * in the prompt.
 */
const LABELS = {
  budget: 'Budget',
  body_type: 'Body',
  powertrain: 'Powertrain',
  usage: 'Use',
};

export default function PreferencesBar({ preferences }) {
  const { t } = useI18n();
  if (!preferences) return null;

  const chips = [];
  for (const key of ['budget', 'body_type', 'powertrain', 'usage']) {
    if (preferences[key]) chips.push([LABELS[key], preferences[key]]);
  }
  for (const arrKey of ['priorities', 'candidates']) {
    const arr = preferences[arrKey];
    if (Array.isArray(arr)) {
      for (const v of arr) chips.push([null, v]);
    }
  }
  if (chips.length === 0) return null;

  return (
    <div className="pref-bar">
      <span className="pref-bar-label">{t('pref.label')}</span>
      {chips.map(([label, val], i) => (
        <span className="pref-chip" key={i}>
          {label && <b>{label}:</b>} {val}
        </span>
      ))}
    </div>
  );
}
