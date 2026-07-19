import { useState } from 'react';

// Light is the default; 'dark' is opt-in and persisted. index.html applies the
// saved value before first paint (no flash) — this hook tracks/toggles it.
export function useTheme() {
  const [theme, setTheme] = useState(
    () => (document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light')
  );
  const toggle = () => {
    const next = theme === 'dark' ? 'light' : 'dark';
    if (next === 'dark') document.documentElement.dataset.theme = 'dark';
    else delete document.documentElement.dataset.theme;
    localStorage.setItem('autosage-theme', next);
    setTheme(next);
  };
  return [theme, toggle];
}
