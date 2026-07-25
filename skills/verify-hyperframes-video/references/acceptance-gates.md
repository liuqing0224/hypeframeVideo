# Acceptance Gates

## HyperFrames

- `lint` passes during iteration.
- Strict `check` passes with transition samples and frame checks. The layout
  tolerance is 80px for intentionally clipped entrance motion; the separate
  frame check remains at 4px and motion sidecars assert all final subject bounds.
- Every sub-composition midpoint snapshot is visible and correctly mounted.
- Motion sidecars pass and the animation map has no unexplained frozen windows.
- Every scene has three distinct subject and environment blocking states; all
  subject start and travel-end bounds remain inside 1920x1080.
- Final Studio preview is explicitly approved before rendering.

## Encoded Output

- 1920x1080, 30 fps, H.264 video, and at least one AAC audio stream.
- Frame count matches rounded manifest duration within one frame.
- Evidence frames are nonblank and show coherent z-order, safe captions, and no green fringe.
- Manual review is recorded before promotion.
