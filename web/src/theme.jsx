import React, { createContext, useContext, useEffect, useState } from "react";

const THEMES = [
  { id: "puppa-night", label: "antani" },
  { id: "radio-puppa", label: "puppa" },
  { id: "ember", label: "ember" },
  { id: "warm", label: "warm" },
];
const DEFAULT = "puppa-night";
const ThemeCtx = createContext({ theme: DEFAULT, setTheme: () => {} });

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    try {
      const saved = localStorage.getItem("bai-theme");
      return THEMES.some((t) => t.id === saved) ? saved : DEFAULT;
    } catch {
      return DEFAULT;
    }
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem("bai-theme", theme); } catch {}
  }, [theme]);

  return (
    <ThemeCtx.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeCtx.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeCtx);
}

export function ThemeSwitch() {
  const { theme, setTheme } = useTheme();
  const idx = Math.max(0, THEMES.findIndex((t) => t.id === theme));
  const next = THEMES[(idx + 1) % THEMES.length];
  return (
    <button className="theme-switch" type="button"
            title={`theme: ${THEMES[idx].id} — click to switch to ${next.label}`}
            aria-label={`theme: ${THEMES[idx].label}. activate to switch to ${next.label}`}
            onClick={() => setTheme(next.id)}>
      ◐ {THEMES[idx].label} ▸
    </button>
  );
}
