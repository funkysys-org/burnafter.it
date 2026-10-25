import React, { createContext, useContext, useEffect, useState } from "react";

const THEMES = [
  { id: "radio-puppa", label: "PUPPA" },
  { id: "ember", label: "EMBER" },
  { id: "warm", label: "WARM" },
];
const DEFAULT = "radio-puppa";
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
  return (
    <div className="theme-switch" role="group"
         aria-label="theme" style={{ display: "inline-flex" }}>
      {THEMES.map((t) => (
        <button key={t.id} aria-pressed={theme === t.id}
                title={`theme: ${t.id}`}
                onClick={() => setTheme(t.id)}>
          {t.label}
        </button>
      ))}
    </div>
  );
}
