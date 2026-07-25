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

### P2: comic treatments are graphic overlays, not true alternate panels

The current reaction and decision borders add editorial rhythm but reuse the
same underlying camera view. A later asset/composition revision should support
real inset crops or alternate pose plates with independent camera framing.

## Verification

- `15 passed`
- Four productions passed composition, HyperFrames lint, strict check,
  snapshots, transition frames, frame checks, and animation-map review.
- New midpoint contact sheets show no translucent subject cutouts.
- Render remains blocked until the new composition hashes receive explicit
  Studio approval.
