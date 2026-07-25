# Professional Manga Gap Review v3

Date: 2026-07-25

## Findings

### P0: one performance pose is reused for all three shots in a scene

Each scene still has one `primary`, `secondary`, and `tertiary` cutout. Blocking,
camera, crop, and treatment now change by shot, but facial expression, hand
gesture, body pose, and prop state do not. This is the largest remaining gap
from a production-grade motion comic.

Required asset-level follow-up: generate append-only pose/expression variants
for every speaking, reaction, decision, and climax beat; record them in the
asset manifest and select them per shot. Do not simulate speech with arbitrary
sprite scaling or fake mouth flaps.

### P1: focus was previously expressed with translucent characters

Resolved in v3. Every subject remains fully opaque after entrance. Scale,
screen side, crop, foreground occlusion, and composition now carry hierarchy.

### P1: nine shots previously shared one generic visual grammar

Resolved in v3. Every shot now declares a purpose-specific `layoutMode`:
full-bleed establish, speaker stage, reaction panel, pressure wide, action
diagonal, decision inset, impact frame, payoff panel, or closing tableau.

### P1: captions read as one educational explainer bar

Improved in v3. Narration uses a restrained lower editorial strip; dialogue
uses a high-contrast manga balloon treatment with a tail; thought lines use a
dashed treatment. Spoken wording and root-level caption ownership are
unchanged.

### P2: comic treatments initially reused the same full-frame view

Improved in v3.1. Reaction and decision shots now render an independently
framed, animated bust/action crop of the focused character. The inset remains
derived from the current cutout; a later asset revision should replace it with
an alternate expression or pose plate.

## Verification

- `15 passed`
- Four productions passed composition, HyperFrames lint, strict check,
  snapshots, transition frames, frame checks, and animation-map review.
- New midpoint contact sheets show no translucent subject cutouts.
- Preview URLs explicitly select `comp=index.html`; Studio no longer opens on
  an empty "No compositions found" state.
- Render remains blocked until the new composition hashes receive explicit
  Studio approval.

## Story-specific directing v4

The batch no longer shares one visual/editorial template:

- Guangzhou uses a clue-expedition grammar: lookout POV, map proof, city
  reveal, and a camera-photo freeze ending.
- Solar System uses an orbital repair countdown: fault scan, ordered orbit
  montage, energy lock, and an eight-planet chain-light ending.
- Navigator uses a horizontal chronicle: era reverse shots, chart-table
  collaboration, role-aware letter handoff, and a letter-to-horizon ending.
- Star Seed uses a vertical pilgrimage: low storm angles, guarded movement,
  tree-crown ascent, and an outward star-bloom ending.

Task cards now own `director_profile`, nine `shot_signatures`, optional
per-scene semantic-to-asset role maps, and one story-specific `ending_mode`.
The compiler verifies that all four profiles, endings, grammars, and signature
sets are distinct.
