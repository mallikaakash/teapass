"use client";

import { useEffect, useState, type ReactNode } from "react";
import { EstatePainting } from "@/components/art/EstatePainting";
import { Passport } from "@/components/passport/Passport";
import { tileFromInput } from "@/lib/detect";
import { LOOKS } from "@/lib/looks";
import { PICKER_LOOKS } from "@/lib/schema";
import { SEALS } from "@/lib/sample";
import { tileLabel } from "@/lib/tile-label";
import { JourneyHero } from "./JourneyHero";
import styles from "./landing.module.css";

const PASTES = [
  "garden@sonapur.example",
  "flush/leaf.png",
  "sonapur/flush",
  "https://www.youtube.com/watch?v=aqz-KE-bpKQ",
  "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC",
  "Plucked at first light.",
];

export function Landing({ cards }: { cards: ReactNode[] }) {
  const [lookIndex, setLookIndex] = useState(0);
  return (
    <div className={styles.page}>
      <header className={styles.nav}>
        <div className={styles.navInner}>
          <a className={styles.brand} href="#estate">TeaPass</a>
          <nav className={styles.navLinks} aria-label="Landing">
            <a href="#journey">Journey</a>
            <a href="#playground">Playground</a>
            <a href="#looks">Looks</a>
            <a href="/verify">Verify a batch</a>
          </nav>
          <a className={styles.navCta} href="/new">Try a demo</a>
        </div>
      </header>

      <main>
        <JourneyHero />

        <section className={styles.section} id="playground">
          <p className={styles.kicker}>Try the product</p>
          <h2 className={styles.sectionTitle}>One playground, four mechanics</h2>
          <div className={styles.playGrid}>
            <article className={styles.playCard} id="harvest">
              <h3>Paste morph</h3>
              <p className={styles.playLede}>Links become the tile detection actually returns.</p>
              <PasteMorph />
            </article>
            <article className={styles.playCard} id="processing">
              <h3>Processing</h3>
              <div className={styles.stages}>
                {["Wither", "Roll", "Oxidize", "Dry"].map((name) => (
                  <span key={name} className={styles.stageChip}>{name}</span>
                ))}
              </div>
            </article>
            <article className={styles.playCard} id="blending">
              <h3>Blending table</h3>
              <p className={styles.playLede}>The props on the blending table, in order.</p>
              <div className={styles.props}>
                {["Basket", "Chest", "Seal", "Cup"].map((name) => (
                  <span key={name} className={styles.prop}>{name}</span>
                ))}
              </div>
            </article>
            <article className={styles.playCard} id="testing">
              <h3>Evidence seal</h3>
              <SealButton id="lab" />
            </article>
          </div>
          <article className={styles.playCardWide} id="packaging">
            <h3>Tea passport</h3>
            <Passport />
          </article>
        </section>

        <section className={styles.section} id="looks">
          <p className={styles.kicker}>Five drawings</p>
          <h2 className={styles.sectionTitle}>One garden page, five looks</h2>
          <div className={styles.lookSwitcher}>
            {PICKER_LOOKS.map((id, i) => (
              <button key={id} type="button" className={i === lookIndex ? styles.on : undefined} onClick={() => setLookIndex(i)}>
                {LOOKS[id].label}
              </button>
            ))}
          </div>
          <p className={styles.lookSentence}>{LOOKS[PICKER_LOOKS[lookIndex]].sentence}</p>
          <div className={styles.previewFrame}>{cards[lookIndex]}</div>
          <p className={styles.demoLink}>
            <a href={`/new?look=${PICKER_LOOKS[lookIndex]}`}>Start in {LOOKS[PICKER_LOOKS[lookIndex]].label}</a>
            {" · "}
            <a href="/sonapur">Open the demo garden</a>
          </p>
        </section>
      </main>

      <footer className={styles.footer}>
        <EstatePainting className={styles.footerArt} />
        <p className={styles.wordmark}>TeaPass</p>
        <p className={styles.footerLine}>Every cup has a story. Now it has proof.</p>
      </footer>
    </div>
  );
}

function PasteMorph() {
  const [text, setText] = useState("");
  const [tile, setTile] = useState<ReturnType<typeof tileFromInput> | null>(null);
  useEffect(() => {
    let sample = 0;
    let count = 0;
    let hold = false;
    const timer = window.setInterval(() => {
      if (hold) return;
      const value = PASTES[sample];
      count += 1;
      setText(value.slice(0, count));
      if (count >= value.length) {
        hold = true;
        setTile(tileFromInput(value));
        window.setTimeout(() => {
          sample = (sample + 1) % PASTES.length;
          count = 0;
          hold = false;
          setTile(null);
          setText("");
        }, 1200);
      }
    }, 65);
    return () => window.clearInterval(timer);
  }, []);
  const label = tile ? tileLabel(tile) : null;
  return (
    <div className={styles.paste}>
      <code>{text}|</code>
      {label ? (
        <div className={styles.pasteTile}>
          <strong>{label.title}</strong>
          <span>{tile?.type}</span>
        </div>
      ) : null}
    </div>
  );
}

function SealButton({ id }: { id: (typeof SEALS)[number]["id"] }) {
  const seal = SEALS.find((s) => s.id === id)!;
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button type="button" className={styles.sealBtn} onClick={() => setOpen((v) => !v)}>
        {open ? "Hide the seal" : "Open the seal"}
      </button>
      {open ? (
        <ul className={styles.sealList}>
          {seal.lines.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
