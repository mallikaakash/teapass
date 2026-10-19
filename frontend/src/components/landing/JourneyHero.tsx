import Image from "next/image";
import { JOURNEY_CHAPTERS, type JourneyChapter } from "./journey-chapters";
import styles from "./landing.module.css";

/**
 * Clean journey: every chapter is a normal block in page flow — copy in one
 * column, artwork in its own box next to it. No pinned/sticky stage, no
 * stacked crossfading backgrounds, no text over images, no floating dots or
 * pills. The artwork is zoom-cropped to its scenic corner (see
 * journey-chapters.ts) so the mockup UI baked into the PNGs stays out of view.
 */
export function JourneyHero() {
  const [hero, ...chapters] = JOURNEY_CHAPTERS;
  return (
    <>
      <section className={styles.hero} id="estate">
        <div className={styles.heroInner}>
          <p className={styles.journeyKicker}>{hero.kicker}</p>
          <h1 className={styles.journeyTitle}>
            Every cup has a story.
            <span className={styles.titleLine}>
              Now it has <em>proof</em>.
            </span>
          </h1>
          <p className={styles.journeyLede}>{hero.lede}</p>
          <div className={styles.journeyActions}>
            <a className={styles.btnPrimary} href="#journey">Explore the journey</a>
            <a className={styles.btnGhost} href="/explore">Explore the technology</a>
            <a className={styles.btnGhost} href="/new">Try a demo</a>
          </div>
        </div>
        <Scene chapter={hero} className={styles.heroScene} priority />
      </section>

      <section className={styles.chapters} id="journey" aria-label="The tea journey">
        {chapters.map((chapter, i) => (
          <article key={chapter.id} className={i % 2 ? styles.chapterFlip : styles.chapter}>
            <div className={styles.chapterCopy}>
              <p className={styles.journeyKicker}>{chapter.kicker}</p>
              <h2 className={styles.chapterTitle}>{chapter.title}</h2>
              <p className={styles.journeyLede}>{chapter.lede}</p>
            </div>
            <Scene chapter={chapter} />
          </article>
        ))}
      </section>
    </>
  );
}

function Scene({ chapter, className, priority }: { chapter: JourneyChapter; className?: string; priority?: boolean }) {
  return (
    <div className={`${styles.scene} ${className ?? ""}`}>
      <Image
        src={chapter.image}
        alt=""
        width={1672}
        height={941}
        priority={priority}
        sizes="(max-width: 800px) 100vw, 1100px"
        className={styles.sceneImg}
        style={{ transformOrigin: chapter.sceneOrigin }}
      />
    </div>
  );
}
