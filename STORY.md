# Story

Product name: TeaPass
One-sentence world: A garden page is a walk through an Assam tea estate, from the hills to a finished cup, with a seal of proof beside each step.
Who it is for: A garden, factory, or blender publishing one public page for an estate or a batch.
Voice (three words): earthen, exact, quiet

## Headline
Pattern: "Every cup has a story. Now it has ____."
Words that rotate: proof, a leaf, a lot, a seal, a name

## Looks
Five. The first is the default. All five are free. There is no paid tier.

| id | label | What the visitor sees | What a link becomes here | free? |
|----|-------|----------------------|--------------------------|-------|
| estate | Estate | Layered hills, a cream sky, tea rows, a winding trail | A leaf tag tied to a bush | yes |
| harvest | Harvest | Cane baskets and floating lot labels | A paper tag on a basket | yes |
| loft | Loft | Withering trays, steam, rolling drums | A process card on a tray | yes |
| road | Road | Tea chests, a warehouse, dotted trails | A stencil on a chest | yes |
| cup | Cup | A packet, a poured cup, an open passport | A line printed in the passport | yes |

Plain fallback id: `plain` (not offered in the picker)

Retired ids, mapped at parse time: `garden` → `estate`

## Layouts offered
bento, list, canvas

## v1 scope
- [x] Public page
- [x] Studio
- [x] Landing
- [ ] Agent API
- [ ] Analytics
- [ ] Paid tier

## Landing scenes
The landing is one continuous estate. Seven chapters carry the tea. The motions below sit inside that journey. Proof is a seal beside the leaf, not a separate pitch.

| Motion | Object in this world |
|--------|----------------------|
| Pinned hero | The estate. Scroll carries the camera down the trail toward the pickers. Chapter 01. |
| Rotating word | proof, a leaf, a lot, a seal, a name |
| Wall of pages | The same sample page, drawn in all five looks, spread like ledgers on a sorting table |
| Look cards | Estate, Harvest, Loft, Road, Cup |
| Paste morph | A pasted email, image, repo, video, music URL, or plain sentence becomes the tile detection actually returns, drawn as a leaf tag or lot label. Chapter 02, Harvest. |
| Draggable props | A basket, a chest, a seal, and a cup on the blending table. Chapter 05. |
| Sketch that paints itself | The footer estate painting. Color shows through as the pencil gives way. |

Chapters, in order:

1. Estate — the pinned hero.
2. Harvest — pickers, baskets, lot labels. Paste morph lives here.
3. Processing — wither, roll, oxidize, dry. Four animated stages.
4. Movement — chests, a warehouse, dotted trails.
5. Blending — leaves enter one vessel. The recipe stays off the page. Draggable props live here.
6. Testing — a vial, an instrument, a certificate. A seal opens a sample evidence record.
7. Packaging — the packet turns. A sample tea passport opens onto lineage, origin, evidence, proof, and claims.

A falling leaf joins the chapters. Workers, steam, drums, and carts move on their own. The typed-agent block is absent, because this version has no agent door.

Actions that stay available: Explore the technology, Try a demo, Verify a batch.

Palette: cream, tea green, sage, terracotta.
Art: original illustration made for this project. Reference paintings are not shipped.

## Do not use
Posy's island, kite, cat, Mira, and the look names Painted, Desk, Washi, Cobalt, Night, Lofi.
