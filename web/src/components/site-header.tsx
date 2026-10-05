import Link from "next/link";

import { ThemeToggle } from "@/components/theme-toggle";

export function SiteHeader() {
  return (
    <header className="relative z-40 border-b bg-background">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-7">
        <Link href="/" aria-label="Resona home" className="font-serif text-base font-semibold tracking-[0.26em] sm:text-lg">
          RESONA
        </Link>
        <div className="flex items-center gap-4 sm:gap-8">
          <nav aria-label="Primary navigation" className="text-xs font-medium sm:text-sm">
            <Link href="/" className="text-foreground hover:text-primary">Search</Link>
          </nav>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
