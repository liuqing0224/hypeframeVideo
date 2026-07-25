# Alpha Quality

- Soft-key the declared chroma color and despill translucent edges.
- Split sheets with minimum-cost seams near expected third boundaries.
- A seam must not cross foreground alpha.
- All four output corners must be transparent.
- Subject coverage must be non-empty and below 95% of the trimmed image.
- No important object may touch a crop edge after padding.
- Inspect every layer on a checkerboard contact sheet.
