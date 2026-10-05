import type { CSSProperties } from "react";

import styles from "./hero-wordmark.module.css";

const letters = "RESONA".split("");

export function HeroWordmark() {
  return (
    <div className={styles.wordmark} role="img" aria-label="RESONA">
      {letters.map((letter, index) => (
        <span
          key={index}
          className={styles.letter}
          style={{ "--delay": `${0.18 + index * 0.12}s` } as CSSProperties}
          aria-hidden="true"
        >
          <span className={styles.outline}>{letter}</span>
          <span className={styles.ink}>{letter}</span>
        </span>
      ))}
    </div>
  );
}
