"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";

import { Button } from "@/components/ui/button";

export function ThemeToggle() {
  const [dark, setDark] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      const saved = localStorage.getItem("resona-theme");
      const enabled = saved === "dark" || (saved === null && matchMedia("(prefers-color-scheme: dark)").matches);
      document.documentElement.classList.toggle("dark", enabled);
      setDark(enabled);
      setReady(true);
    });
    return () => cancelAnimationFrame(frame);
  }, []);

  const toggleTheme = () => {
    const next = !dark;
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("resona-theme", next ? "dark" : "light");
    setDark(next);
  };

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon-sm"
      onClick={toggleTheme}
      aria-label={ready && dark ? "Switch to light theme" : "Switch to dark theme"}
      title={ready && dark ? "Light theme" : "Dark theme"}
      className="rounded-full"
    >
      {ready && dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </Button>
  );
}
