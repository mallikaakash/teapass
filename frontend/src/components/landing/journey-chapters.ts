/**
 * Chapter copy + artwork.
 *
 * NOTE: the PNGs in /public/landing are AI-generated UI mockups — they have a
 * fake nav, headline, and buttons baked into the pixels. They must never be
 * shown full-frame with real UI on top (that is what caused the overlapping
 * ghost text). `sceneOrigin` zooms each image into its scenic corner
 * (fields / people / product, bottom-right) so the baked-in mockup UI is
 * cropped out of view. See `.sceneImg` in landing.module.css.
 */
export const JOURNEY_CHAPTERS = [
  { id: "estate", kicker: "01 / Estate", title: "Every cup has a story.", lede: "Trace your tea from leaf to cup with privacy-preserving verification. Real people. Real places. A more transparent tea world.", image: "/landing/chapter-01-estate.png", sceneOrigin: "82% 92%" },
  { id: "harvest", kicker: "02 / Harvest · Origin", title: "It begins with a leaf.", lede: "Grower lots, harvest timestamps, and origin attestations — from the field to your cup.", image: "/landing/chapter-02-harvest.png", sceneOrigin: "85% 82%" },
  { id: "processing", kicker: "03 / Processing · Transformation", title: "From fresh leaves to fine tea.", lede: "Intake, processing, yields, and transformation records in one verifiable chain.", image: "/landing/chapter-03-processing.png", sceneOrigin: "90% 80%" },
  { id: "movement", kicker: "04 / Movement · Chain of custody", title: "A journey worth tracing.", lede: "Every transfer recorded — estate to factory, warehouse to market.", image: "/landing/chapter-04-movement.png", sceneOrigin: "85% 88%" },
  { id: "blending", kicker: "05 / Blending · Private proof", title: "The recipe stays secret. The integrity does not.", lede: "Verify authentic, traceable inputs without revealing the confidential formula.", image: "/landing/chapter-05-blending.png", sceneOrigin: "72% 85%" },
  { id: "testing", kicker: "06 / Testing · Quality evidence", title: "Trust should be testable.", lede: "Lab results and quality evidence bound to every batch.", image: "/landing/chapter-06-testing.png", sceneOrigin: "70% 88%" },
  { id: "packaging", kicker: "07 / Packaging · The passport", title: "One scan. A whole journey.", lede: "Origin, evidence, and disclosed claims — from leaf to cup.", image: "/landing/chapter-07-packaging.png", sceneOrigin: "74% 90%" },
] as const;

export type JourneyChapter = (typeof JOURNEY_CHAPTERS)[number];
